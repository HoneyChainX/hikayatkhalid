#!/usr/bin/env bash
# Install the SeedVR2 video upscaler/restorer custom node (numz, most-maintained).
# The DiT/VAE models auto-download to models/SEEDVR2 on first use (3B FP16 fits 24GB).
#   COMFY_ROOT=/workspace/ComfyUI bash pipeline/comfy/install_seedvr2.sh
set -e
COMFY_ROOT="${COMFY_ROOT:-/workspace/ComfyUI}"
cd "$COMFY_ROOT/custom_nodes"
[ -d ComfyUI-SeedVR2_VideoUpscaler ] || git clone https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler
cd ComfyUI-SeedVR2_VideoUpscaler
git pull --ff-only || true
PIP="$COMFY_ROOT/venv/bin/pip"
[ -x "$PIP" ] || PIP=pip
[ -f requirements.txt ] && "$PIP" install -q -r requirements.txt || true
echo "DONE — SeedVR2 nodes installed (restart ComfyUI to register). Model auto-downloads on first run."
echo "Nodes: 'SeedVR2 Video Upscaler', 'SeedVR2 (Down)Load DiT Model', 'SeedVR2 (Down)Load VAE Model'"
