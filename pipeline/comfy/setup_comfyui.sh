#!/usr/bin/env bash
# Path B — provision a rented/owned NVIDIA RTX box (RunPod/Vast/local) with
# ComfyUI + the nodes & models needed to animate Hikayat Khalid shots (LTX-2.3).
# Tested target: Ubuntu 22.04 + CUDA 12.x, NVIDIA RTX (16-24 GB VRAM ideal; 8 GB
# works with GGUF Q4). Run once per fresh pod:
#     bash setup_comfyui.sh && ~/start_comfy.sh
set -euo pipefail

ROOT="${COMFY_ROOT:-$HOME/ComfyUI}"
HF="${HF_TOKEN:-}"                      # optional, for gated/faster HF downloads
py() { python3 "$@"; }

echo "==> system deps"
sudo apt-get update -y && sudo apt-get install -y git wget aria2 ffmpeg python3-venv || true

echo "==> ComfyUI"
[ -d "$ROOT" ] || git clone https://github.com/comfyanonymous/ComfyUI "$ROOT"
cd "$ROOT"
python3 -m venv venv && source venv/bin/activate
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124 || pip install torch torchvision
pip install -r requirements.txt
pip install "huggingface_hub[cli]"

echo "==> custom nodes (Manager + GGUF + KJNodes + VideoHelperSuite)"
cd custom_nodes
for repo in \
  https://github.com/ltdrdata/ComfyUI-Manager \
  https://github.com/city96/ComfyUI-GGUF \
  https://github.com/kijai/ComfyUI-KJNodes \
  https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite ; do
  d=$(basename "$repo"); [ -d "$d" ] || git clone "$repo" "$d"
  [ -f "$d/requirements.txt" ] && pip install -r "$d/requirements.txt" || true
done
cd "$ROOT"

echo "==> models (LTX-2.3 GGUF + LoRA + VAE + T5)"
dl() { huggingface-cli download "$1" "$2" --local-dir "$3" ${HF:+--token "$HF"} || \
       echo "  !! verify repo/file: $1 :: $2"; }
mkdir -p models/unet models/loras models/vae models/text_encoders models/checkpoints
# LTX-2.3 quantized transformer (pick a quant that fits your VRAM: Q8 ~22GB, Q4 ~12GB)
dl unsloth/LTX-2.3-GGUF        "LTX-2.3-Q8_0.gguf"                              models/unet
# distilled LoRA (far fewer steps = much faster/cheaper)
dl Lightricks/LTX-2.3          "ltx-2.3-22b-distilled-lora-384-1.1.safetensors" models/loras
# VAE + T5 text encoder
dl Lightricks/LTX-2.3          "vae/diffusion_pytorch_model.safetensors"        models/vae
dl city96/t5-v1_1-xxl-encoder-gguf "t5-v1_1-xxl-encoder-Q8_0.gguf"             models/text_encoders
echo "   (filenames drift between releases — if a download warns, browse the HF repo and adjust.)"

echo "==> launcher"
cat > "$HOME/start_comfy.sh" <<EOF
#!/usr/bin/env bash
cd "$ROOT" && source venv/bin/activate
python3 main.py --listen 0.0.0.0 --port 8188 "\$@"
EOF
chmod +x "$HOME/start_comfy.sh"

cat <<'NEXT'

==> DONE. Next:
  1) start ComfyUI:        ~/start_comfy.sh
  2) open it (RunPod proxy URL or http://POD_IP:8188), then
     Workflow ▸ Templates ▸ "LTX-2 Image to Video" — load it, title the nodes
     KEYFRAME / POSITIVE / NEGATIVE / SAMPLER / LENGTH, add the distilled LoRA,
     Export (API) → save over pipeline/comfy/workflow_ltx2_i2v.api.json.
  3) from your repo (can be local; point COMFY_URL at the pod):
       export COMFY_URL=https://<pod>-8188.proxy.runpod.net
       python3 pipeline/comfy/animate_episode.py
  4) stitch: python3 pipeline/build_ep01.py  (or finish in DaVinci Resolve)
NEXT
