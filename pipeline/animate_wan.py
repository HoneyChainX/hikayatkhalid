#!/usr/bin/env python3
"""
Stage 3 (story shots) — animate via **Alibaba Wan** on Model Studio / DashScope.

Routing-aware (see pipeline/route_shots.py): this backend handles only the
non-puppet shots —
  • wan_s2v : portrait keyframe + the shot's ElevenLabs audio → **lip-synced** clip
  • wan_i2v : keyframe → motion clip (story-world scenes & faceless-light prophet shots;
              audio is laid over at assembly, NEVER lip-synced)
Puppet shots (modern-frame cast dialogue) are produced in Adobe Character Animator
and dropped into build/<ep>/clips_anim/ separately. Wan = Apache-2.0 (commercial-safe).

    export DASHSCOPE_KEY=...            # Alibaba Cloud Model Studio API key
    export WAN_ASSET_BASE=https://<public-host>/build   # where build/<ep>/ is reachable
    export EPISODE=ep01
    python3 pipeline/route_shots.py     # writes build/<ep>/routing.json
    python3 pipeline/animate_wan.py     # -> build/<ep>/clips_anim/shotNN.mp4

NOTE: DashScope fetches inputs by URL, so keyframes+audio must be HTTP-reachable
(set WAN_ASSET_BASE, or host build/<ep>/). Model IDs/endpoint are env-overridable —
verify against current Model Studio docs (model names evolve). The async submit→poll
flow is stable.
"""
import json
import os
import time
import urllib.request
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
EP = os.environ.get("EPISODE", "ep01")
BUILD = ROOT / "build" / EP
OUT = BUILD / "clips_anim"
OUT.mkdir(parents=True, exist_ok=True)

KEY = os.environ.get("DASHSCOPE_KEY") or os.environ.get("DASHSCOPE_API_KEY")
BASE = os.environ.get("WAN_BASE", "https://dashscope-intl.aliyuncs.com/api/v1")
I2V_MODEL = os.environ.get("WAN_I2V_MODEL", "wan2.2-i2v-flash")   # verify in Model Studio
S2V_MODEL = os.environ.get("WAN_S2V_MODEL", "wan2.2-s2v")         # verify in Model Studio
ASSET_BASE = (os.environ.get("WAN_ASSET_BASE") or "").rstrip("/")
NEG = "text, letters, watermark, blurry, deformed, scary, photorealistic"


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def routing():
    p = BUILD / "routing.json"
    if not p.exists():
        raise SystemExit("run pipeline/route_shots.py first (no routing.json).")
    return json.loads(p.read_text(encoding="utf-8"))


def shotmap():
    for p in (BUILD / "shotlist.json", ROOT / "pipeline" / f"{EP}_shotlist.json"):
        if p.exists():
            return {s["scene_id"]: s for s in json.loads(p.read_text(encoding="utf-8"))}
    raise SystemExit(f"no shotlist for {EP}")


def asset_url(rel):
    if not ASSET_BASE:
        raise SystemExit("set WAN_ASSET_BASE to a public URL prefix serving build/ "
                         "(DashScope fetches image/audio by URL).")
    return f"{ASSET_BASE}/{EP}/{rel}"


def motion_prompt(shot):
    scene = (shot.get("visual_prompt") or "").replace("[STYLE]", "").replace("[CUTE GRAPHICS STYLE]", "").strip()
    return (f"{scene} Gentle wholesome children's-storybook animation: soft natural motion, "
            "breeze, drifting light, slow cinematic push-in. Characters stay on-model.")


def submit(model, inp, params):
    h = {"Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
         "X-DashScope-Async": "enable"}
    body = {"model": model, "input": inp, "parameters": params}
    r = requests.post(f"{BASE}/services/aigc/video-generation/video-synthesis",
                      headers=h, json=body, timeout=60)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"submit {r.status_code}: {r.text[:200]}")
    tid = r.json().get("output", {}).get("task_id")
    if not tid:
        raise RuntimeError(f"no task_id: {r.text[:200]}")
    return tid


def poll(task_id, tries=180):
    h = {"Authorization": f"Bearer {KEY}"}
    for _ in range(tries):
        out = requests.get(f"{BASE}/tasks/{task_id}", headers=h, timeout=30).json().get("output", {})
        st = out.get("task_status")
        if st == "SUCCEEDED":
            return out.get("video_url") or (out.get("results") or {}).get("video_url")
        if st in ("FAILED", "CANCELED", "UNKNOWN"):
            raise RuntimeError(f"task {st}: {str(out)[:200]}")
        time.sleep(5)
    raise TimeoutError("wan task timed out")


def main():
    if not KEY:
        raise SystemExit("set DASHSCOPE_KEY (Alibaba Cloud Model Studio).")
    RT = {r["scene_id"]: r for r in routing()}
    SH = shotmap()
    todo = [(sid, r) for sid, r in RT.items() if r["engine"] in ("wan_s2v", "wan_i2v")]
    log(f"episode={EP}  wan shots={len(todo)} "
        f"(s2v={sum(1 for _,r in todo if r['engine']=='wan_s2v')}, "
        f"i2v={sum(1 for _,r in todo if r['engine']=='wan_i2v')})  "
        f"[puppet shots handled in Character Animator]")
    done, failed = [], []
    for sid, r in sorted(todo):
        out = OUT / f"shot{sid:02d}.mp4"
        if out.exists():
            log(f"shot {sid:02d} exists, skip"); continue
        shot = SH.get(sid, {})
        img = asset_url(f"img/shot{sid:02d}.jpg")
        try:
            if r["engine"] == "wan_s2v":           # lip-synced talking character
                inp = {"image_url": img, "audio_url": asset_url(f"audio/shot{sid:02d}.mp3")}
                if shot.get("line"):
                    inp["text"] = shot["line"]
                tid = submit(S2V_MODEL, inp, {})
            else:                                   # i2v motion (incl. faceless prophet shots)
                inp = {"img_url": img, "prompt": motion_prompt(shot)}
                tid = submit(I2V_MODEL, inp, {"negative_prompt": NEG,
                                              "resolution": os.environ.get("WAN_RES", "720P")})
            t = time.time()
            url = poll(tid)
            urllib.request.urlretrieve(url, out)
            log(f"shot {sid:02d} [{r['engine']}{' · prophet' if r['prophet'] else ''}] "
                f"animated ({time.time()-t:.0f}s)")
            done.append(sid)
        except Exception as e:
            log(f"shot {sid:02d} FAILED: {repr(e)[:160]}"); failed.append(sid)
    log(f"DONE. animated={len(done)} {done}  failed={failed}")


if __name__ == "__main__":
    main()
