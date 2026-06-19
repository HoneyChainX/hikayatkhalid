#!/usr/bin/env python3
"""
FREE Khalid-consistency pass using Flux.1 Kontext (open weights) on public
Hugging Face Spaces — no API key, no credits.

It edits a fixed reference of Khalid (khalid_v1.png, placed on a 16:9 white
canvas) into each scene, so Khalid's face / kufi / thobe stay identical
shot-to-shot. Only shots that contain KHALID are re-rendered; the others keep
their flux images. Outputs overwrite build/ep01/img/shotNN.jpg (originals are
backed up to build/ep01/img_flux/). Re-run to resume — finished shots are skipped.

Anonymous HF ZeroGPU has a small per-IP quota, so this ROTATES across several
mirror Kontext Spaces; when one is out of quota it moves to the next. For an
uninterrupted run, set HF_TOKEN (free) or KONTEXT_SPACES to your own list.

    pip install gradio_client imageio-ffmpeg huggingface_hub
    python3 pipeline/rerender_khalid_kontext.py
    python3 pipeline/build_ep01.py          # restitch the MP4 with the new frames

Env: KONTEXT_SPACES="a,b,c" (override mirror list), KHALID_SHOTS="1,4,26" (limit).
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
CANVAS = BUILD / "free" / "khalid_canvas.png"

_DEFAULT_SPACES = [
    "black-forest-labs/FLUX.1-Kontext-Dev",
    "black-forest-labs/FLUX.1-Kontext-dev",
    "Nymbo/FLUX.1-Kontext-Dev",
    "akhaliq/FLUX.1-Kontext-dev",
    "ginigen/FLUX.1-Kontext-Dev",
    "joztt31/black-forest-labs-FLUX.1-Kontext-dev",
    "Swagcrew/black-forest-labs-FLUX.1-Kontext-dev",
    "coasttmetal/black-forest-labs-FLUX.1-Kontext-dev",
    "Gvqlo10c/black-forest-labs-FLUX.1-Kontext-dev",
]
SPACES = [s for s in os.environ.get("KONTEXT_SPACES", "").split(",") if s] or _DEFAULT_SPACES

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
    log(f"spaces={len(SPACES)}  Khalid shots: {[s['scene_id'] for s in targets]}")

    if not (IMG.parent / "img_flux").exists():
        shutil.copytree(IMG, IMG.parent / "img_flux")
        log("backed up flux images -> build/ep01/img_flux/")

    sidx = 0
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
        for attempt in range(len(SPACES) + 2):
            try:
                if client is None:
                    # gradio_client auto-reads HF_TOKEN from the env when set;
                    # pass it explicitly only if this version supports the kwarg.
                    tok = os.environ.get("HF_TOKEN")
                    try:
                        client = Client(SPACES[sidx], hf_token=tok, verbose=False) if tok \
                            else Client(SPACES[sidx], verbose=False)
                    except TypeError:
                        client = Client(SPACES[sidx], verbose=False)
                    log(f"  connected to {SPACES[sidx]}")
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
                log(f"shot {sid:02d} OK via {SPACES[sidx]} ({time.time()-t:.0f}s)")
                ok = True
                break
            except Exception as e:
                msg = repr(e)[:140]
                sidx = (sidx + 1) % len(SPACES)        # rotate to next mirror
                client = None
                log(f"shot {sid:02d} attempt {attempt+1} failed: {msg} -> next space {SPACES[sidx]}")
                time.sleep(5)
        (done if ok else failed).append(sid)
        time.sleep(1)

    log(f"DONE. rendered={len(done)} {done}  failed={failed}")
    if failed:
        log("failed shots kept their flux image; re-run to retry just those.")


if __name__ == "__main__":
    main()
