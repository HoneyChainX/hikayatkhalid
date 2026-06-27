#!/usr/bin/env python3
"""
Wan 2.2 S2V — audio-driven lip-synced video from a portrait/keyframe + a voice clip.
Drives ComfyUI over HTTP (browser UA for the RunPod proxy). Uploads BOTH the image and
the audio, sizes `length` to the audio at 16 fps, and returns a lip-synced (voiced) mp4.

    export COMFY_URL=https://<pod>-8188.proxy.runpod.net
    python3 pipeline/comfy/animate_s2v.py \
        --image assets/characters/khalid_ref_3d.png \
        --audio build/ep01/audio/shot01.mp3 \
        --workflow pipeline/comfy/workflow_wan_s2v.api.json \
        --out build/ep01/clips_s2v/shot01.mp4
"""
import argparse
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
FPS = 16


def http(method, path, data=None, headers=None, timeout=1200):
    h = {"User-Agent": UA}
    h.update(headers or {})
    with urllib.request.urlopen(urllib.request.Request(f"{COMFY}{path}", data=data, method=method, headers=h),
                                timeout=timeout) as r:
        return r.read()


def upload(p: Path, ctype):
    b = uuid.uuid4().hex
    body = b"".join([
        f"--{b}\r\n".encode(),
        f'Content-Disposition: form-data; name="image"; filename="{p.name}"\r\n'.encode(),
        f"Content-Type: {ctype}\r\n\r\n".encode(), p.read_bytes(), b"\r\n",
        f"--{b}\r\n".encode(), b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n',
        f"--{b}--\r\n".encode()])
    return json.loads(http("POST", "/upload/image", body,
                           {"Content-Type": f"multipart/form-data; boundary={b}"}))["name"]


def audio_seconds(p: Path):
    try:
        import imageio_ffmpeg
        ff = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ff = "ffmpeg"
    err = subprocess.run([ff, "-i", str(p)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", err)
    return (int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])) if m else 4.0


def find(wf, t):
    for n in wf.values():
        if isinstance(n, dict) and n.get("_meta", {}).get("title", "").upper() == t:
            return n
    return None


def patch(wf, image_name, audio_name, prompt, length, seed):
    for title, key, val in [("KEYFRAME", "image", image_name), ("AUDIO", "audio", audio_name),
                            ("POSITIVE", "text", prompt)]:
        n = find(wf, title)
        if n:
            n["inputs"][key] = val
    ln = find(wf, "LENGTH")
    if ln and "length" in ln["inputs"]:
        ln["inputs"]["length"] = length
    s = find(wf, "SAMPLER")
    if s:
        for k in ("seed", "noise_seed"):
            if k in s["inputs"]:
                s["inputs"][k] = seed
    return wf


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
    ap.add_argument("--image", required=True)
    ap.add_argument("--audio", required=True)
    ap.add_argument("--workflow", default="pipeline/comfy/workflow_wan_s2v.api.json")
    ap.add_argument("--prompt", default="A wholesome 3D animated character speaks warmly to camera, natural gentle "
                    "expression, soft lighting, stays perfectly on-model, smooth motion.")
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    img, aud, out = Path(a.image), Path(a.audio), Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    secs = audio_seconds(aud)
    length = min(77, max(16, round(secs * FPS)))
    template = json.loads(Path(a.workflow).read_text(encoding="utf-8"))
    print(f"ComfyUI={COMFY}  img={img}  audio={aud} ({secs:.1f}s -> {length} frames @ {FPS}fps)", flush=True)
    iname = upload(img, "image/png" if img.suffix.lower() == ".png" else "image/jpeg")
    aname = upload(aud, "audio/mpeg")
    wf = patch(json.loads(json.dumps(template)), iname, aname, a.prompt, length, a.seed)
    wf = {k: v for k, v in wf.items() if not k.startswith("_") and isinstance(v, dict)
          and v.get("class_type") not in ("Note", "MarkdownNote")}
    t = time.time()
    ok = queue_fetch(wf, out)
    print((f"OK  {out}  ({time.time()-t:.0f}s)") if ok else "FAILED: no video output", flush=True)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
