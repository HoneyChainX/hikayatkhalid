#!/usr/bin/env python3
"""
Produce one episode end-to-end — the single entry point.

Runs the pipeline stages in order, auto-selecting whichever backend is available,
and skipping stages whose outputs already exist. Designed so that the moment a
GPU box or a generation subscription is live, ONE command produces the episode:

    export EPISODE=ep01
    # plus whatever keys you have (see .env.example); then:
    python3 pipeline/produce_episode.py

Stages (override with STAGES="animate,assemble"):
  keyframes  rerender_balancer.py        (HF / NVIDIA / Gemini)  -> build/<ep>/img
  voices     revoice_elevenlabs.py       (ElevenLabs)            -> build/<ep>/audio
  animate    animate_fal.py | comfy/animate_episode.py
                                          (FAL_KEY | COMFY_URL)   -> build/<ep>/clips_anim
  assemble   build_ep01.py               (ffmpeg; animated if present, else stills)
  persist    upload_to_supabase.py       (SUPABASE_SERVICE_ROLE_KEY, optional)
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EP = os.environ.get("EPISODE", "ep01")
BUILD = ROOT / "build" / EP
PY = sys.executable
STAGES = [s.strip() for s in os.environ.get(
    "STAGES", "keyframes,voices,animate,assemble,persist").split(",") if s.strip()]


def n(globpat):
    d = BUILD / globpat.split("/")[0]
    return len(list(d.glob(globpat.split("/", 1)[1]))) if d.exists() else 0


def env(*names):
    return next((os.environ[x] for x in names if os.environ.get(x)), None)


def run(script, why):
    print(f"\n\033[96m==> {why}: {script}\033[0m", flush=True)
    r = subprocess.run([PY, str(ROOT / script)], env={**os.environ, "EPISODE": EP})
    if r.returncode != 0:
        print(f"\033[91m   stage failed ({script}); stopping.\033[0m")
        sys.exit(r.returncode)


def main():
    print(f"=== producing {EP} ===  stages: {STAGES}")

    if "keyframes" in STAGES:
        if n("img/*.jpg") >= 1 and env() is None:
            print("==> keyframes: present, skip")
        elif env("HF_TOKEN", "NVIDIA_API_KEY", "GEMINI_API_KEY"):
            run("pipeline/rerender_balancer.py", "Stage 2 keyframes")
        else:
            print("\033[93m!! keyframes: no backend key (HF_TOKEN/NVIDIA_API_KEY/GEMINI_API_KEY) "
                  "and none on disk — run Workflow B or add a key.\033[0m")

    if "voices" in STAGES:
        if n("audio/*.mp3") >= 1:
            print("==> voices: present, skip")
        elif os.environ.get("ELEVENLABS_API_KEY"):
            run("pipeline/revoice_elevenlabs.py", "Stage 5 voices")
        else:
            print("\033[93m!! voices: set ELEVENLABS_API_KEY (or pre-place audio).\033[0m")

    if "animate" in STAGES:
        run("pipeline/route_shots.py", "Stage 3a route shots (hybrid: puppet / wan_s2v / wan_i2v)")
        if env("DASHSCOPE_KEY", "DASHSCOPE_API_KEY"):
            # Hybrid (chosen): Wan handles story shots (lip-sync + motion); modern-frame
            # cast dialogue is produced in Adobe Character Animator and dropped into clips_anim/.
            run("pipeline/animate_wan.py", "Stage 3 animate (hybrid · Wan S2V/i2v for story shots)")
            print("\033[96m   note: puppet (modern-frame cast) shots come from Adobe Character "
                  "Animator → place them in build/<ep>/clips_anim/shotNN.mp4\033[0m")
        elif env("FAL_KEY", "FAL_API_KEY"):
            run("pipeline/animate_fal.py", "Stage 3 animate (Path A · fal.ai cloud, all shots)")
        elif os.environ.get("COMFY_URL"):
            run("pipeline/comfy/animate_episode.py", "Stage 3 animate (Path B · ComfyUI GPU)")
        elif n("clips_anim/*.mp4") >= 1:
            print("==> animate: clips already present (e.g. Character Animator puppets); "
                  "no cloud backend set — assembling with what's on disk.")
        else:
            print("\033[93m!! animate: no DASHSCOPE_KEY / FAL_KEY / COMFY_URL and no clips on disk "
                  "— assembling stills draft instead of animation.\033[0m")

    if "assemble" in STAGES:
        run("pipeline/build_ep01.py", "Stage 6 assemble")

    if "persist" in STAGES and os.environ.get("SUPABASE_SERVICE_ROLE_KEY"):
        run("pipeline/upload_to_supabase.py", "Persist to Supabase")

    mp4 = BUILD / f"{EP if EP != 'ep01' else 'ep01'}.mp4"
    final = BUILD / "ep01.mp4"   # build_ep01.py writes ep01.mp4 in BUILD
    out = final if final.exists() else mp4
    print(f"\n\033[92m=== {EP} done ===\033[0m  ->  {out}")


if __name__ == "__main__":
    main()
