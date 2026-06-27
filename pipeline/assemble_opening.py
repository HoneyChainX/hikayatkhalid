#!/usr/bin/env python3
"""
Assemble a sequence of (video, voice) shots into one film. Each shot's normalized
voice is muxed onto its (upscaled, silent) clip, every shot is re-encoded to identical
params, then concatenated losslessly. Pads/truncates audio to the video length.

    python3 pipeline/assemble_opening.py \
        --clips build/ep01/clips_up/shot01.mp4 ... \
        --audios build/ep01/audio_norm/shot01.mp3 ... \
        --out build/ep01/ep01_opening_v2.mp4
or shorthand (shotNN.mp4 + shotNN.mp3 by index):
    python3 pipeline/assemble_opening.py --dir-clips build/ep01/clips_up \
        --dir-audio build/ep01/audio_norm --shots 1 2 3 4 --out build/ep01/ep01_opening_v2.mp4
"""
import argparse
import subprocess
import tempfile
from pathlib import Path


def ff_bin():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


FF = ff_bin()
# common target: portrait HD, 16 fps, h264 + aac
VF = "scale=1080:1440:force_original_aspect_ratio=decrease,pad=1080:1440:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps=16"


def mux(video: Path, audio: Path, out: Path):
    args = [FF, "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(video), "-i", str(audio),
            "-map", "0:v:0", "-map", "1:a:0",
            "-vf", VF, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "16",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-shortest", str(out)]
    subprocess.run(args, check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clips", nargs="*", default=[])
    ap.add_argument("--audios", nargs="*", default=[])
    ap.add_argument("--dir-clips")
    ap.add_argument("--dir-audio")
    ap.add_argument("--shots", nargs="*", type=int, default=[])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    if a.shots:
        clips = [Path(a.dir_clips) / f"shot{n:02d}.mp4" for n in a.shots]
        audios = [Path(a.dir_audio) / f"shot{n:02d}.mp3" for n in a.shots]
    else:
        clips = [Path(c) for c in a.clips]
        audios = [Path(c) for c in a.audios]
    assert len(clips) == len(audios) and clips, "clips/audios mismatch or empty"

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp())
    parts = []
    for i, (v, au) in enumerate(zip(clips, audios)):
        if not v.exists():
            print(f"  !! missing clip {v} — skipping"); continue
        p = tmp / f"p{i:02d}.mp4"
        print(f"  mux {v.name} + {au.name}")
        mux(v, au, p)
        parts.append(p)
    listfile = tmp / "list.txt"
    listfile.write_text("".join(f"file '{p}'\n" for p in parts))
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "concat", "-safe", "0", "-i", str(listfile),
                    "-c", "copy", str(out)], check=True)
    dur = subprocess.run([FF, "-hide_banner", "-i", str(out)], capture_output=True, text=True).stderr
    import re
    m = re.search(r"Duration: (\S+)", dur)
    print(f"OK -> {out}  ({len(parts)} shots, {m.group(1) if m else '?'})")


if __name__ == "__main__":
    main()
