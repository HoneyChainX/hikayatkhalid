#!/usr/bin/env bash
# Set up the S2V pipeline in an ISOLATED dir (/workspace/comfy-s2v) so it never clashes
# with an existing /workspace/ComfyUI (e.g. an LTX setup on the same network volume),
# download only our models (~40GB), and launch ONE ComfyUI per GPU for parallel rendering.
#   curl -sL https://raw.githubusercontent.com/HoneyChainX/hikayatkhalid/claude/zealous-cerf-jhk0of/pipeline/comfy/pod_setup_s2v_multi.sh | bash
set -e
export DEBIAN_FRONTEND=noninteractive
ROOT="${COMFY_ROOT:-/workspace/comfy-s2v}"

echo "== [1/5] system deps =="
apt-get update -y >/dev/null 2>&1 && apt-get install -y git wget aria2 ffmpeg curl python3-venv >/dev/null 2>&1 || true

echo "== [2/5] repo =="
cd /workspace
[ -d hikayatkhalid ] || git clone https://github.com/HoneyChainX/hikayatkhalid
cd hikayatkhalid && git fetch origin && git checkout claude/zealous-cerf-jhk0of && git pull origin claude/zealous-cerf-jhk0of

echo "== [3/5] ComfyUI (isolated at $ROOT) + venv + torch + nodes =="
[ -d "$ROOT" ] || git clone https://github.com/comfyanonymous/ComfyUI "$ROOT"
cd "$ROOT"
[ -d venv ] || python3 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
python -c "import torch" 2>/dev/null || pip install -q torch torchvision --index-url https://download.pytorch.org/whl/cu124 || pip install -q torch torchvision
pip install -q -r requirements.txt
pip install -q "huggingface_hub[cli]"
cd custom_nodes
for repo in ltdrdata/ComfyUI-Manager city96/ComfyUI-GGUF kijai/ComfyUI-KJNodes Kosinkadink/ComfyUI-VideoHelperSuite numz/ComfyUI-SeedVR2_VideoUpscaler; do
  d=$(basename "$repo"); [ -d "$d" ] || git clone "https://github.com/$repo" "$d"
  [ -f "$d/requirements.txt" ] && pip install -q -r "$d/requirements.txt" || true
done
cd /workspace/hikayatkhalid

echo "== [4/5] models (Flux Kontext + S2V GGUF + deps; ~40GB) =="
COMFY_ROOT="$ROOT" bash pipeline/comfy/download_models_flux_kontext.sh
COMFY_ROOT="$ROOT" bash pipeline/comfy/download_models_wan_s2v_gguf.sh

echo "== [5/5] launch one ComfyUI per GPU =="
COMFY_ROOT="$ROOT" bash pipeline/comfy/start_comfy_multi.sh
echo ""
echo "✅ READY — parallel S2V on all GPUs (ports 8188 + 19123). SeedVR2 weights auto-download on first upscale."
