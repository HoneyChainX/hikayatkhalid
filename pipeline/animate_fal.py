#!/usr/bin/env python3
"""
Path A — animate keyframes into motion clips via fal.ai (cloud, no GPU).

Stage 3 alternative to the ComfyUI/RTX path: same job (consistent keyframe ->
motion clip), but on a pay-per-use API. Default engine: Seedance 2.0 Fast
(reference-driven, ~$0.022/s). Mirrors pipeline/comfy/animate_episode.py's
inputs/outputs so the rest of the pipeline is identical.

    export FAL_KEY=...                     # from fal.ai
    export EPISODE=ep01
    python3 pipeline/animate_fal.py        # -> build/<ep>/clips_anim/shotNN.mp4

Env: FAL_MODEL (default Seedance Lite i2v), KEYFRAME_DIR, CLIP_FPS.
"""
import base64
import json
import os
import time
import urllib.request
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
EP = os.environ.get("EPISODE", "ep01")
BUILD = ROOT / "build" / EP
KEYFRAMES = Path(os.environ.get("KEYFRAME_DIR", BUILD / "img"))
OUT = BUILD / "clips_anim"
OUT.mkdir(parents=True, exist_ok=True)

KEY = os.environ.get("FAL_KEY") or os.environ.get("FAL_API_KEY")
MODEL = os.environ.get("FAL_MODEL", "fal-ai/bytedance/seedance/v1/lite/image-to-video")
FPS = int(os.environ.get("CLIP_FPS", 24))
PAD, MIN_S, MAX_S = 0.8, 3.0, 10.0
NEG = "text, letters, watermark, blurry, deformed, scary, photorealistic"


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def shots():
    for p in (BUILD / "shotlist.json", ROOT / "pipeline" / f"{EP}_shotlist.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise SystemExit(f"no shotlist for {EP}")


def motion_prompt(shot):
    scene = shot["visual_prompt"].replace("[STYLE]", "").strip()
    return (f"{scene} Gentle wholesome animation: soft natural motion, breathing and blinking, "
            "breeze in the leaves, drifting light, slow cinematic push-in. Flat-to-3D cartoon "
            "children's storybook style, warm colors, characters stay on-model.")


def audio_seconds(sid):
    try:
        from mutagen.mp3 import MP3
        return float(MP3(str(BUILD / "audio" / f"shot{sid:02d}.mp3")).info.length)
    except Exception:
        return 5.0


def data_uri(p: Path):
    return "data:image/jpeg;base64," + base64.b64encode(p.read_bytes()).decode()


def submit(prompt, img_uri, seconds):
    body = {"prompt": prompt, "image_url": img_uri,
            "duration": str(int(round(seconds))), "negative_prompt": NEG,
            "resolution": os.environ.get("FAL_RES", "720p")}
    h = {"Authorization": f"Key {KEY}", "Content-Type": "application/json"}
    r = requests.post(f"https://queue.fal.run/{MODEL}", headers=h, json=body, timeout=60)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"submit {r.status_code}: {r.text[:160]}")
    return r.json()


def poll(job, tries=120):
    h = {"Authorization": f"Key {KEY}"}
    status_url = job.get("status_url")
    resp_url = job.get("response_url")
    for _ in range(tries):
        s = requests.get(status_url, headers=h, timeout=30).json()
        if s.get("status") == "COMPLETED":
            out = requests.get(resp_url, headers=h, timeout=60).json()
            vid = (out.get("video") or {}).get("url") or out.get("video_url")
            if not vid and isinstance(out.get("videos"), list):
                vid = out["videos"][0].get("url")
            return vid
        if s.get("status") in ("FAILED", "ERROR"):
            raise RuntimeError(f"job failed: {str(s)[:160]}")
        time.sleep(5)
    raise TimeoutError("fal job timed out")


def main():
    if not KEY:
        raise SystemExit("set FAL_KEY in the environment (fal.ai).")
    SH = shots()
    log(f"model={MODEL}  episode={EP}  keyframes={KEYFRAMES}  shots={len(SH)}")
    done, failed = [], []
    for shot in SH:
        sid = int(shot["scene_id"])
        out = OUT / f"shot{sid:02d}.mp4"
        if out.exists():
            log(f"shot {sid:02d} exists, skip"); continue
        kf = KEYFRAMES / f"shot{sid:02d}.jpg"
        if not kf.exists():
            log(f"shot {sid:02d} no keyframe, skip"); failed.append(sid); continue
        secs = max(MIN_S, min(audio_seconds(sid) + PAD, MAX_S))
        try:
            t = time.time()
            url = poll(submit(motion_prompt(shot), data_uri(kf), secs))
            urllib.request.urlretrieve(url, out)
            log(f"shot {sid:02d} animated {secs:.1f}s ({time.time()-t:.0f}s)")
            done.append(sid)
        except Exception as e:
            log(f"shot {sid:02d} FAILED: {repr(e)[:160]}"); failed.append(sid)
    log(f"DONE. animated={len(done)} {done}  failed={failed}")


if __name__ == "__main__":
    main()
