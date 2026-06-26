#!/usr/bin/env python3
"""
One-shot proof: animate a SINGLE image via ComfyUI (LTX/Wan i2v) → mp4.
Headless (web-terminal friendly — no canvas needed). Auto-detects the installed
LTX checkpoint + T5 so it survives model-filename differences.

    export COMFY_URL=http://127.0.0.1:8188
    # cheap environment check first (no GPU/render):
    python3 pipeline/comfy/animate_one.py --diagnose
    # then the real proof:
    python3 pipeline/comfy/animate_one.py \
        --image assets/characters/khalid_ref.png \
        --out /workspace/khalid_proof.mp4 --seconds 5

Patches the workflow template by node title (KEYFRAME/POSITIVE/NEGATIVE/SAMPLER/
LENGTH) AND rewrites the checkpoint/clip loaders to whatever is actually installed.
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
DEFAULT_WF = Path(__file__).parent / "workflow_ltx2_i2v.api.json"
FPS = int(os.environ.get("CLIP_FPS", 24))
NEG = ("text, letters, watermark, logo, blurry, low quality, deformed, extra limbs, "
       "horror, scary, photorealistic, nsfw")


# RunPod's proxy (Cloudflare) 403s the default Python-urllib UA; present a browser UA.
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def http(method, path, data=None, headers=None, timeout=600):
    h = {"User-Agent": UA}
    h.update(headers or {})
    req = urllib.request.Request(f"{COMFY}{path}", data=data, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def object_info(klass):
    try:
        return json.loads(http("GET", f"/object_info/{klass}", timeout=30))
    except Exception:
        return {}


def options_for(klass, input_name):
    """Return the list of allowed values for a node input (e.g. installed ckpt names)."""
    info = object_info(klass).get(klass, {})
    req = (info.get("input", {}) or {}).get("required", {})
    val = req.get(input_name)
    if isinstance(val, list) and val and isinstance(val[0], list):
        return val[0]
    return []


def pick(names, *prefer):
    for p in prefer:
        for n in names:
            if p.lower() in n.lower():
                return n
    return names[0] if names else None


def diagnose():
    cks = options_for("CheckpointLoaderSimple", "ckpt_name")
    unets = options_for("UNETLoader", "unet_name")
    clips = options_for("CLIPLoader", "clip_name")
    nodes = object_info("")  # all nodes (may be large); fall back to targeted checks
    have = lambda k: bool(object_info(k))
    print(f"ComfyUI: {COMFY}")
    print(f"checkpoints ({len(cks)}): {cks}")
    print(f"unet/gguf  ({len(unets)}): {unets}")
    print(f"clip/t5    ({len(clips)}): {clips}")
    print("LTXVImgToVideo node:", "yes" if have("LTXVImgToVideo") else "NO")
    print("WanImageToVideo node:", "yes" if have("WanImageToVideo") else "no")
    print("VHS_VideoCombine node:", "yes" if have("VHS_VideoCombine") else "NO")
    ltx_ck = pick(cks, "ltx")
    t5 = pick(clips, "t5xxl", "t5")
    print(f"-> would use checkpoint: {ltx_ck}")
    print(f"-> would use T5 clip   : {t5}")
    if not ltx_ck and unets:
        print("!! no LTX *checkpoint* — LTX is likely GGUF (UNETLoader). The classic template "
              "needs a checkpoint; export a GGUF i2v template to workflow_ltx2_i2v.api.json, "
              "or place an LTX safetensors checkpoint. (Reported so we can adapt.)")


def find(wf, title):
    for node in wf.values():
        if isinstance(node, dict) and node.get("_meta", {}).get("title", "").upper() == title:
            return node
    return None


def patch(wf, image_name, prompt, seed, n_frames):
    # rewrite loaders to installed files
    ck = find(wf, "LTXV CHECKPOINT")
    if ck:
        names = options_for("CheckpointLoaderSimple", "ckpt_name")
        sel = pick(names, "ltx")
        if sel:
            ck["inputs"]["ckpt_name"] = sel
    t5 = find(wf, "T5 TEXT ENCODER")
    if t5:
        names = options_for("CLIPLoader", "clip_name")
        sel = pick(names, "t5xxl", "t5")
        if sel:
            t5["inputs"]["clip_name"] = sel
    # patch per-shot inputs
    for title, key, value in [("KEYFRAME", "image", image_name), ("POSITIVE", "text", prompt),
                              ("NEGATIVE", "text", NEG)]:
        node = find(wf, title)
        if node:
            node["inputs"][key] = value
    smp = find(wf, "SAMPLER")
    if smp:
        for k in ("seed", "noise_seed"):
            if k in smp["inputs"]:
                smp["inputs"][k] = seed
    ln = find(wf, "LENGTH")
    if ln:
        for k in ("length", "frames", "num_frames", "video_length"):
            if k in ln["inputs"]:
                ln["inputs"][k] = n_frames
    return wf


def upload_image(p: Path):
    boundary = uuid.uuid4().hex
    ctype = "image/png" if p.suffix.lower() == ".png" else "image/jpeg"
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="image"; filename="{p.name}"\r\n'.encode(),
        f"Content-Type: {ctype}\r\n\r\n".encode(), p.read_bytes(), b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n',
        f"--{boundary}--\r\n".encode(),
    ])
    out = http("POST", "/upload/image", body,
               {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return json.loads(out)["name"]


def queue_and_fetch(wf, out_path: Path):
    cid = uuid.uuid4().hex
    res = json.loads(http("POST", "/prompt", json.dumps({"prompt": wf, "client_id": cid}).encode(),
                          {"Content-Type": "application/json"}))
    pid = res["prompt_id"]
    print("queued:", pid, flush=True)
    while True:
        time.sleep(3)
        hist = json.loads(http("GET", f"/history/{pid}") or b"{}")
        if pid in hist:
            for node in hist[pid].get("outputs", {}).values():
                for v in (node.get("gifs") or node.get("videos") or node.get("images") or []):
                    if str(v.get("filename", "")).lower().endswith((".mp4", ".webm", ".mov")):
                        q = urllib.parse.urlencode({"filename": v["filename"],
                                                    "subfolder": v.get("subfolder", ""),
                                                    "type": v.get("type", "output")})
                        out_path.write_bytes(http("GET", f"/view?{q}"))
                        return True
            return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--diagnose", action="store_true", help="report installed models/nodes and exit")
    ap.add_argument("--image", help="image to animate")
    ap.add_argument("--prompt", default="gentle wholesome 2D cartoon animation, soft natural motion, "
                    "breathing and blinking, light warm breeze, slow cinematic push-in, character stays on-model")
    ap.add_argument("--out", default="/workspace/proof.mp4")
    ap.add_argument("--seconds", type=float, default=5.0)
    ap.add_argument("--workflow", default=str(DEFAULT_WF))
    a = ap.parse_args()

    if a.diagnose:
        diagnose()
        return
    if not a.image:
        raise SystemExit("--image is required (or use --diagnose)")
    img, wf_path, out = Path(a.image), Path(a.workflow), Path(a.out)
    if not img.exists():
        raise SystemExit(f"missing image {img}")
    if not wf_path.exists():
        raise SystemExit(f"missing workflow {wf_path}")
    template = json.loads(wf_path.read_text(encoding="utf-8"))
    print(f"ComfyUI={COMFY}  image={img}  -> {out}", flush=True)
    name = upload_image(img)
    # LTXV needs (frames-1) divisible by 8 → round to the nearest 8k+1
    raw = int(round(a.seconds * FPS))
    n_frames = max(25, ((raw - 1 + 4) // 8) * 8 + 1)
    wf = patch(json.loads(json.dumps(template)), name, a.prompt, 7777, n_frames)
    # drop non-executable nodes (Notes / underscore keys) — /prompt rejects them
    wf = {k: v for k, v in wf.items()
          if not k.startswith("_") and isinstance(v, dict)
          and v.get("class_type") not in ("Note", "MarkdownNote")}
    t = time.time()
    ok = queue_and_fetch(wf, out)
    print((f"OK  {out}  ({time.time()-t:.0f}s)") if ok else
          "FAILED: no video in outputs — run --diagnose to check models/nodes.", flush=True)
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
