#!/usr/bin/env bash
# BLANK volume -> full Hikayat S2V pipeline (Flux Kontext + Wan-S2V GGUF + SeedVR2), then
# launch ComfyUI on :8188. Downloads ONLY the current pipeline (~40GB; skips LTX/Wan-5B).
# Run ONCE in a fresh RunPod web terminal:
#   curl -sL https://raw.githubusercontent.com/HoneyChainX/hikayatkhalid/claude/zealous-cerf-jhk0of/pipeline/comfy/pod_setup_s2v.sh | bash
set -e
export DEBIAN_FRONTEND=noninteractive
ROOT="${COMFY_ROOT:-/workspace/ComfyUI}"

echo "== [1/5] system deps =="
apt-get update -y >/dev/null 2>&1 && apt-get install -y git wget aria2 ffmpeg curl python3-venv >/dev/null 2>&1 || true

echo "== [2/5] repo =="
cd /workspace
[ -d hikayatkhalid ] || git clone https://github.com/HoneyChainX/hikayatkhalid
cd hikayatkhalid && git fetch origin && git checkout claude/zealous-cerf-jhk0of && git pull origin claude/zealous-cerf-jhk0of

echo "== [3/5] ComfyUI + venv + torch + nodes =="
cd /workspace
[ -d ComfyUI ] || git clone https://github.com/comfyanonymous/ComfyUI
cd "$ROOT"
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
python -c "import torch" 2>/dev/null || pip install -q torch torchvision --index-url https://download.pytorch.org/whl/cu124 || pip install -q torch torchvision
pip install -q -r requirements.txt
pip install -q "huggingface_hub[cli]"
cd custom_nodes
for repo in \
  https://github.com/ltdrdata/ComfyUI-Manager \
  https://github.com/city96/ComfyUI-GGUF \
  https://github.com/kijai/ComfyUI-KJNodes \
  https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite \
  https://github.com/numz/ComfyUI-SeedVR2_VideoUpscaler ; do
  d=$(basename "$repo"); [ -d "$d" ] || git clone "$repo" "$d"
  [ -f "$d/requirements.txt" ] && pip install -q -r "$d/requirements.txt" || true
done
cd /workspace/hikayatkhalid

echo "== [4/5] models (Flux Kontext + S2V GGUF + deps; ~40GB) =="
COMFY_ROOT="$ROOT" bash pipeline/comfy/download_models_flux_kontext.sh
COMFY_ROOT="$ROOT" bash pipeline/comfy/download_models_wan_s2v_gguf.sh

echo "== [5/5] launch ComfyUI =="
COMFY_ROOT="$ROOT" bash pipeline/comfy/start_comfy.sh
echo ""
echo "✅ READY — S2V pipeline up on :8188. SeedVR2 weights auto-download on first upscale."
