# Hikayat Khalid — حكايات خالد

An automated Islamic children's-story channel (ages 4–10, simplified Arabic) for
YouTube / Instagram / TikTok. Stories are produced by an **n8n** assembly line on
a **Supabase** backend behind **two human approval gates** (shariah, then
technical). Hero: **Khalid** (7-year-old boy), with **Noor** (sister), **Teta**
(grandmother narrator) and the **Lantern of Tales**.

Pipeline: **A** write script → shariah gate · **B** generate per-shot images +
voice → assemble video → technical gate · **C** publish (madeForKids) · **D**
analytics → backlog.

### Hard rules (never violated)
1. No depiction of any prophet — ever.
2. No image/audio generation before the script passes the **shariah gate**.
3. Never publish without `madeForKids = true`.
4. AI dramatizes, never invents religion — content comes only from the approved
   `source_text`.
5. Secrets live in n8n credentials or a local `.env` — **never** in the repo.

## What's in this repo

| Path | What |
|------|------|
| [`pipeline/`](pipeline/) | **Local $0 video builder** for ep01 — turns the approved shotlist into a finished MP4 with free tools (Pollinations + gTTS + ffmpeg). The local equivalent of Workflow B. See [pipeline/README.md](pipeline/README.md). |
| `pipeline/ep01_shotlist.json` | The 31-shot list for ep01 «رحمة قطرة ماء», exported from Supabase. |
| `pipeline/characters.json` | Art style + character bible + per-speaker voice pitch. |
| [`docs/HANDOFF.md`](docs/HANDOFF.md) | Full project handoff (infra, IDs, state, gotchas). |
| `docs/samples/` | Sample frames from the ep01 build. |

## Quick start — build the first video

```bash
pip install -r pipeline/requirements.txt
python3 pipeline/build_ep01.py     # -> build/ep01/ep01.mp4
```

Optionally persist to Supabase (needs your service_role key in the environment):

```bash
export SUPABASE_URL="https://dvxmgtelcismjumgxwkw.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="...."
python3 pipeline/upload_to_supabase.py
```

## Backend

- **Supabase** project `dvxmgtelcismjumgxwkw` (`hikayat-khalid`). Key tables:
  `backlog`, `episodes`, `characters`, `episode_assets` (per-shot rows; an
  AFTER-INSERT trigger rolls `image_url`/`audio_url` up into
  `episodes.image_urls[]`/`audio_urls[]`), `app_config`, `activity_log`.
- Media bucket `episode-media` (public read, 25 MB/object).

> `build/` holds generated media and is git-ignored.
