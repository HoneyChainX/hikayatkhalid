#!/usr/bin/env python3
"""
Persist the locally-built ep01 assets to Supabase (storage + episode_assets +
episodes.video_draft_url), mirroring what Workflow B would do.

SECRETS: this script reads the service_role key from the environment ONLY.
Never hard-code it and never commit it. Run it locally:

    export SUPABASE_URL="https://dvxmgtelcismjumgxwkw.supabase.co"
    export SUPABASE_SERVICE_ROLE_KEY="...your service_role key..."
    python3 pipeline/upload_to_supabase.py

It will:
  1. upload build/ep01/img/*.jpg, audio/*.mp3 and the MP4 to the
     `episode-media` bucket under ep01/
  2. replace episode_assets rows for the episode (the AFTER-INSERT trigger
     rolls them up into episodes.image_urls / audio_urls)
  3. set episodes.video_draft_url and tech_status='tech_review'
"""
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build" / "ep01"
URL = os.environ.get("SUPABASE_URL", "https://dvxmgtelcismjumgxwkw.supabase.co").rstrip("/")
KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
BUCKET = os.environ.get("EPISODE_MEDIA_BUCKET", "episode-media")
STORY = os.environ.get("EPISODE_STORY_ID", "ep01")

if not KEY:
    sys.exit("ERROR: set SUPABASE_SERVICE_ROLE_KEY in your environment (do not hard-code it).")

H = {"apikey": KEY, "Authorization": f"Bearer {KEY}"}
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".mp3": "audio/mpeg", ".mp4": "video/mp4"}


def public_url(path):
    return f"{URL}/storage/v1/object/public/{BUCKET}/{path}"


def upload(local: Path, dest: str):
    ct = MIME.get(local.suffix.lower(), "application/octet-stream")
    r = requests.post(
        f"{URL}/storage/v1/object/{BUCKET}/{dest}",
        headers={**H, "Content-Type": ct, "x-upsert": "true"},
        data=local.read_bytes(), timeout=120)
    if r.status_code not in (200, 201):
        raise SystemExit(f"upload failed {dest}: {r.status_code} {r.text[:200]}")
    return public_url(dest)


def main():
    manifest = json.loads((BUILD / "manifest.json").read_text(encoding="utf-8"))

    # resolve episode_id
    r = requests.get(f"{URL}/rest/v1/episodes",
                     headers=H, params={"story_id": f"eq.{STORY}", "select": "episode_id"},
                     timeout=30)
    r.raise_for_status()
    rows = r.json()
    if not rows:
        sys.exit(f"no episode with story_id={STORY}")
    ep = rows[0]["episode_id"]
    print(f"episode_id={ep}  uploading {len(manifest['shots'])} shots to {BUCKET}/ ...")

    assets = []
    for s in manifest["shots"]:
        sid = s["scene_id"]
        img_url = upload(ROOT / s["image"], f"{STORY}/shot{sid:02d}.jpg")
        aud_url = upload(ROOT / s["audio"], f"{STORY}/shot{sid:02d}.mp3")
        assets.append({"episode_id": ep, "scene_id": sid, "speaker": s["speaker"],
                       "line": s["line"], "image_url": img_url, "audio_url": aud_url,
                       "is_story_shot": s["is_story_shot"]})
        print(f"  shot{sid:02d} uploaded")

    # video
    vfile = ROOT / manifest.get("upload_file", manifest["master"])
    video_url = upload(vfile, f"{STORY}/{vfile.name}")
    print(f"  video uploaded -> {video_url}")

    # replace episode_assets (trigger rolls up arrays)
    requests.delete(f"{URL}/rest/v1/episode_assets",
                    headers={**H, "Prefer": "return=minimal"},
                    params={"episode_id": f"eq.{ep}"}, timeout=30)
    r = requests.post(f"{URL}/rest/v1/episode_assets",
                      headers={**H, "Content-Type": "application/json", "Prefer": "return=minimal"},
                      data=json.dumps(assets), timeout=60)
    if r.status_code not in (200, 201, 204):
        sys.exit(f"episode_assets insert failed: {r.status_code} {r.text[:300]}")

    # set video + technical gate
    r = requests.patch(f"{URL}/rest/v1/episodes",
                       headers={**H, "Content-Type": "application/json", "Prefer": "return=minimal"},
                       params={"episode_id": f"eq.{ep}"},
                       data=json.dumps({"video_draft_url": video_url, "tech_status": "tech_review"}),
                       timeout=30)
    if r.status_code not in (200, 204):
        sys.exit(f"episodes update failed: {r.status_code} {r.text[:300]}")

    print(f"DONE. episode_assets={len(assets)}, video_draft_url set, tech_status=tech_review.")


if __name__ == "__main__":
    main()
