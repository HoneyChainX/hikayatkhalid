#!/usr/bin/env python3
"""
Producer's state manifest — the single source of truth for an episode's progress through the
AI-team pipeline. Builds build/epNN/production_state.json from routing.json + shotlist, and
provides get/set/summary helpers the Producer and QA use to drive (and redo) the pipeline.

    python3 pipeline/production_state.py init  --ep ep01
    python3 pipeline/production_state.py show  --ep ep01
    python3 pipeline/production_state.py set    --ep ep01 --shot 2 --stage render --status done
"""
import argparse
import json
from pathlib import Path

STAGES = ["shariah", "keyframe", "voice", "audio", "render", "upscale", "qa"]
ROOT = Path(__file__).resolve().parents[1]


def paths(ep):
    b = ROOT / "build" / ep
    return b, b / "production_state.json", b / "routing.json", b / "shotlist.json"


def init(ep):
    b, state_p, routing_p, shot_p = paths(ep)
    routing = json.loads(routing_p.read_text(encoding="utf-8")) if routing_p.exists() else []
    shots = json.loads(shot_p.read_text(encoding="utf-8")) if shot_p.exists() else []
    text = {s.get("scene_id"): (s.get("text") or "") for s in shots if isinstance(s, dict)}
    rows = []
    for r in routing:
        sid = r.get("scene_id")
        rows.append({
            "scene_id": sid, "speaker": r.get("speaker"), "engine": r.get("engine"),
            "is_story_shot": r.get("is_story_shot", False), "prophet": r.get("prophet", False),
            "text": text.get(sid, ""),
            "stages": {s: "pending" for s in STAGES},
        })
    state = {"episode": ep, "shots": rows}
    state_p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"init {ep}: {len(rows)} shots -> {state_p}")
    return state


def load(ep):
    _, state_p, _, _ = paths(ep)
    return json.loads(state_p.read_text(encoding="utf-8"))


def save(ep, state):
    _, state_p, _, _ = paths(ep)
    state_p.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def set_status(ep, shot, stage, status):
    state = load(ep)
    for r in state["shots"]:
        if r["scene_id"] == shot:
            r["stages"][stage] = status
    save(ep, state)
    print(f"{ep} shot{shot} {stage}={status}")


def show(ep):
    state = load(ep)
    from collections import Counter
    print(f"== {ep}: {len(state['shots'])} shots ==")
    for s in STAGES:
        c = Counter(r["stages"][s] for r in state["shots"])
        print(f"  {s:9s} " + "  ".join(f"{k}={v}" for k, v in sorted(c.items())))
    blocked = [r["scene_id"] for r in state["shots"] if r["stages"]["shariah"] == "fail"]
    if blocked:
        print("  !! shariah-blocked shots:", blocked)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["init", "show", "set"])
    ap.add_argument("--ep", default="ep01")
    ap.add_argument("--shot", type=int)
    ap.add_argument("--stage", choices=STAGES)
    ap.add_argument("--status", choices=["pending", "done", "fail"])
    a = ap.parse_args()
    if a.cmd == "init":
        init(a.ep)
    elif a.cmd == "show":
        show(a.ep)
    elif a.cmd == "set":
        set_status(a.ep, a.shot, a.stage, a.status)


if __name__ == "__main__":
    main()
