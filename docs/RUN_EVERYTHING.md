# Run everything — turnkey episode production

The moment a **GPU box** or a **generation subscription** is live, producing an
episode is **one command**. Everything below is committed and resumable; each
stage auto-skips if its output already exists.

```bash
cp .env.example .env          # fill in whatever keys you have
set -a; source .env; set +a   # load them into the environment
python3 pipeline/preflight.py # ← tells you exactly what's ready / missing
python3 pipeline/produce_episode.py
# -> build/<ep>/ep01.mp4   (animated if an animate backend is set, else stills draft)
```

## What runs, and what it needs

| Stage | Script | Needs (any) | Output |
|---|---|---|---|
| 1 Script + shotlist | n8n Workflow A (+ shariah gate) | sheikh-approved `source_text` | `episodes.shotlist_json` |
| 2 Keyframes (consistent) | `rerender_balancer.py` | `HF_TOKEN` / `NVIDIA_API_KEY` / `GEMINI_API_KEY` (or a GPU box) | `build/<ep>/img/shotNN.jpg` |
| 3 **Animate** | `animate_fal.py` **or** `comfy/animate_episode.py` | `FAL_KEY` (cloud) **or** `COMFY_URL` (GPU) | `build/<ep>/clips_anim/shotNN.mp4` |
| 4 Voices | `revoice_elevenlabs.py` | `ELEVENLABS_API_KEY` | `build/<ep>/audio/shotNN.mp3` |
| 5 Assemble | `build_ep01.py` | ffmpeg (bundled) | `build/<ep>/ep01.mp4` |
| 6 Persist *(opt)* | `upload_to_supabase.py` | `SUPABASE_SERVICE_ROLE_KEY` | Supabase storage + `episode_assets` |
| 7 Finish *(opt)* | **DaVinci Resolve (free)** | — | 4K, Arabic titles/subtitles, mix |

`produce_episode.py` orchestrates 2→6 in order, **auto-picking** the animate
backend (fal if `FAL_KEY`, else ComfyUI if `COMFY_URL`), and **degrading
gracefully** to the Ken-Burns stills draft if no animate backend is set.

## The two animation paths (pick one when the subscription lands)

- **Path A — cloud (no hardware):** set `FAL_KEY`. Seedance 2.0 Fast ≈ **$4–5 / 3-min ep**, runs immediately. See `pipeline/animate_fal.py`.
- **Path B — rented/owned RTX:** bring up a ComfyUI box (`pipeline/comfy/setup_comfyui.sh` or the `Dockerfile`), set `COMFY_URL`. LTX-2.3 ≈ **$0.5–1.5 / ep at 4K**. See `pipeline/comfy/SETUP_RUNPOD.md`.

Both write `build/<ep>/clips_anim/shotNN.mp4`; the assembler prefers those over stills automatically.

## Producing all 10 episodes

1. **Approve** ep02–ep10 `source_text` → `docs/SHARIAH_REVIEW_ep02-ep10.md` (the only human gate).
2. Run **Workflow A/B** per approved episode → its `shotlist_json`.
3. For each episode: `EPISODE=epNN python3 pipeline/produce_episode.py`.
4. Finish in **DaVinci Resolve** (free) — color, Arabic animated subtitles, 4K.

Budget for all 10 (Path B): **~$12–18 of GPU time**; voices ~$1; DaVinci $0.

## Files added for "everything ready"

```
.env.example                     all keys/knobs, documented (no secrets)
pipeline/preflight.py            "is it ready?" doctor (per path)
pipeline/produce_episode.py      one-command orchestrator (auto-picks backend)
pipeline/animate_fal.py          Path A · cloud image-to-video (fal.ai)
pipeline/comfy/animate_episode.py  Path B · ComfyUI image-to-video (GPU)
pipeline/comfy/setup_comfyui.sh  one-shot GPU-box provision
pipeline/comfy/Dockerfile        reproducible image (pod or serverless)
pipeline/comfy/workflow_ltx2_i2v.api.json  titled i2v workflow template
pipeline/build_ep01.py           universal assembler (animated clips OR stills)
pipeline/revoice_elevenlabs.py   real Arabic voices
pipeline/upload_to_supabase.py   persist assets + DB
docs/SERIES_PRODUCTION_PLAN.md   the plan + costs
docs/SHARIAH_REVIEW_ep02-ep10.md the approval gate for the 9 remaining episodes
```

No secrets are committed — every key is read from the environment at run time.
