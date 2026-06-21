# Path B — rented/owned RTX animation pipeline (~$1/episode, 4K)

Animate Hikayat Khalid episodes with **ComfyUI + LTX‑2.3** (open weights) on a
rented NVIDIA GPU, for **~$0.5–1.5/episode** instead of ~$5 cloud. This is
**Stage 3** of the [series plan](../../docs/SERIES_PRODUCTION_PLAN.md): it turns
the consistent keyframes we already produce into real motion clips.

## Pieces in this folder

| File | Role |
|---|---|
| `setup_comfyui.sh` | one-time provision of the GPU box (ComfyUI + nodes + LTX‑2.3 models) |
| `workflow_ltx2_i2v.api.json` | image‑to‑video workflow template (nodes titled for the orchestrator) |
| `animate_episode.py` | drives ComfyUI's API: per shot → upload keyframe, queue, download clip |

## Flow (end to end)

```
[keyframes]  rerender_balancer.py  -> build/ep01/img/shotNN.jpg   (consistent Khalid)
[animate ]   animate_episode.py    -> build/ep01/clips_anim/shotNN.mp4  (on the GPU box)
[voice   ]   revoice_elevenlabs.py -> build/ep01/audio/shotNN.mp3
[stitch  ]   build_ep01.py  (quick)  OR  DaVinci Resolve  (broadcast finish)
```

## Steps

1. **Rent a GPU.** RunPod or Vast, an **RTX 4090 / L40S / A10G (16–24 GB)**.
   RunPod community 4090 ≈ **$0.34–0.69/hr**. Pick the "ComfyUI" or a CUDA 12
   PyTorch template.
2. **Provision** (once per pod):
   ```bash
   git clone <this repo> && cd hikayatkhalid
   bash pipeline/comfy/setup_comfyui.sh      # installs ComfyUI + nodes + LTX‑2.3
   ~/start_comfy.sh                          # serves on :8188
   ```
3. **Lock the workflow** (once): open ComfyUI, load **Templates ▸ "LTX‑2 Image to
   Video"**, attach the **distilled LoRA** (fewer steps = cheaper), set node
   **titles** `KEYFRAME / POSITIVE / NEGATIVE / SAMPLER / LENGTH`, then
   **Workflow ▸ Export (API)** over `pipeline/comfy/workflow_ltx2_i2v.api.json`.
   *(The shipped JSON is a classic‑LTXV reference so the orchestrator runs out of
   the box; the official LTX‑2.3 template gives the best quality.)*
4. **Animate** (from anywhere — point at the pod):
   ```bash
   export COMFY_URL=https://<pod-id>-8188.proxy.runpod.net   # or http://POD_IP:8188
   export KEYFRAME_DIR=build/ep01/img
   python3 pipeline/comfy/animate_episode.py     # -> build/ep01/clips_anim/shotNN.mp4
   ```
   Resumable (skips finished shots); per‑shot duration auto‑matches the narration.
5. **Stitch & finish:** `python3 pipeline/build_ep01.py` for a quick cut, or import
   `clips_anim/` + `audio/` into **DaVinci Resolve** for color, Arabic
   titles/animated subtitles, audio mix, and **Super Scale → 4K**.

## Cost & time (3‑min episode ≈ 20–36 clips of ~5 s)

| GPU | $/hr | speed (5 s, GGUF+distilled, 720p) | episode time | **$/episode** |
|---|---|---|---|---|
| RTX 4090 | ~$0.44 | ~1–2 min/clip | ~45–90 min | **~$0.5–0.7** |
| L40S / A10G | ~$0.6–0.8 | ~1.5–3 min/clip | ~1–1.8 h | **~$0.8–1.4** |

Full‑fp16 1080p/4K is much slower (4090: ~7–8 min/10 s at 1080p, ~25–30 min at
4K) — use **GGUF + distilled LoRA at 720p** for budget, upscale to 4K in DaVinci.
Sources: [RTX + LTX‑2 + ComfyUI](https://blogs.nvidia.com/blog/rtx-ai-garage-ces-2026-open-models-video-generation/) ·
[LTX‑2 GGUF guide](https://dev.to/gary_yan_86eb77d35e0070f5/how-to-install-and-configure-ltx-2-gguf-models-in-comfyui-complete-2026-guide-1d3m) ·
[worker‑comfyui (serverless)](https://github.com/runpod-workers/worker-comfyui).

## Quality & consistency notes

- The **start frame is the identity anchor** — always feed the locked keyframe
  (our Kontext/nano‑banana output). Short clips (5–8 s) drift less.
- Swap LTX‑2.3 → **Wan 2.2 Animate** (same orchestrator, different template) when
  a shot needs stronger character‑motion fidelity.
- For dialogue shots, run **LivePortrait** (free, add the custom node) driven by
  the shot's ElevenLabs mp3 to lip‑sync Khalid/Noor/Teta.
- **Serverless option:** for hands‑off batch runs, wrap this graph with
  `runpod-workers/worker-comfyui` and pay only per render.

## No secrets

`HF_TOKEN` (optional, for faster model pulls) and any keys are read from the
environment only — never commit them.
