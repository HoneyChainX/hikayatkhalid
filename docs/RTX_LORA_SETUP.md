# RTX + character-LoRA setup — high quality AND locked characters

Goal: run the **story-world shots** (and, if you want, a fully-generative version of the
whole series) on a rented/owned **NVIDIA RTX**, at **high quality (up to 4K)** with
**locked character identity** via a trained **character LoRA**. This is the "very
consistent generative" path from `docs/TOOLS_EVAL.md` — excellent, and ~$0/clip of
generation once the box is up.

> Reminder of the honest trade-off (`docs/PRODUCTION_HYBRID.md`): a trained LoRA makes
> characters **very** consistent, not *identical*. For the recurring cast in dialogue, the
> **Character Animator puppet** is still the only truly-fixed option. The RTX-LoRA path
> shines for story scenes and for any character you'd rather generate than rig.

## The box

| Option | VRAM | ~$/hr | Notes |
|---|---|---|---|
| RunPod / Vast **RTX 4090** | 24 GB | $0.34–0.69 | sweet spot: trains a LoRA in ~30–60 min, animates LTX/Wan |
| **A100 80 GB** | 80 GB | $1.2–1.9 | faster training + 4K headroom |
| Owned RTX (≥16 GB) | 16–24 GB | $0 (power) | 8–16 GB works with NF4/GGUF, slower |

Provision once: `bash pipeline/comfy/setup_comfyui.sh && ~/start_comfy.sh` (installs ComfyUI
+ LTX-2.3 / Wan nodes + models). Then export `COMFY_URL=https://<pod>-8188.proxy.runpod.net`.

## The flow (per character, then per episode)

```
assets/characters/<char>_ref.png          (the locked reference — already in the repo)
   │  ① lora_dataset.py  → 24 varied prompts + captions
   ▼
build/lora/<char>/NN.png + NN.txt          (render NN.png with Flux Kontext, identity from ref)
   │  ② train_character_lora.sh  → Flux LoRA (~30–60 min on a 4090)
   ▼
ComfyUI/models/loras/<char>_lora.safetensors   (trigger token, e.g. kh4lidboy)
   │  ③ keyframes: prompt with the trigger → perfectly on-model shot stills
   ▼
build/<ep>/img/shotNN.jpg
   │  ④ animate: pipeline/comfy/animate_episode.py (LTX/Wan i2v)  → clips_anim/shotNN.mp4
   ▼
   ⑤ assemble: pipeline/build_ep01.py  (+ voices)  → build/<ep>/ep01.mp4
```

## Step by step

**① Prepare each character's dataset** (already have the refs):
```bash
python3 pipeline/comfy/lora_dataset.py --char khalid   # and: noor, teta
```
Then on the GPU box, render the 24 prompts in `build/lora/khalid/prompts.jsonl` with
**Flux Kontext** in ComfyUI — load `assets/characters/khalid_ref.png` as the Kontext image so
the face/outfit stay locked; save outputs as `build/lora/khalid/01.png … 24.png`. Keep the
20-ish cleanest, on-model ones (quality > quantity).

**② Train the LoRA:**
```bash
export HF_TOKEN=...        # accept the FLUX.1-dev license on HF first
CHAR=khalid bash pipeline/comfy/train_character_lora.sh
# -> ComfyUI/models/loras/khalid_lora.safetensors   (trigger: kh4lidboy)
```

**③ Generate locked keyframes** in ComfyUI: a normal Flux text-to-image graph with the
LoRA loaded; start each shot prompt with the trigger token, e.g.
`kh4lidboy, sitting in a sunny garden looking worried, flat 2D vector cartoon …`.
Save to `build/<ep>/img/shotNN.jpg`. (Use `pipeline/<ep>_shotlist.json` for the shot prompts;
`route_shots.py` tells you which shots are story/`wan_*` vs puppet.)

**④ Animate** the keyframes (existing Path-B orchestrator):
```bash
export COMFY_URL=https://<pod>-8188.proxy.runpod.net
EPISODE=ep03 python3 pipeline/comfy/animate_episode.py     # LTX/Wan i2v -> clips_anim/
```

**⑤ Assemble** (unchanged): `EPISODE=ep03 python3 pipeline/produce_episode.py`.

## Two LoRA strategies

- **A · Flux image-LoRA → i2v (recommended, in this guide).** Lock identity at the *keyframe*
  with the LoRA, then let LTX/Wan add motion from that start frame. Robust, cheap to train,
  works on 24 GB, and the keyframe is the identity anchor so video drift is minimal.
- **B · Wan video-LoRA (advanced).** Train a LoRA on the *video* model itself
  (`diffusion-pipe`, needs more VRAM/time) for identity directly in motion. Use only if A
  still drifts on long takes; most kids'-show shots are short (5–8 s) where A is enough.

## Cost & time (one-time vs per-episode)

| | One-time | Per episode |
|---|---|---|
| LoRA training (3 chars × ~45 min) | ~2–3 GPU-hrs ≈ **$1–2** | — |
| Keyframes + animate (story shots) | — | ~0.5–1 GPU-hr ≈ **$0.3–0.7** |
| Voices / assembly / finish | — | ElevenLabs ~$0.1 · DaVinci $0 |

After the one-time LoRA training, story shots cost **well under $1/episode**, 4K, no watermark,
commercial-safe (LTX/Wan are open), with characters held very consistent by the LoRA + keyframe.

## Where this plugs into the repo

- Reuses: `pipeline/comfy/setup_comfyui.sh`, `animate_episode.py`, `workflow_ltx2_i2v.api.json`,
  `build_ep01.py`, `route_shots.py`.
- Adds: `lora_dataset.py` (dataset prep), `ai_toolkit_flux_lora.yaml` (train config),
  `train_character_lora.sh` (training), this guide.
- Character refs to train from: `assets/characters/{khalid,noor,teta}_ref.png`.
