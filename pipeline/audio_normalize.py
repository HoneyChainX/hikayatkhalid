#!/usr/bin/env python3
"""
Normalize every voice clip to the SAME perceived loudness (fixes "voices volume are
not the same"). Two-pass EBU R128 loudnorm -> -14 LUFS integrated (YouTube target),
-1.5 dBTP ceiling, 11 LRA. Run BEFORE S2V so the lip-sync is driven by the leveled
waveform and the muxed output audio is already consistent.

    python3 pipeline/audio_normalize.py --in build/ep01/audio --out build/ep01/audio_norm

Outputs <out>/shotNN.mp3 for every shotNN.mp3 in <in>, plus a loudness report.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

I_TARGET, TP_TARGET, LRA_TARGET = -14.0, -1.5, 11.0


def ffmpeg_bin():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


FF = ffmpeg_bin()


def run(args):
    return subprocess.run([FF, "-hide_banner", *args], capture_output=True, text=True)


def duration(p: Path):
    err = run(["-i", str(p)]).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", err)
    return (int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])) if m else None


def measure(p: Path):
    """Pass 1: measure loudness, return the JSON loudnorm emits on stderr."""
    err = run(["-i", str(p), "-af",
               f"loudnorm=I={I_TARGET}:TP={TP_TARGET}:LRA={LRA_TARGET}:print_format=json",
               "-f", "null", "-"]).stderr
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", err, re.S)
    return json.loads(m.group(0)) if m else None


def normalize(src: Path, dst: Path, m):
    """Pass 2: apply linear loudnorm using the measured values."""
    af = (f"loudnorm=I={I_TARGET}:TP={TP_TARGET}:LRA={LRA_TARGET}:"
          f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
          f"offset={m['target_offset']}:linear=true:print_format=summary")
    r = run(["-y", "-i", str(src), "-af", af, "-ar", "48000", "-b:a", "192k", str(dst)])
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="build/ep01/audio")
    ap.add_argument("--out", dest="out", default="build/ep01/audio_norm")
    a = ap.parse_args()
    src, out = Path(a.src), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(src.glob("shot*.mp3"))
    if not files:
        print(f"no shot*.mp3 in {src}", file=sys.stderr)
        raise SystemExit(1)
    print(f"ffmpeg={FF}\nnormalizing {len(files)} clips -> {I_TARGET} LUFS / {TP_TARGET} dBTP\n")
    report, ok = [], 0
    for p in files:
        m = measure(p)
        if not m:
            print(f"  {p.name:14s} MEASURE FAILED — skipped")
            continue
        dst = out / p.name
        good = normalize(p, dst, m)
        ok += good
        report.append({"file": p.name, "in_LUFS": m["input_i"], "in_TP": m["input_tp"],
                       "dur": duration(p), "ok": good})
        print(f"  {p.name:14s} in {float(m['input_i']):7.1f} LUFS  TP {float(m['input_tp']):6.1f}  "
              f"-> -14.0  {'OK' if good else 'FAIL'}")
    (out / "_loudness_report.json").write_text(json.dumps(report, indent=2))
    print(f"\nDONE — {ok}/{len(files)} normalized -> {out}")
    raise SystemExit(0 if ok == len(files) else 1)


if __name__ == "__main__":
    main()
