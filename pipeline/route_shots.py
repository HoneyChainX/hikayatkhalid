#!/usr/bin/env python3
"""
Shot router for the HYBRID pipeline (chosen approach):
  • puppet     — modern-frame dialogue by our recurring cast (خالد/نور/تيتا/فانوس)
                 → animated in **Adobe Character Animator** (rigged puppet + auto lip-sync
                 from the ElevenLabs audio). Perfect consistency, ~$0/episode.
  • wan_s2v    — STORY-world shot where a NON-prophet, on-screen character speaks
                 → **Wan 2.2-S2V** (portrait keyframe + audio → lip-synced clip), DashScope.
  • wan_i2v    — story-world motion / scene, narrator voice-over, OR a prophet shot
                 → **Wan 2.2 i2v** (keyframe → motion); audio is laid over, NO lip-sync.

COMPLIANCE (hard rule): a prophet is NEVER lip-synced or embodied. Any shot whose
speaker/visual involves a prophet is forced to `wan_i2v` with `prophet=True`
(faceless light / off-screen voice only). See docs/COMPLIANCE_REVIEW.md.

    EPISODE=ep01 python3 pipeline/route_shots.py      # one episode
    python3 pipeline/route_shots.py --all             # all epNN_shotlist.json
Writes build/<ep>/routing.json and prints a summary. Pure classification — no network.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CAST = ["خالد", "نور", "تيتا", "فانوس"]            # recurring, depictable puppets
NARRATORS = ["راو", "راوٍ", "الراوي"]               # voice-over only (not on-screen)
PROPHETS = ["النبي", "نبي", "رسول الله", "الرسول", "موسى", "عيسى", "إبراهيم", "نوح",
            "يوسف", "يونس", "داود", "داوود", "سليمان", "آدم", "إسماعيل", "لوط", "هود",
            "صالح", "شعيب", "زكريا", "يحيى", "أيوب", "إدريس", "محمد"]
PROPHET_VIS = ["faceless", "off-screen", "off screen", "halo", "luminous", "faint light",
               "bright light", "shadow", "silhouette", "abstract", "represented as"]
PROPHET_EN = ["prophet", "noah", "ibrahim", "abraham", "sulaiman", "solomon", "younus",
              "yunus", "jonah", "musa", "moses", "isa ", "jesus", "yusuf", "joseph",
              "idris", "ayyub", "job", "dawud", "david", "lut", "lot", "hud", "saleh"]


def norm(s):
    return re.sub("[ً-ْ]", "", s or "")


def has(text, words):
    t = norm(text)
    return any(norm(w) in t for w in words)


def has_en(text, words):
    t = (text or "").lower()
    return any(w in t for w in words)


def shots(ep):
    for p in (ROOT / "build" / ep / "shotlist.json",
              ROOT / "pipeline" / f"{ep}_shotlist.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise SystemExit(f"no shotlist for {ep}")


def route(shot):
    speaker = shot.get("speaker") or ""
    line = (shot.get("line") or "").strip()
    visual = shot.get("visual_prompt") or ""
    is_story = bool(shot.get("is_story_shot"))
    has_line = bool(line)

    # A prophet must never be lip-synced/embodied. Flag a shot prophet=True only when the
    # prophet is actually VOICED (named in the speaker) or DEPICTED (a faceless/off-screen
    # VISUAL that names a prophet, AR or EN). A mere narration *mention* of a prophet (in the
    # line, while Teta is on-screen) is NOT a depiction → it stays a puppet shot.
    prophet = (has(speaker, PROPHETS)
               or (is_story and has(visual, PROPHET_VIS)
                   and (has(visual, PROPHETS) or has_en(visual, PROPHET_EN))))

    # 1) prophet → never lip-synced: faceless-light scene + off-screen voice
    if prophet:
        return ("wan_i2v", True, "prophet: faceless light + off-screen voice, NO lip-sync")
    # 2) modern-frame cast dialogue → Character Animator puppet
    if (not is_story) and has_line and has(speaker, CAST) and not has(speaker, NARRATORS):
        return ("puppet", False, "modern-frame cast dialogue (Character Animator)")
    # 3) story dialogue by an on-screen non-prophet character → Wan-S2V lip-sync
    if is_story and has_line and not has(speaker, NARRATORS) and not has(speaker, CAST):
        return ("wan_s2v", False, "story character speaks on-screen (Wan-S2V lip-sync)")
    # 4) story shot narrated by Teta/راوٍ (voice-over) or any cast VO over story → motion + VO
    if is_story:
        return ("wan_i2v", False, "story-world visual + narrator/cast voice-over (no lip-sync)")
    # 5) modern-frame, no/!cast line → light motion or still
    if has_line:
        return ("puppet", False, "modern-frame dialogue (cast fallback)")
    return ("wan_i2v", False, "scene / no dialogue")


def run(ep):
    SH = shots(ep)
    out = []
    for s in SH:
        eng, prophet, why = route(s)
        out.append({"scene_id": s.get("scene_id"), "engine": eng, "prophet": prophet,
                    "speaker": s.get("speaker"), "is_story_shot": bool(s.get("is_story_shot")),
                    "reason": why})
    bd = ROOT / "build" / ep
    bd.mkdir(parents=True, exist_ok=True)
    (bd / "routing.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {}
    for r in out:
        counts[r["engine"]] = counts.get(r["engine"], 0) + 1
    proph = sum(1 for r in out if r["prophet"])
    tag = f"  (prophet shots: {proph})" if proph else ""
    print(f"{ep}: {len(out):>2} shots  "
          f"puppet={counts.get('puppet',0):>2}  wan_s2v={counts.get('wan_s2v',0):>2}  "
          f"wan_i2v={counts.get('wan_i2v',0):>2}{tag}")
    return counts, proph


def main():
    eps = ([f"ep{n:02d}" for n in range(1, 11)] if "--all" in sys.argv
           else [os.environ.get("EPISODE", "ep01")])
    tot = {}
    tp = 0
    for ep in eps:
        try:
            c, p = run(ep)
        except SystemExit as e:
            print(e); continue
        for k, v in c.items():
            tot[k] = tot.get(k, 0) + v
        tp += p
    if len(eps) > 1:
        print(f"\nTOTAL: puppet={tot.get('puppet',0)}  wan_s2v={tot.get('wan_s2v',0)}  "
              f"wan_i2v={tot.get('wan_i2v',0)}  (prophet shots: {tp})")
        print("→ puppet = Character Animator (one-time rig, ~$0/ep); "
              "wan_s2v/i2v = DashScope (~$0.10-0.15/clip).")


if __name__ == "__main__":
    main()
