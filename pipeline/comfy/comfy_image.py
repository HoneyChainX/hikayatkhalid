#!/usr/bin/env python3
"""
Drive a ComfyUI IMAGE workflow over HTTP: upload an input image, run the graph,
download the output PNG. Used to restyle keyframes flat-2D -> 3D with Flux Kontext.
Headless + browser User-Agent (RunPod proxy friendly), like animate_one.py.

    export COMFY_URL=https://<pod>-8188.proxy.runpod.net
    python3 pipeline/comfy/comfy_image.py \
        --image build/ep01/img/shot01.jpg \
        --workflow pipeline/comfy/workflow_flux_kontext.api.json \
        --prompt "Convert to a polished 3D Pixar-style render; keep the same characters, poses, composition and scene." \
        --out build/ep01/img3d/shot01.png
"""
import argparse
import json
import os
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def http(method, path, data=None, headers=None, timeout=600):
    h = {"User-Agent": UA}
    h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(f"{COMFY}{path}", data=data, method=method, headers=h),
                                timeout=timeout) as r:
        return r.read()


def upload_image(p: Path):
    b = uuid.uuid4().hex
    ct = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    body = b"".join([
        f"--{b}\r\n".encode(),
        f'Content-Disposition: form-data; name="image"; filename="{p.name}"\r\n'.encode(),
        f"Content-Type: {ct}\r\n\r\n".encode(), p.read_bytes(), b"\r\n",
        f"--{b}\r\n".encode(), b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n',
        f"--{b}--\r\n".encode()])
    return json.loads(http("POST", "/upload/image", body,
                           {"Content-Type": f"multipart/form-data; boundary={b}"}))["name"]


def find(wf, title):
    for n in wf.values():
        if isinstance(n, dict) and n.get("_meta", {}).get("title", "").upper() == title:
            return n
    return None


def patch(wf, image_name, prompt, seed):
    k, p, s = find(wf, "KEYFRAME"), find(wf, "POSITIVE"), find(wf, "SAMPLER")
    if k:
        k["inputs"]["image"] = image_name
    if p:
        p["inputs"]["text"] = prompt
    if s:
        for key in ("seed", "noise_seed"):
            if key in s["inputs"]:
                s["inputs"][key] = seed
    return wf


def queue_fetch(wf, out: Path):
    r = json.loads(http("POST", "/prompt", json.dumps({"prompt": wf, "client_id": uuid.uuid4().hex}).encode(),
                        {"Content-Type": "application/json"}))
    pid = r["prompt_id"]
    print("queued:", pid, flush=True)
    while True:
        time.sleep(2)
        h = json.loads(http("GET", f"/history/{pid}") or b"{}")
        if pid in h:
            for node in h[pid].get("outputs", {}).values():
                for im in node.get("images", []):
                    if str(im.get("filename", "")).lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                        q = urllib.parse.urlencode({"filename": im["filename"],
                                                    "subfolder": im.get("subfolder", ""),
                                                    "type": im.get("type", "output")})
                        out.write_bytes(http("GET", f"/view?{q}"))
                        return True
            return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--workflow", required=True)
    ap.add_argument("--prompt", default="Convert to a polished 3D Pixar-style animated movie render; keep the same "
                    "characters, faces, clothing, poses, composition and background; soft cinematic lighting; high detail.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    img, out, wf_path = Path(a.image), Path(a.out), Path(a.workflow)
    if not img.exists():
        raise SystemExit(f"missing image {img}")
    out.parent.mkdir(parents=True, exist_ok=True)
    template = json.loads(wf_path.read_text(encoding="utf-8"))
    print(f"ComfyUI={COMFY}  {img} -> {out}", flush=True)
    name = upload_image(img)
    wf = patch(json.loads(json.dumps(template)), name, a.prompt, a.seed)
    wf = {k: v for k, v in wf.items()
          if not k.startswith("_") and isinstance(v, dict) and v.get("class_type") not in ("Note", "MarkdownNote")}
    t = time.time()
    ok = queue_fetch(wf, out)
    print((f"OK  {out}  ({time.time()-t:.0f}s)") if ok else "FAILED: no image output", flush=True)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
