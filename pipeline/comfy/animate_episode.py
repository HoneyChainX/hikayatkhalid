#!/usr/bin/env python3
"""
Path B — animate an episode on a ComfyUI box (rented/owned NVIDIA RTX).

Stage 3 of the series pipeline: takes the per-shot *consistent keyframes* (from
the keyframe stage, e.g. build/ep01/img/shotNN.jpg) and animates each into a
short clip with an image-to-video model (LTX-2.3 by default) running in ComfyUI,
then you stitch them (build_ep01.py / DaVinci).

It talks to a running ComfyUI over its HTTP API, so it works the same whether
ComfyUI is local, on a RunPod/Vast pod, or a serverless worker. It patches a
*workflow template* by node title, so you can drop in ComfyUI's own up-to-date
"LTX-2 Image-to-Video" template (Workflow ▸ Templates ▸ Export API) and just
title 4 nodes — no brittle hard-coded graph.

    export COMFY_URL=http://127.0.0.1:8188
    python3 pipeline/comfy/animate_episode.py            # -> build/ep01/clips_anim/shotNN.mp4
    python3 pipeline/build_ep01.py                        # (or DaVinci) to stitch

Workflow template (pipeline/comfy/workflow_ltx2_i2v.api.json) must contain nodes
whose `_meta.title` is one of:
  KEYFRAME  (LoadImage)         POSITIVE (text encode)   NEGATIVE (text encode)
  SAMPLER   (the sampler; seed) LENGTH   (optional: frame count / duration)
Resumable: shots with an output already present are skipped.
"""
import json
import os
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "build" / "ep01"
KEYFRAMES = Path(os.environ.get("KEYFRAME_DIR", BUILD / "img"))
OUT = BUILD / "clips_anim"
OUT.mkdir(parents=True, exist_ok=True)
COMFY = os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")
WORKFLOW = Path(os.environ.get("COMFY_WORKFLOW",
                               Path(__file__).parent / "workflow_ltx2_i2v.api.json"))
FPS = int(os.environ.get("CLIP_FPS", 24))
PAD_SEC = float(os.environ.get("CLIP_PAD", 0.8))     # extra video beyond narration
MIN_SEC, MAX_SEC = 3.0, 8.0
NEG = ("text, letters, watermark, logo, blurry, low quality, deformed, extra limbs, "
       "horror, scary, photorealistic, nsfw")

SHOTS = json.loads((ROOT / "pipeline" / "ep01_shotlist.json").read_text(encoding="utf-8"))


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def http(method, path, data=None, headers=None):
    req = urllib.request.Request(f"{COMFY}{path}", data=data, method=method,
                                 headers=headers or {})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def upload_image(p: Path):
    """Multipart upload to ComfyUI /upload/image; returns the stored name."""
    boundary = uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="image"; filename="{p.name}"\r\n'.encode(),
        b"Content-Type: image/jpeg\r\n\r\n", p.read_bytes(), b"\r\n",
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n',
        f"--{boundary}--\r\n".encode(),
    ])
    out = http("POST", "/upload/image", body,
               {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return json.loads(out)["name"]


def find(wf, title):
    for nid, node in wf.items():
        if node.get("_meta", {}).get("title", "").upper() == title:
            return nid, node
    return None, None


def patch(wf, image_name, prompt, seed, n_frames):
    _, kf = find(wf, "KEYFRAME")
    if kf:
        kf["inputs"]["image"] = image_name
    _, pos = find(wf, "POSITIVE")
    if pos:
        pos["inputs"]["text"] = prompt
    _, neg = find(wf, "NEGATIVE")
    if neg:
        neg["inputs"]["text"] = NEG
    _, smp = find(wf, "SAMPLER")
    if smp:
        for k in ("seed", "noise_seed"):
            if k in smp["inputs"]:
                smp["inputs"][k] = seed
    _, ln = find(wf, "LENGTH")
    if ln:
        for k in ("length", "frames", "num_frames", "video_length"):
            if k in ln["inputs"]:
                ln["inputs"][k] = n_frames
    return wf


def motion_prompt(shot):
    scene = shot["visual_prompt"].replace("[STYLE]", "").strip()
    return (f"{scene} Subtle, gentle, wholesome animation: natural breathing and blinking, "
            "small lifelike gestures, soft breeze in leaves, drifting light and tiny sparkles, "
            "slow cinematic camera push-in. Flat-to-3D cartoon children's storybook style, "
            "warm colors, smooth motion, characters stay on-model.")


def audio_seconds(sid):
    mp3 = BUILD / "audio" / f"shot{sid:02d}.mp3"
    try:
        from mutagen.mp3 import MP3
        return float(MP3(str(mp3)).info.length)
    except Exception:
        return 5.0


def queue_and_fetch(wf, out_path: Path):
    cid = uuid.uuid4().hex
    res = json.loads(http("POST", "/prompt",
                          json.dumps({"prompt": wf, "client_id": cid}).encode(),
                          {"Content-Type": "application/json"}))
    pid = res["prompt_id"]
    while True:
        time.sleep(3)
        hist = json.loads(http("GET", f"/history/{pid}") or b"{}")
        if pid in hist:
            outs = hist[pid].get("outputs", {})
            for node in outs.values():
                vids = node.get("gifs") or node.get("videos") or node.get("images") or []
                for v in vids:
                    if str(v.get("filename", "")).lower().endswith((".mp4", ".webm", ".mov")):
                        q = urllib.parse.urlencode({"filename": v["filename"],
                                                    "subfolder": v.get("subfolder", ""),
                                                    "type": v.get("type", "output")})
                        out_path.write_bytes(http("GET", f"/view?{q}"))
                        return True
            return False


def main():
    if not WORKFLOW.exists():
        raise SystemExit(f"missing workflow template: {WORKFLOW}\n"
                         "Export ComfyUI's LTX-2 I2V template (Workflow ▸ Export API) here, "
                         "and title nodes KEYFRAME/POSITIVE/NEGATIVE/SAMPLER/LENGTH.")
    template = json.loads(WORKFLOW.read_text(encoding="utf-8"))
    log(f"ComfyUI={COMFY}  keyframes={KEYFRAMES}  shots={len(SHOTS)}")
    done, failed = [], []
    for shot in SHOTS:
        sid = int(shot["scene_id"])
        out = OUT / f"shot{sid:02d}.mp4"
        if out.exists():
            log(f"shot {sid:02d} exists, skip")
            continue
        kf = KEYFRAMES / f"shot{sid:02d}.jpg"
        if not kf.exists():
            log(f"shot {sid:02d} no keyframe at {kf}, skip")
            failed.append(sid)
            continue
        dur = max(MIN_SEC, min(audio_seconds(sid) + PAD_SEC, MAX_SEC))
        n_frames = int(dur * FPS)
        try:
            name = upload_image(kf)
            wf = patch(json.loads(json.dumps(template)), name, motion_prompt(shot),
                       7000 + sid, n_frames)
            t = time.time()
            if queue_and_fetch(wf, out):
                log(f"shot {sid:02d} animated {dur:.1f}s ({time.time()-t:.0f}s)")
                done.append(sid)
            else:
                log(f"shot {sid:02d} no video in outputs")
                failed.append(sid)
        except Exception as e:
            log(f"shot {sid:02d} FAILED: {repr(e)[:160]}")
            failed.append(sid)
    log(f"DONE. animated={len(done)} {done}  failed={failed}")


if __name__ == "__main__":
    main()
