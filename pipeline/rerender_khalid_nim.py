#!/usr/bin/env python3
"""
Khalid-consistency pass via NVIDIA NIM's hosted FLUX.1 Kontext (image editing).

Same idea as rerender_khalid_kontext.py (edit the locked khalid_v1.png reference
into each scene so Khalid stays identical), but calls NVIDIA's cloud API instead
of a Hugging Face Space — no shared anonymous GPU quota, runs straight through on
NVIDIA's free credits.

SECRETS: the NVIDIA key is read from the environment ONLY. Never hard-code or
commit it; revoke/rotate it afterwards.

    export NVIDIA_API_KEY="nvapi-..."          # free key from build.nvidia.com
    pip install requests imageio-ffmpeg
    python3 pipeline/rerender_khalid_nim.py
    python3 pipeline/build_ep01.py             # restitch the MP4

Env: KHALID_SHOTS="1,4,26" to limit which shots; NIM_MODEL to override the model.
"""
import base64
import json
import os
import random
import shutil
import subprocess
import time
from pathlib import Path

import imageio_ffmpeg
import requests

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "ep01"
IMG = BUILD / "img"
FREE = BUILD / "nim"
FREE.mkdir(parents=True, exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
CANVAS = BUILD / "free" / "khalid_canvas.png"

KEY = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVIDIA_NIM_API_KEY")
MODEL = os.environ.get("NIM_MODEL", "black-forest-labs/flux.1-kontext-dev")
INVOKE = f"https://ai.api.nvidia.com/v1/genai/{MODEL}"

SHOTS = json.loads((ROOT / "pipeline" / "ep01_shotlist.json").read_text(encoding="utf-8"))
ONLY = {int(x) for x in os.environ.get("KHALID_SHOTS", "").split(",") if x.strip().isdigit()}


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def ensure_canvas():
    if CANVAS.exists():
        return
    CANVAS.parent.mkdir(parents=True, exist_ok=True)
    ref = BUILD / "khalid_ref.png"
    front = BUILD / "free" / "khalid_front.png"
    subprocess.run([FFMPEG, "-y", "-i", str(ref), "-vf", "crop=430:740:18:14", str(front)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([FFMPEG, "-y", "-i", str(front), "-vf",
                    "scale=-1:660,pad=1280:720:120:30:white", str(CANVAS)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def edit_prompt(shot):
    vp = shot["visual_prompt"]
    scene = vp.replace("[STYLE]", "").strip()
    extra = []
    if "NOOR" in vp:
        extra.append("the little girl NOOR has a light-blue headscarf and a light-blue dress")
    if "TETA" in vp:
        extra.append("the grandmother TETA has a cream hijab, thin glasses and olive clothes")
    extras = (" In this scene " + "; ".join(extra) + ".") if extra else ""
    return ("Keep this same boy character completely unchanged — identical face, olive-and-gold "
            "kufi cap, black thobe with gold embroidery, small brown satchel. Replace the plain "
            f"white background with this full scene (the boy is KHALID): {scene}" + extras +
            " Do not add any other people who are not described. Flat 2D cartoon children's "
            "storybook style, warm cheerful colors, simple background, no text or letters.")


def output_b64(data):
    """NVIDIA GenAI image responses vary; pull the base64 from the common shapes."""
    if isinstance(data, dict):
        if "artifacts" in data and data["artifacts"]:
            a = data["artifacts"][0]
            return a.get("base64") or a.get("b64_json") or a.get("image")
        for k in ("image", "b64_json", "images"):
            if k in data:
                v = data[k]
                return v[0] if isinstance(v, list) else v
    return None


def call_nim(prompt, canvas_b64, tries=4):
    payload = {
        "prompt": prompt,
        "image": f"data:image/png;base64,{canvas_b64}",
        "cfg_scale": 2.5,
        "aspect_ratio": "16:9",
        "steps": 30,
        "seed": random.randint(0, 2_000_000_000),
        "samples": 1,
    }
    headers = {"Authorization": f"Bearer {KEY}", "Accept": "application/json",
               "Content-Type": "application/json"}
    for i in range(tries):
        try:
            r = requests.post(INVOKE, headers=headers, json=payload, timeout=180)
            if r.status_code == 200:
                b64 = output_b64(r.json())
                if b64:
                    return b64.split(",", 1)[-1]  # strip any data-uri prefix
                log(f"  no image in response: {str(r.json())[:160]}")
            else:
                log(f"  HTTP {r.status_code}: {r.text[:160]}")
        except Exception as e:
            log(f"  error try {i+1}: {repr(e)[:140]}")
        time.sleep(5 * (i + 1))
    return None


def main():
    if not KEY:
        raise SystemExit("set NVIDIA_API_KEY in your environment (free key at build.nvidia.com).")
    ensure_canvas()
    canvas_b64 = base64.b64encode(CANVAS.read_bytes()).decode()
    targets = [s for s in SHOTS if "KHALID" in s["visual_prompt"]]
    if ONLY:
        targets = [s for s in targets if int(s["scene_id"]) in ONLY]
    log(f"model={MODEL}  Khalid shots: {[s['scene_id'] for s in targets]}")

    if not (IMG.parent / "img_flux").exists():
        shutil.copytree(IMG, IMG.parent / "img_flux")
        log("backed up flux images -> build/ep01/img_flux/")

    done, failed = [], []
    for shot in targets:
        sid = int(shot["scene_id"])
        png = FREE / f"shot{sid:02d}.png"
        out = IMG / f"shot{sid:02d}.jpg"
        if png.exists():
            log(f"shot {sid:02d} already done, skip")
            continue
        t = time.time()
        b64 = call_nim(edit_prompt(shot), canvas_b64)
        if not b64:
            log(f"shot {sid:02d} FAILED (kept flux image)")
            failed.append(sid)
            continue
        png.write_bytes(base64.b64decode(b64))
        subprocess.run([FFMPEG, "-y", "-i", str(png), "-q:v", "3", str(out)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        log(f"shot {sid:02d} OK ({time.time()-t:.0f}s)")
        done.append(sid)
        time.sleep(1)

    log(f"DONE. rendered={len(done)} {done}  failed={failed}")


if __name__ == "__main__":
    main()
