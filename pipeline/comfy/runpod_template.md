# RunPod template — copy-paste a ready-to-run box (LoRA training + animation)

A single pod that trains the character LoRAs **and** animates episodes. Sized for the
full RTX-LoRA path (`docs/RTX_LORA_SETUP.md`): Flux LoRA training needs ~24 GB VRAM and
FLUX.1-dev (~24 GB on disk) + LTX-2.3 / Wan models.

## Recommended pod

| Field | Value |
|---|---|
| **GPU** | **RTX 4090 (24 GB)** — community ≈ $0.34–0.69/hr (A5000/A6000/A100 also fine) |
| **Template** | RunPod **"ComfyUI"** or **"RunPod PyTorch 2.4"** (CUDA 12.x) |
| **Container image** | `runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04` |
| **Container disk** | **30 GB** |
| **Volume disk** | **80 GB** → mount `/workspace` (holds FLUX.1-dev + LTX/Wan + datasets) |
| **Expose HTTP ports** | **8188** (ComfyUI), 8888 (Jupyter, optional) |
| **Expose TCP ports** | 22 (SSH) |
| **Env vars** | `HF_TOKEN=<your token>` (accept the FLUX.1-dev license on HF first) |

## Option 1 — Web UI (fastest)

1. RunPod ▸ **Deploy** ▸ pick an **RTX 4090** (Community Cloud is cheapest).
2. **Edit Template** → set the **container image**, **container disk 30 GB**,
   **volume disk 80 GB** mounted at `/workspace`, expose HTTP **8188**, add env `HF_TOKEN`.
3. Deploy → open a terminal (Web Terminal or SSH) and run **Bring-up** below.

## Option 2 — CLI (`runpodctl`)

```bash
runpodctl create pod \
  --name hikayat-rtx \
  --gpuType "NVIDIA GeForce RTX 4090" --gpuCount 1 \
  --imageName "runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04" \
  --containerDiskSize 30 --volumeSize 80 --volumePath /workspace \
  --ports "8188/http,8888/http,22/tcp" \
  --env HF_TOKEN=$HF_TOKEN
```

## Bring-up (once per pod)

```bash
cd /workspace
git clone https://github.com/HoneyChainX/hikayatkhalid && cd hikayatkhalid
export COMFY_ROOT=/workspace/ComfyUI
bash pipeline/comfy/setup_comfyui.sh        # ComfyUI + LTX-2.3/Wan + nodes
nohup ~/start_comfy.sh >/workspace/comfy.log 2>&1 &   # serves on :8188
# COMFY_URL for off-box runs: https://<POD_ID>-8188.proxy.runpod.net
```

## Then: train a LoRA, animate (per `docs/RTX_LORA_SETUP.md`)

```bash
# ① render build/lora/khalid/NN.png in ComfyUI (Flux Kontext, identity from
#    assets/characters/khalid_ref.png) — captions/prompts already prepared.
export HF_TOKEN=...
CHAR=khalid bash pipeline/comfy/train_character_lora.sh      # ② ~45 min
# ③ keyframes with the trigger token, then:
export COMFY_URL=https://<POD_ID>-8188.proxy.runpod.net
EPISODE=ep03 python3 pipeline/comfy/animate_episode.py        # ④ → clips_anim/
EPISODE=ep03 python3 pipeline/produce_episode.py              # ⑤ assemble
```

## Cost snapshot

| Phase | GPU-time | ~$ (4090 @ $0.44/hr) |
|---|---|---|
| Bring-up + model downloads | ~20–30 min | ~$0.2 |
| Train 3 character LoRAs | ~2–2.5 hr | ~$1–1.5 (one-time) |
| Animate a 30-shot episode | ~0.5–1 hr | ~$0.3–0.7 |

**Stop the pod when idle** — you pay per minute. Persist outputs to the **80 GB volume**
(or push keyframes/clips to the repo / object storage) so a stopped pod loses nothing.

## Serverless (hands-off batch)

For unattended episode runs, wrap the ComfyUI graph with
[`runpod-workers/worker-comfyui`](https://github.com/runpod-workers/worker-comfyui) and pay
only per render instead of keeping a pod warm.

> Secrets: `HF_TOKEN` lives only in the pod's env — never commit it.
