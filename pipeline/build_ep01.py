#!/usr/bin/env python3
"""
Hikayat Khalid — local $0 video builder for ep01 «رحمة قطرة ماء».

Pipeline (no paid services, no secrets):
  shotlist.json  ->  per-shot illustration (Pollinations / flux, free)
                 ->  per-shot Arabic narration (gTTS, free)
                 ->  per-shot clip (ffmpeg: Ken-Burns + fades + per-speaker pitch)
                 ->  concatenated ep01.mp4

This proves the full Workflow-B assembly end to end and produces a real,
watermark-free MP4. It is intentionally model-agnostic: swap the image step
for Cloudflare flux / Higgsfield, or the audio step for ElevenLabs, by editing
fetch_image() / synth_tts() — the assembly stays the same.

Usage:
    python3 pipeline/build_ep01.py
Env knobs:
    EP01_LIMIT=N    only process the first N shots (smoke test)
    EP01_W / EP01_H aspect override (default 1280x720)
"""
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import imageio_ffmpeg
from gtts import gTTS

try:
    from mutagen.mp3 import MP3
except Exception:  # pragma: no cover
    MP3 = None

# ----------------------------------------------------------------------------- paths/config
ROOT = Path(__file__).resolve().parents[1]
EP = os.environ.get("EPISODE", "ep01")
BUILD = ROOT / "build" / EP
IMG = BUILD / "img"
AUD = BUILD / "audio"
CLIPS = BUILD / "clips"
CLIPS_ANIM = BUILD / "clips_anim"        # animated clips (Path A/B) — preferred if present
for d in (IMG, AUD, CLIPS):
    d.mkdir(parents=True, exist_ok=True)

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
CHARS = json.loads((ROOT / "pipeline" / "characters.json").read_text(encoding="utf-8"))


def _load_shotlist():
    # prefer the working copy pulled from Supabase; fall back to the committed
    # snapshot so the build is reproducible from a clean checkout.
    for p in (BUILD / "shotlist.json", ROOT / "pipeline" / f"{EP}_shotlist.json"):
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    raise SystemExit("no shotlist found (build/ep01/shotlist.json or pipeline/ep01_shotlist.json)")


SHOTS = _load_shotlist()

W = int(os.environ.get("EP01_W", 1280))
H = int(os.environ.get("EP01_H", 720))
FPS = 25
LIMIT = int(os.environ.get("EP01_LIMIT", 0)) or len(SHOTS)
TAIL = 0.8          # seconds of breathing room after narration
MIN_DUR = 2.8       # never flash a shot too fast
COVER_DUR = 3.2
END_DUR = 3.4


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.returncode, p.stdout.decode("utf-8", "replace")


# ----------------------------------------------------------------------------- prompts
def build_image_prompt(shot):
    vp = shot["visual_prompt"]
    prompt = vp.replace("[STYLE]", CHARS["style"])
    notes = []
    for c in CHARS["characters"].values():
        if any(tok in vp for tok in c["match"]):
            notes.append(c["descriptor"])
    if notes:
        prompt += " | Character notes: " + " ".join(notes)
    if shot.get("is_story_shot"):
        prompt += (" | The story-world man's face is NEVER shown — only a "
                   "back view or plain silhouette, no facial features.")
    prompt += " | " + CHARS["negative"]
    return prompt[:1100]


PAREN = re.compile(r"\([^)]*\)|（[^）]*）")


def clean_line(text):
    t = PAREN.sub(" ", text)            # drop stage directions
    t = t.replace("\\n", " ، ").replace("\n", " ، ")
    t = t.replace('"', " ").replace("«", " ").replace("»", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t


# ----------------------------------------------------------------------------- image (free: Pollinations flux)
def fetch_image(prompt, seed, out: Path, tries=5):
    if out.exists() and out.stat().st_size > 4000:
        return True
    q = urllib.parse.quote(prompt, safe="")
    url = (f"https://image.pollinations.ai/prompt/{q}"
           f"?width={W}&height={H}&nologo=true&model=flux&seed={seed}")
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "hikayat/1.0"})
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if len(data) > 4000 and data[:3] in (b"\xff\xd8\xff", b"\x89PN"):
                out.write_bytes(data)
                return True
            log(f"  image small/invalid ({len(data)}B) try {i+1}")
        except Exception as e:
            log(f"  image error try {i+1}: {e}")
        time.sleep(2 * (i + 1))
    return False


def placeholder_image(out: Path, seed):
    """Solid warm gradient fallback so assembly never blocks on a failed gen."""
    hue = 25 + (seed % 40)
    rc, o = run([FFMPEG, "-y", "-f", "lavfi", "-i",
                 f"gradients=s={W}x{H}:c0=0x{hue:02x}3a5a:c1=0xf0c878:duration=1",
                 "-frames:v", "1", str(out)])
    return out.exists()


# ----------------------------------------------------------------------------- audio (free: gTTS)
def synth_tts(text, out: Path, tries=4):
    if out.exists() and out.stat().st_size > 1500:
        return True
    spoken = clean_line(text)
    if not spoken:
        spoken = "..."
    for i in range(tries):
        try:
            gTTS(spoken, lang="ar", slow=False).save(str(out))
            if out.stat().st_size > 1200:
                return True
        except Exception as e:
            log(f"  tts error try {i+1}: {e}")
        time.sleep(2 * (i + 1))
    return False


def audio_dur(path: Path):
    if MP3 is not None:
        try:
            return float(MP3(str(path)).info.length)
        except Exception:
            pass
    rc, o = run([FFMPEG, "-i", str(path)])
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", o)
    if m:
        h, mi, s = m.groups()
        return int(h) * 3600 + int(mi) * 60 + float(s)
    return 4.0


# ----------------------------------------------------------------------------- clip assembly
def zoom_expr(zoom_in):
    if zoom_in:
        z = "z='min(1.0+0.0012*on,1.15)'"
    else:
        z = "z='if(lte(on,1),1.15,max(1.15-0.0012*on,1.0))'"
    return (f"zoompan={z}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d=1:s={W}x{H}:fps={FPS}")


def vfilter(dur, zoom_in):
    fout = max(dur - 0.45, 0.1)
    return (f"[0:v]scale={W*2}:{H*2}:force_original_aspect_ratio=increase,"
            f"crop={W*2}:{H*2},{zoom_expr(zoom_in)},"
            f"fade=t=in:st=0:d=0.4,fade=t=out:st={fout:.2f}:d=0.4,"
            f"format=yuv420p[v]")


def make_clip(img: Path, audio: Path, pitch, dur, out: Path, zoom_in):
    f = max(0.5, min(2.0, float(pitch)))
    afil = (f"[1:a]asetrate=44100*{f},aresample=44100,atempo={1.0/f:.5f},"
            f"aformat=sample_rates=44100:channel_layouts=stereo[a]")
    fc = vfilter(dur, zoom_in) + ";" + afil
    cmd = [FFMPEG, "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.2f}",
           "-i", str(img), "-i", str(audio),
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
           "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k",
           "-t", f"{dur:.2f}", "-movflags", "+faststart", str(out)]
    rc, o = run(cmd)
    return rc == 0 and out.exists()


def probe_dur(path: Path):
    rc, o = run([FFMPEG, "-i", str(path)])
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", o)
    if m:
        h, mi, s = m.groups()
        return int(h) * 3600 + int(mi) * 60 + float(s)
    return None


def make_from_clip(clip_in: Path, audio: Path, dur, out: Path):
    """Fit an animated clip to `dur` (freeze-pad if short, trim if long) + the voice track."""
    cdur = probe_dur(clip_in) or dur
    pad = max(0.0, dur - cdur)
    fout = max(dur - 0.45, 0.1)
    vf = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}"
          + (f",tpad=stop_mode=clone:stop_duration={pad:.2f}" if pad > 0.05 else "")
          + f",fade=t=in:st=0:d=0.4,fade=t=out:st={fout:.2f}:d=0.4,format=yuv420p[v]")
    afil = "[1:a]aformat=sample_rates=44100:channel_layouts=stereo[a]"
    cmd = [FFMPEG, "-y", "-i", str(clip_in), "-i", str(audio),
           "-filter_complex", vf + ";" + afil, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", "-t", f"{dur:.2f}",
           "-movflags", "+faststart", str(out)]
    rc, o = run(cmd)
    return rc == 0 and out.exists()


def make_title_clip(img: Path, dur, out: Path, zoom_in=True):
    fc = (vfilter(dur, zoom_in) + ";"
          "[1:a]aformat=sample_rates=44100:channel_layouts=stereo[a]")
    cmd = [FFMPEG, "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.2f}",
           "-i", str(img),
           "-f", "lavfi", "-t", f"{dur:.2f}", "-i", "anullsrc=r=44100:cl=stereo",
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
           "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k",
           "-t", f"{dur:.2f}", "-movflags", "+faststart", str(out)]
    rc, o = run(cmd)
    return rc == 0 and out.exists()


def concat(clip_paths, out: Path):
    lst = BUILD / "concat.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in clip_paths), encoding="utf-8")
    rc, o = run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                 "-c", "copy", "-movflags", "+faststart", str(out)])
    if rc != 0 or not out.exists():
        log("concat copy failed, re-encoding:", o[-400:])
        rc, o = run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                     "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
                     "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2",
                     "-movflags", "+faststart", str(out)])
    return out.exists()


# ----------------------------------------------------------------------------- main
def main():
    log(f"ffmpeg: {FFMPEG}")
    log(f"shots: {len(SHOTS)}  building: {LIMIT}  out: {W}x{H}@{FPS}")
    manifest = {"episode": "ep01", "story_id": "ep01", "width": W, "height": H,
                "fps": FPS, "shots": []}
    clip_paths = []

    # --- cover ---
    cover_img = IMG / "cover.jpg"
    if not fetch_image(CHARS["style"] + " | " + CHARS["cover_prompt"] + " | " + CHARS["negative"],
                       7000, cover_img):
        placeholder_image(cover_img, 7000)
    cover_clip = CLIPS / "cover.mp4"
    make_title_clip(cover_img, COVER_DUR, cover_clip, zoom_in=True)
    clip_paths.append(cover_clip)

    # --- story shots ---
    for shot in SHOTS[:LIMIT]:
        sid = int(shot["scene_id"])
        speaker = shot.get("speaker", "")
        log(f"shot {sid:02d}  [{speaker}]")
        img = IMG / f"shot{sid:02d}.jpg"
        aud = AUD / f"shot{sid:02d}.mp3"

        prompt = build_image_prompt(shot)
        if not fetch_image(prompt, 7000 + sid, img):
            log(f"  -> image FAILED, placeholder")
            placeholder_image(img, 7000 + sid)
        if not synth_tts(shot["line"], aud):
            log(f"  -> tts FAILED, silent 3s")
            run([FFMPEG, "-y", "-f", "lavfi", "-t", "3",
                 "-i", "anullsrc=r=44100:cl=stereo", "-q:a", "9", str(aud)])

        adur = audio_dur(aud)
        dur = max(adur + TAIL, MIN_DUR)
        pitch = CHARS["speaker_pitch"].get(speaker, 1.0)
        clip = CLIPS / f"shot{sid:02d}.mp4"
        anim = CLIPS_ANIM / f"shot{sid:02d}.mp4"
        if anim.exists():
            ok = make_from_clip(anim, aud, dur, clip)        # animated (Path A/B)
        else:
            ok = make_clip(img, aud, pitch, dur, clip, zoom_in=(sid % 2 == 0))  # Ken-Burns draft
        if not ok:
            log(f"  -> clip FAILED for shot {sid}")
            continue
        clip_paths.append(clip)
        manifest["shots"].append({
            "scene_id": sid, "speaker": speaker, "line": shot["line"],
            "is_story_shot": shot.get("is_story_shot", False),
            "image": str(img.relative_to(ROOT)), "audio": str(aud.relative_to(ROOT)),
            "clip": str(clip.relative_to(ROOT)),
            "audio_dur": round(adur, 2), "clip_dur": round(dur, 2),
        })

    # --- end card ---
    end_img = IMG / "endcard.jpg"
    if not fetch_image(CHARS["style"] + " | " + CHARS["endcard_prompt"] + " | " + CHARS["negative"],
                       7099, end_img):
        placeholder_image(end_img, 7099)
    end_clip = CLIPS / "endcard.mp4"
    make_title_clip(end_img, END_DUR, end_clip, zoom_in=False)
    clip_paths.append(end_clip)

    # --- concat ---
    master = BUILD / "ep01.mp4"
    log(f"concatenating {len(clip_paths)} clips -> {master.name}")
    if not concat(clip_paths, master):
        log("FATAL: concat failed")
        sys.exit(1)

    size_mb = master.stat().st_size / 1e6
    total = sum(s["clip_dur"] for s in manifest["shots"]) + COVER_DUR + END_DUR
    manifest["duration_sec"] = round(total, 1)
    manifest["master"] = str(master.relative_to(ROOT))
    manifest["master_mb"] = round(size_mb, 2)

    # web copy (<25MB) for the 25MB Supabase bucket limit
    upload = master
    if size_mb > 24:
        web = BUILD / "ep01_web.mp4"
        log(f"master {size_mb:.1f}MB > 24MB, encoding web copy")
        run([FFMPEG, "-y", "-i", str(master), "-vf", "scale=960:540",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
             "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "112k",
             "-movflags", "+faststart", str(web)])
        if web.exists():
            upload = web
            manifest["web_copy"] = str(web.relative_to(ROOT))
            manifest["web_mb"] = round(web.stat().st_size / 1e6, 2)
    manifest["upload_file"] = str(upload.relative_to(ROOT))

    (BUILD / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"DONE  {master}  {size_mb:.1f}MB  ~{total:.0f}s  shots={len(manifest['shots'])}")
    log(f"upload file -> {upload.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
