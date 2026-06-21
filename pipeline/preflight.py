#!/usr/bin/env python3
"""
Preflight doctor — "is everything ready to produce an episode?"

Reports which production PATH is runnable given the current environment, what's
present, and what's missing. Reads keys/knobs from the environment only.

    python3 pipeline/preflight.py            # check ep01
    EPISODE=ep02 python3 pipeline/preflight.py
"""
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EP = os.environ.get("EPISODE", "ep01")
BUILD = ROOT / "build" / EP

OK, NO, WARN = "\033[92m✓\033[0m", "\033[91m✗\033[0m", "\033[93m!\033[0m"


def has(*names):
    return next((n for n in names if os.environ.get(n)), None)


def count(globpat):
    p = BUILD / globpat.split("/")[0]
    return len(list(p.glob(globpat.split("/", 1)[1]))) if p.exists() else 0


def main():
    print(f"\n=== Hikayat Khalid · preflight · episode {EP} ===\n")

    # tooling
    import importlib.util as iu
    def mod(m): return iu.find_spec(m) is not None
    try:
        import imageio_ffmpeg  # noqa
        ff = True
    except Exception:
        ff = False
    print("Tooling")
    print(f"  {OK if ff else NO} ffmpeg (imageio-ffmpeg)")
    for m in ("requests", "gradio_client", "gtts", "mutagen"):
        print(f"  {OK if mod(m) else WARN} python: {m}")

    # inputs
    shotlist = (BUILD / "shotlist.json")
    snap = ROOT / "pipeline" / f"{EP}_shotlist.json"
    have_shots = shotlist.exists() or snap.exists()
    n_shots = 0
    for p in (shotlist, snap):
        if p.exists():
            n_shots = len(json.loads(p.read_text(encoding="utf-8"))); break
    print("\nInputs")
    print(f"  {OK if have_shots else NO} shotlist ({n_shots} shots)" if have_shots
          else f"  {NO} shotlist — run Workflow A/B for {EP} first")
    print(f"  {OK if (BUILD/'khalid_ref.png').exists() or (ROOT/'docs/samples').exists() else WARN} character reference(s)")

    # keys
    print("\nCredentials (env only)")
    rows = [
        ("ELEVENLABS_API_KEY",   "voices (ElevenLabs)"),
        ("HF_TOKEN",             "keyframes via HF Kontext / lifts GPU cap"),
        ("NVIDIA_API_KEY",       "keyframes via NVIDIA NIM"),
        ("GEMINI_API_KEY",       "keyframes via Gemini (needs billing for images)"),
        ("FAL_KEY",              "cloud animation (Path A: Seedance/Kling)"),
        ("COMFY_URL",            "GPU animation (Path B: ComfyUI box)"),
        ("SUPABASE_SERVICE_ROLE_KEY", "persist assets to Supabase"),
    ]
    for env, desc in rows:
        v = has(env)
        print(f"  {OK if v else WARN} {env:28} {desc}")

    # path readiness
    kf_ready = bool(has("HF_TOKEN", "NVIDIA_API_KEY", "GEMINI_API_KEY")) or count("img/*.jpg")
    animate_cloud = bool(has("FAL_KEY"))
    animate_gpu = bool(has("COMFY_URL"))
    voices_ready = bool(has("ELEVENLABS_API_KEY")) or count("audio/*.mp3")
    print("\nAssets on disk")
    print(f"  keyframes:  {count('img/*.jpg')}     animated clips: {count('clips_anim/*.mp4')}     voices: {count('audio/*.mp3')}")

    print("\nReady to run?")
    def line(label, ok, why=""):
        print(f"  {OK if ok else NO} {label}{(' — ' + why) if (why and not ok) else ''}")
    line("Stage 2 keyframes", kf_ready, "add HF_TOKEN / NVIDIA_API_KEY / GEMINI_API_KEY")
    line("Stage 3 animate · Path A cloud", animate_cloud, "add FAL_KEY")
    line("Stage 3 animate · Path B GPU", animate_gpu, "start ComfyUI box, set COMFY_URL")
    line("Stage 5 voices", voices_ready, "add ELEVENLABS_API_KEY")
    line("Stage 6 assemble", ff, "install imageio-ffmpeg")

    can_full = have_shots and kf_ready and (animate_cloud or animate_gpu) and voices_ready and ff
    print("\n" + ("=" * 52))
    if can_full:
        print(f"{OK} FULL animated pipeline is READY for {EP}.")
        print("   run:  python3 pipeline/produce_episode.py")
    else:
        path = "Path A (cloud)" if animate_cloud else ("Path B (GPU)" if animate_gpu else "an animation backend")
        print(f"{WARN} Not fully ready. Closest: add a key for {path} (+ keyframe key + ELEVENLABS).")
        print("   draft (stills) still works:  python3 pipeline/build_ep01.py")
    print("=" * 52 + "\n")
    return 0 if can_full else 1


if __name__ == "__main__":
    sys.exit(main())
