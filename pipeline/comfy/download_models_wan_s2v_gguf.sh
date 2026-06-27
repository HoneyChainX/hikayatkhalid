#!/usr/bin/env bash
# GGUF-quantized Wan 2.2 S2V (fits a 24GB GPU -> no offloading -> much faster).
#   COMFY_ROOT=/workspace/ComfyUI bash pipeline/comfy/download_models_wan_s2v_gguf.sh
set -e
COMFY_ROOT="${COMFY_ROOT:-/workspace/ComfyUI}"
HF="${HF_TOKEN:-}"
UNET="$COMFY_ROOT/models/unet"; mkdir -p "$UNET"
"$COMFY_ROOT/venv/bin/pip" install -q -U "huggingface_hub[cli]" 2>/dev/null || true
HFCLI=""
for c in "$COMFY_ROOT/venv/bin/hf" "$(command -v hf 2>/dev/null)" "$COMFY_ROOT/venv/bin/huggingface-cli" "$(command -v huggingface-cli 2>/dev/null)"; do
  [ -n "$c" ] && [ -x "$c" ] && { HFCLI="$c"; break; }
done
[ -n "$HFCLI" ] || { echo "!! no hf cli"; exit 1; }
G="${WAN_S2V_GGUF:-Wan2.2-S2V-14B-Q5_K_M.gguf}"
echo "==> $G (~10 GB)"
[ -s "$UNET/$G" ] || "$HFCLI" download QuantStack/Wan2.2-S2V-14B-GGUF "$G" --local-dir "$UNET" ${HF:+--token "$HF"}
ls -la "$UNET"/*.gguf
echo "DONE"
