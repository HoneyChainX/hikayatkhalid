# ep01 video pipeline (local, $0)

Builds the first **Hikayat Khalid** video — ep01 «رحمة قطرة ماء» (*The Mercy of a
Drop of Water*) — entirely from free tools, with **no API keys and no secrets**.
It is the local equivalent of n8n **Workflow B**: it turns the shariah-approved
shotlist into per-shot illustrations + Arabic narration and assembles a real MP4.

```
shotlist  ->  image (Pollinations / flux, free)
          ->  narration (gTTS Arabic, free)
          ->  clip (ffmpeg: Ken-Burns zoom, fades, per-speaker pitch)
          ->  ep01.mp4  (1280x720, H.264/AAC, watermark-free)
```

## Run

```bash
pip install -r pipeline/requirements.txt
python3 pipeline/build_ep01.py          # writes build/ep01/ep01.mp4 + manifest.json
```

Knobs: `EP01_LIMIT=3` (smoke test on first N shots), `EP01_W` / `EP01_H` (aspect).

The build is **idempotent** — already-generated images/audio are reused, so a
re-run only fills gaps and re-stitches.

## Inputs (committed, reproducible)

- `pipeline/ep01_shotlist.json` — the 31-shot list (scene_id, speaker, Arabic
  line, English `visual_prompt`, `is_story_shot`), exported from
  `episodes.shotlist_json`. The builder prefers `build/ep01/shotlist.json` if a
  fresh copy was pulled from Supabase, else falls back to this snapshot.
- `pipeline/characters.json` — shared art style, the character bible used to
  inject visual descriptors into each prompt, and per-speaker voice pitch.

## Persist to Supabase (optional)

`upload_to_supabase.py` uploads the assets to the `episode-media` bucket, writes
`episode_assets` rows (the DB trigger rolls them up into
`episodes.image_urls` / `audio_urls`) and sets `episodes.video_draft_url` +
`tech_status='tech_review'`. It reads the **service_role key from the
environment only** — never commit it:

```bash
export SUPABASE_URL="https://dvxmgtelcismjumgxwkw.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="...."   # paste locally, do not commit
python3 pipeline/upload_to_supabase.py
```

## Quality notes / upgrade path

This is a **first-draft** quality bar that proves the full assembly:

- **Character consistency** rides on textual descriptors only (Pollinations/flux
  is text-to-image), so Khalid is recognizable but not pixel-identical
  shot-to-shot — the same limitation noted in the project handoff. To fix, swap
  `fetch_image()` for a reference-capable model (Higgsfield with `khalid_v1.png`,
  or Cloudflare flux) — the rest of the pipeline is unchanged.
- **Voices** are a single free Arabic TTS, differentiated by subtle per-speaker
  pitch. Swap `synth_tts()` for ElevenLabs (Khalid voice
  `rzNH3PV43Tk38jg31TS6`) once those voices are cloned.
- **Timing** uses real per-shot narration durations (not fixed 5s), so nothing
  is cut off.

## Hard rules respected

- Built only from the **shariah-approved** script/shotlist (`script_status=approved`).
- Story-world shots keep the man **faceless / silhouetted** (no prophet or
  named-figure depiction — there is no prophet in this story regardless).
- No secrets in code; service keys come from the environment at run time.
