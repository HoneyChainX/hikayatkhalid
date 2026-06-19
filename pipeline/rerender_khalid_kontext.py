#!/usr/bin/env python3
"""
FREE Khalid-consistency pass using Flux.1 Kontext (open weights) on a public
Hugging Face Space — no API key, no credits.

It edits a fixed reference of Khalid (khalid_v1.png, placed on a 16:9 white
canvas) into each scene, so Khalid's face / kufi / thobe stay identical
shot-to-shot. Only shots that contain KHALID are re-rendered; the others keep
their flux images. Outputs overwrite build/ep01/img/shotNN.jpg (originals are
backed up to build/ep01/img_flux/). Re-run to resume — finished shots are skipped.

    pip install gradio_client imageio-ffmpeg
    python3 pipeline/rerender_khalid_kontext.py
    python3 pipeline/build_ep01.py          # restitch the MP4 with the new frames

Env: KONTEXT_SPACE (default black-forest-labs/FLUX.1-Kontext-dev),
     KHALID_SHOTS="1,4,26" to limit which shots.
"""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import imageio_ffmpeg
from gradio_client import Client, handle_file

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "ep01"
IMG = BUILD / "img"
FREE = BUILD / "kontext"
FREE.mkdir(parents=True, exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
SPACE = os.environ.get("KONTEXT_SPACE", "black-forest-labs/FLUX.1-Kontext-dev")
CANVAS = BUILD / "free" / "khalid_canvas.png"

SHOTS = json.loads((ROOT / "pipeline" / "ep01_shotlist.json").read_text(encoding="utf-8"))
ONLY = {int(x) for x in os.environ.get("KHALID_SHOTS", "").split(",") if x.strip().isdigit()}


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def ensure_canvas():
    """Front view of Khalid on a 1280x720 white canvas (drives 16:9 output)."""
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
    scene = shot["visual_prompt"].replace("[STYLE]", "").strip()
    return ("Keep this same boy character completely unchanged — identical face, olive-and-gold "
            "kufi cap, black thobe with gold embroidery, small brown satchel. Replace the plain "
            f"white background with this full scene (the boy is KHALID): {scene} "
            "Draw any little girl as NOOR (light-blue headscarf and dress) and any grandmother as "
            "TETA (cream hijab, glasses, olive clothes). Flat 2D cartoon children's storybook "
            "style, warm cheerful colors, simple background, no text or letters.")


def extract(res):
    if isinstance(res, (list, tuple)):
        res = res[0]
    if isinstance(res, dict):
        return res.get("path") or res.get("url")
    return res


def main():
    ensure_canvas()
    targets = [s for s in SHOTS if "KHALID" in s["visual_prompt"]]
    if ONLY:
        targets = [s for s in targets if int(s["scene_id"]) in ONLY]
    log(f"space={SPACE}  Khalid shots to render: {[s['scene_id'] for s in targets]}")

    if not (IMG.parent / "img_flux").exists():
        shutil.copytree(IMG, IMG.parent / "img_flux")
        log("backed up flux images -> build/ep01/img_flux/")

    client = None
    done, failed = [], []
    for shot in targets:
        sid = int(shot["scene_id"])
        webp = FREE / f"shot{sid:02d}.webp"
        out = IMG / f"shot{sid:02d}.jpg"
        if webp.exists():
            log(f"shot {sid:02d} already done, skip")
            continue
        ok = False
        for attempt in range(4):
            try:
                if client is None:
                    client = Client(SPACE, verbose=False)
                t = time.time()
                res = client.predict(
                    input_image=handle_file(str(CANVAS)),
                    prompt=edit_prompt(shot),
                    seed=0, randomize_seed=True, guidance_scale=2.5, steps=28,
                    api_name="/infer")
                p = extract(res)
                shutil.copy(p, webp)
                subprocess.run([FFMPEG, "-y", "-i", str(webp), "-q:v", "3", str(out)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                log(f"shot {sid:02d} OK ({time.time()-t:.0f}s)")
                ok = True
                break
            except Exception as e:
                wait = 10 * (attempt + 1) ** 2
                log(f"shot {sid:02d} attempt {attempt+1} failed: {repr(e)[:160]} -> wait {wait}s")
                client = None
                time.sleep(wait)
        (done if ok else failed).append(sid)
        time.sleep(2)

    log(f"DONE. rendered={len(done)} {done}  failed={failed}")
    if failed:
        log("failed shots kept their flux image; re-run to retry just those.")


if __name__ == "__main__":
    main()
