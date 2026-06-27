#!/usr/bin/env python3
"""
SeedVR2 video upscale/restore. Uploads a clip to ComfyUI, runs the SeedVR2 DiT
upscaler (shortest edge -> --res px, default 1080), returns the upscaled mp4 (silent;
mux the normalized audio at assembly). First run auto-downloads the 3B model (~6 GB).

    export COMFY_URL=https://<pod>-8188.proxy.runpod.net
    python3 pipeline/comfy/upscale_seedvr2.py \
        --in build/ep01/clips_s2v/shot01.mp4 \
        --out build/ep01/clips_up/shot01.mp4 --res 1080
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


def http(method, path, data=None, headers=None, timeout=2400):
    h = {"User-Agent": UA}
    h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(f"{COMFY}{path}", data=data, method=method, headers=h),
                                timeout=timeout) as r:
        return r.read()


def upload(p: Path):
    b = uuid.uuid4().hex
    body = b"".join([
        f"--{b}\r\n".encode(),
        f'Content-Disposition: form-data; name="image"; filename="{p.name}"\r\n'.encode(),
        b"Content-Type: video/mp4\r\n\r\n", p.read_bytes(), b"\r\n",
        f"--{b}\r\n".encode(), b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n',
        f"--{b}--\r\n".encode()])
    return json.loads(http("POST", "/upload/image", body,
                           {"Content-Type": f"multipart/form-data; boundary={b}"}))["name"]


def find(wf, t):
    for n in wf.values():
        if isinstance(n, dict) and n.get("_meta", {}).get("title", "").upper() == t:
            return n
    return None


def queue_fetch(wf, out: Path):
    pid = json.loads(http("POST", "/prompt", json.dumps({"prompt": wf, "client_id": uuid.uuid4().hex}).encode(),
                          {"Content-Type": "application/json"}))["prompt_id"]
    print("queued:", pid, flush=True)
    while True:
        time.sleep(3)
        h = json.loads(http("GET", f"/history/{pid}") or b"{}")
        if pid in h:
            for node in h[pid].get("outputs", {}).values():
                for v in (node.get("gifs") or node.get("videos") or node.get("images") or []):
                    if str(v.get("filename", "")).lower().endswith((".mp4", ".webm", ".mov")):
                        q = urllib.parse.urlencode({"filename": v["filename"], "subfolder": v.get("subfolder", ""),
                                                    "type": v.get("type", "output")})
                        out.write_bytes(http("GET", f"/view?{q}"))
                        return True
            return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workflow", default="pipeline/comfy/workflow_seedvr2_upscale.api.json")
    ap.add_argument("--res", type=int, default=1080, help="target shortest-edge px")
    ap.add_argument("--batch", type=int, default=1, help="frames per batch (4n+1); 1 fits 24GB at 1080p")
    ap.add_argument("--model", default=None, help="override DiT model (e.g. seedvr2_ema_7b_sharp_fp16.safetensors)")
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    wf = json.loads(Path(a.workflow).read_text(encoding="utf-8"))
    name = upload(src)
    inp = find(wf, "INPUT")
    inp["inputs"]["video"] = name
    up = find(wf, "UPSCALE")
    up["inputs"]["resolution"] = a.res
    up["inputs"]["batch_size"] = a.batch
    if a.model:
        find(wf, "DIT")["inputs"]["model"] = a.model
    print(f"ComfyUI={COMFY}  upscaling {src.name} -> shortest edge {a.res}px", flush=True)
    t = time.time()
    ok = queue_fetch(wf, out)
    print((f"OK  {out}  ({time.time()-t:.0f}s)") if ok else "FAILED: no video output", flush=True)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
