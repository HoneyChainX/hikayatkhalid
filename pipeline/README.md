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

## Free Khalid-consistency pass (`rerender_khalid_kontext.py`)

Locks Khalid's face/outfit across shots for **$0 — no API key, no credits**,
using **Flux.1 Kontext** (open weights) on a public Hugging Face Space. It edits
the locked reference `khalid_v1.png` (placed on a 16:9 white canvas) into each
scene, so the same Khalid appears in every shot. Only the 22 shots containing
KHALID are re-rendered; the rest keep their flux images.

```bash
pip install gradio_client imageio-ffmpeg
python3 pipeline/rerender_khalid_kontext.py   # writes build/ep01/img/shotNN.jpg (flux backed up to img_flux/)
python3 pipeline/build_ep01.py                # restitch the MP4 with the consistent frames
```

Resumable (finished shots are skipped) and rate-limit tolerant (it rotates across
mirror Spaces on quota errors). Anonymous HF ZeroGPU has a small per-IP daily
budget shared across all spaces, so for an uninterrupted run set a free
`HF_TOKEN`.

**No-quota alternative — `rerender_khalid_nim.py`:** the *same* FLUX.1 Kontext
model is hosted on **NVIDIA NIM** (`ai.api.nvidia.com`), which runs on free
credits with no shared GPU wall. Get a free key at build.nvidia.com, then:

```bash
export NVIDIA_API_KEY="nvapi-..."
python3 pipeline/rerender_khalid_nim.py && python3 pipeline/build_ep01.py
```

The identical quality is also available via the Gemini free tier ("nano-banana"
/ Gemini Flash Image) with your existing Gemini key.

**Recommended runner — `rerender_balancer.py`:** a smart multi-backend balancer
that spreads the shots across whichever free identity-locking backends are
healthy (HF Kontext / NVIDIA NIM / Gemini), health-gating each one (auto-skip on
quota or error, auto-resume when it recovers). It maximizes free throughput and
needs no single backend to carry the whole job:

```bash
# enable whatever you have; unset ones are simply skipped
export HF_TOKEN=...           # optional, lifts the HF anonymous cap
export NVIDIA_API_KEY=...     # optional, NVIDIA NIM
export GEMINI_API_KEY=...     # optional, Gemini nano-banana
python3 pipeline/rerender_balancer.py && python3 pipeline/build_ep01.py
```

## Quality notes / upgrade path

This is a **first-draft** quality bar that proves the full assembly:

- **Character consistency**: the base build's images are text-to-image
  (Pollinations/flux), so Khalid is recognizable but not pixel-identical
  shot-to-shot. **Fixed for free** by `rerender_khalid_kontext.py` (below).
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
