#!/usr/bin/env python3
"""
Re-voice ep01 with real ElevenLabs Arabic voices (replaces the gTTS draft audio).

Per-speaker voices come from pipeline/characters.json -> elevenlabs_voices
(Khalid = the project's "Khalid MJ" voice; narrator = an Egyptian-Arabic voice;
Noor/Teta = bright/warm voices via the multilingual model). Output overwrites
build/ep01/audio/shotNN.mp3, then re-run build_ep01.py to restitch.

SECRETS: reads ELEVENLABS_API_KEY from the environment only.

    export ELEVENLABS_API_KEY="..."
    pip install requests
    python3 pipeline/revoice_elevenlabs.py && python3 pipeline/build_ep01.py
"""
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "ep01"
AUD = BUILD / "audio"
AUD.mkdir(parents=True, exist_ok=True)

KEY = os.environ.get("ELEVENLABS_API_KEY")
MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_multilingual_v2")
CHARS = json.loads((ROOT / "pipeline" / "characters.json").read_text(encoding="utf-8"))
VOICES = CHARS["elevenlabs_voices"]
SHOTS = json.loads((ROOT / "pipeline" / "ep01_shotlist.json").read_text(encoding="utf-8"))

PAREN = re.compile(r"\([^)]*\)|（[^）]*）")


def clean_line(text):
    t = PAREN.sub(" ", text)
    t = t.replace("\\n", " ، ").replace("\n", " ، ").replace('"', " ").replace("«", " ").replace("»", " ")
    return re.sub(r"\s+", " ", t).strip() or "..."


def tts(text, voice_id, out: Path, tries=4):
    body = {"text": text, "model_id": MODEL,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0}}
    h = {"xi-api-key": KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"}
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    for i in range(tries):
        try:
            r = requests.post(url, headers=h, json=body, timeout=120)
            if r.status_code == 200 and len(r.content) > 1200:
                out.write_bytes(r.content)
                return True
            print(f"  tts {r.status_code}: {r.text[:120]}", flush=True)
        except Exception as e:
            print(f"  tts error {i+1}: {repr(e)[:120]}", flush=True)
        time.sleep(3 * (i + 1))
    return False


def main():
    if not KEY:
        sys.exit("set ELEVENLABS_API_KEY in the environment.")
    ok = bad = 0
    for shot in SHOTS:
        sid = int(shot["scene_id"])
        speaker = shot.get("speaker", "")
        voice = VOICES.get(speaker, VOICES["_default"])
        text = clean_line(shot["line"])
        out = AUD / f"shot{sid:02d}.mp3"
        if tts(text, voice, out):
            print(f"shot {sid:02d} [{speaker}] -> {voice}  ({len(text)} chars)", flush=True)
            ok += 1
        else:
            print(f"shot {sid:02d} FAILED (kept previous audio)", flush=True)
            bad += 1
        time.sleep(0.3)
    print(f"DONE. voiced={ok} failed={bad}", flush=True)


if __name__ == "__main__":
    main()
