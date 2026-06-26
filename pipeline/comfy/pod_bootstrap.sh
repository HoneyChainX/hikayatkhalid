#!/usr/bin/env bash
# One-shot pod provisioner: install ComfyUI + nodes + LTX models and launch ComfyUI on :8188.
# Run ONCE in the RunPod web terminal:
#   cd /workspace && curl -sL https://raw.githubusercontent.com/HoneyChainX/hikayatkhalid/claude/zealous-cerf-jhk0of/pipeline/comfy/pod_bootstrap.sh | bash
# After it prints "PROVISIONED", ComfyUI is reachable on the pod's :8188 proxy and Claude
# can drive the rest (the proof + future episodes) over that URL via the RunPod API.
set -e
export DEBIAN_FRONTEND=noninteractive
export COMFY_ROOT="${COMFY_ROOT:-/workspace/ComfyUI}"

echo "== [1/4] system deps =="
apt-get update -y >/dev/null 2>&1 && apt-get install -y git wget aria2 ffmpeg curl >/dev/null 2>&1 || true

echo "== [2/4] repo =="
cd /workspace
[ -d hikayatkhalid ] || git clone https://github.com/HoneyChainX/hikayatkhalid
cd hikayatkhalid
git fetch origin && git checkout claude/zealous-cerf-jhk0of && git pull origin claude/zealous-cerf-jhk0of

echo "== [3/4] ComfyUI + nodes + LTX models (~15-25 min first time) =="
bash pipeline/comfy/setup_comfyui.sh
bash pipeline/comfy/download_models_ltx.sh

echo "== [4/4] launch ComfyUI on :8188 =="
bash pipeline/comfy/start_comfy.sh

echo ""
echo "✅ PROVISIONED — ComfyUI is up on :8188 (persists via nohup)."
echo "   Models + repo live on the /workspace volume, so future starts only need start_comfy.sh."
echo "   Tell Claude it's ready; it will run the proof over the :8188 proxy."
