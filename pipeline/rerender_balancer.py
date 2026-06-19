#!/usr/bin/env python3
"""
Smart multi-backend balancer for the Khalid-consistency re-render.

The same job (edit the locked khalid_v1.png reference into each scene so Khalid
stays identical) is sent to whichever FREE identity-locking backend is healthy,
spreading load so no single free quota is the bottleneck. Each backend is
health-gated: on a quota/error it goes into cooldown and the balancer uses the
others; it is picked up again automatically when its cooldown expires.

Backends (enabled when reachable / their key is present):
  - hf      Flux.1 Kontext on public HF Spaces (anonymous, or set HF_TOKEN)
  - nim     NVIDIA NIM hosted Flux.1 Kontext  (set NVIDIA_API_KEY)
  - gemini  Gemini 2.5 Flash Image / "nano-banana" (set GEMINI_API_KEY)

    pip install requests gradio_client imageio-ffmpeg
    python3 pipeline/rerender_balancer.py
    python3 pipeline/build_ep01.py        # restitch with the consistent frames

Resumable: shots with an output already present are skipped. Env:
  ENABLE_BACKENDS="hf,nim,gemini"  (default all)  ·  KHALID_SHOTS="1,4,26"
  MAX_RUNTIME_MIN=180
"""
import base64
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "ep01"
IMG = BUILD / "img"
OUT = BUILD / "balancer"
OUT.mkdir(parents=True, exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
CANVAS = BUILD / "free" / "khalid_canvas.png"

SHOTS = json.loads((ROOT / "pipeline" / "ep01_shotlist.json").read_text(encoding="utf-8"))
ONLY = {int(x) for x in os.environ.get("KHALID_SHOTS", "").split(",") if x.strip().isdigit()}
ENABLED = set(os.environ.get("ENABLE_BACKENDS", "hf,nim,gemini").split(","))
MAX_RUNTIME = float(os.environ.get("MAX_RUNTIME_MIN", "180")) * 60

HF_SPACES = ["black-forest-labs/FLUX.1-Kontext-Dev", "black-forest-labs/FLUX.1-Kontext-dev",
             "Nymbo/FLUX.1-Kontext-Dev", "akhaliq/FLUX.1-Kontext-dev"]
NIM_FN = "c173de37-785b-4487-8db5-b0ea0013fa6d"


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


# --------------------------------------------------------------------------- backends
class QuotaError(Exception):
    pass


class Backend:
    """A free image-editing provider with simple health/cooldown tracking."""
    def __init__(self, name, fn, cooldown):
        self.name, self.fn, self.cooldown = name, fn, cooldown
        self.until = 0.0
        self.ok = self.fail = 0

    def healthy(self):
        return time.time() >= self.until

    def run(self, shot, png_out: Path):
        data = self.fn(shot)                 # returns image bytes
        png_out.write_bytes(data)
        self.ok += 1


# -- HF Kontext (gradio) ----
_hf = {"client": None, "idx": 0}


def hf_gen(shot):
    from gradio_client import Client, handle_file
    if _hf["client"] is None:
        tok = os.environ.get("HF_TOKEN")
        sp = HF_SPACES[_hf["idx"] % len(HF_SPACES)]
        try:
            _hf["client"] = Client(sp, hf_token=tok, verbose=False) if tok else Client(sp, verbose=False)
        except TypeError:
            _hf["client"] = Client(sp, verbose=False)
    try:
        res = _hf["client"].predict(input_image=handle_file(str(CANVAS)), prompt=edit_prompt(shot),
                                    seed=0, randomize_seed=True, guidance_scale=2.5, steps=28,
                                    api_name="/infer")
        p = res[0]["path"] if isinstance(res, (list, tuple)) and isinstance(res[0], dict) else \
            (res[0] if isinstance(res, (list, tuple)) else res)
        return Path(p).read_bytes()
    except Exception as e:
        _hf["client"] = None
        _hf["idx"] += 1
        if "quota" in str(e).lower():
            raise QuotaError(str(e)[:80])
        raise


# -- NVIDIA NIM Kontext ----
def nim_gen(shot):
    import requests
    key = os.environ.get("NVIDIA_API_KEY") or os.environ.get("NVIDIA_NIM_API_KEY")
    if not key:
        raise QuotaError("no NVIDIA_API_KEY")
    H = {"Authorization": f"Bearer {key}"}
    a = requests.post("https://api.nvcf.nvidia.com/v2/nvcf/assets",
                      headers={**H, "Content-Type": "application/json", "accept": "application/json"},
                      json={"contentType": "image/png", "description": "k"}, timeout=60).json()
    aid = a["assetId"]
    requests.put(a["uploadUrl"], data=CANVAS.read_bytes(),
                 headers={"Content-Type": "image/png", "x-amz-meta-nvcf-asset-description": "k"}, timeout=120)
    body = {"prompt": edit_prompt(shot), "image": f"data:image/png;example_id,{aid}",
            "cfg_scale": 2.5, "aspect_ratio": "match_input_image", "steps": 30, "seed": 1}
    r = requests.post(f"https://api.nvcf.nvidia.com/v2/nvcf/pexec/functions/{NIM_FN}",
                      headers={**H, "Accept": "application/json", "Content-Type": "application/json",
                               "NVCF-INPUT-ASSET-REFERENCES": aid}, json=body, timeout=180)
    if r.status_code != 200:
        raise QuotaError(f"nim {r.status_code} {r.headers.get('nvcf-status','')}")
    j = r.json()
    b64 = (j.get("artifacts") or [{}])[0].get("base64") or j.get("image")
    return base64.b64decode(b64.split(",", 1)[-1])


# -- Gemini 2.5 Flash Image (nano-banana) ----
def gemini_gen(shot):
    import requests
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise QuotaError("no GEMINI_API_KEY")
    model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    cb64 = base64.b64encode(CANVAS.read_bytes()).decode()
    body = {"contents": [{"parts": [{"text": edit_prompt(shot)},
                                    {"inline_data": {"mime_type": "image/png", "data": cb64}}]}]}
    r = requests.post(url, json=body, timeout=120)
    if r.status_code != 200:
        raise QuotaError(f"gemini {r.status_code} {r.text[:80]}")
    for part in r.json()["candidates"][0]["content"]["parts"]:
        d = part.get("inline_data") or part.get("inlineData")
        if d:
            return base64.b64decode(d["data"])
    raise QuotaError("gemini: no image in response")


# --------------------------------------------------------------------------- scheduler
def main():
    if not CANVAS.exists():
        ensure_canvas()
    all_backends = [
        Backend("hf", hf_gen, cooldown=1500),       # anonymous ZeroGPU resets ~25 min
        Backend("nim", nim_gen, cooldown=600),       # NVIDIA worker errors -> back off 10 min
        Backend("gemini", gemini_gen, cooldown=120),
    ]
    backends = [b for b in all_backends if b.name in ENABLED]
    log(f"backends: {[b.name for b in backends]}")

    if not (IMG.parent / "img_flux").exists():
        shutil.copytree(IMG, IMG.parent / "img_flux")
        log("backed up flux images -> build/ep01/img_flux/")

    pending = [s for s in SHOTS if "KHALID" in s["visual_prompt"]
               and not (OUT / f"shot{int(s['scene_id']):02d}.png").exists()]
    if ONLY:
        pending = [s for s in pending if int(s["scene_id"]) in ONLY]
    log(f"pending Khalid shots: {[s['scene_id'] for s in pending]}")

    start = time.time()
    while pending and time.time() - start < MAX_RUNTIME:
        progressed = False
        for shot in list(pending):
            sid = int(shot["scene_id"])
            for b in backends:
                if not b.healthy():
                    continue
                try:
                    t = time.time()
                    png = OUT / f"shot{sid:02d}.png"
                    b.run(shot, png)
                    subprocess.run([FFMPEG, "-y", "-i", str(png), "-q:v", "3",
                                    str(IMG / f"shot{sid:02d}.jpg")],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    log(f"shot {sid:02d} OK via {b.name} ({time.time()-t:.0f}s)")
                    pending.remove(shot)
                    progressed = True
                    break
                except Exception as e:
                    b.fail += 1
                    b.until = time.time() + b.cooldown
                    log(f"  {b.name} failed shot {sid:02d}: {str(e)[:90]} -> cooldown {b.cooldown}s")
            time.sleep(1)
        if not progressed:
            nxt = min((b.until for b in backends), default=time.time() + 60)
            wait = max(5, min(nxt - time.time(), 1500))
            log(f"all backends cooling; sleeping {wait:.0f}s ({len(pending)} shots left)")
            time.sleep(wait)

    log(f"DONE. remaining={[int(s['scene_id']) for s in pending]}  "
        f"stats={{ {', '.join(f'{b.name}:{b.ok}ok/{b.fail}fail' for b in backends)} }}")


if __name__ == "__main__":
    main()
