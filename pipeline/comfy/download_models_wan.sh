#!/usr/bin/env bash
# Wan 2.2 TI2V-5B image-to-video models for ComfyUI (high quality, fits a 24GB GPU).
# Verified files (docs.comfy.org/tutorials/video/wan/wan2_2):
#   wan2.2_ti2v_5B_fp16.safetensors        -> models/diffusion_models/
#   umt5_xxl_fp8_e4m3fn_scaled.safetensors -> models/text_encoders/   (from the Wan 2.1 repack)
#   wan2.2_vae.safetensors                 -> models/vae/
#
#   COMFY_ROOT=/workspace/ComfyUI bash pipeline/comfy/download_models_wan.sh
set -e
COMFY_ROOT="${COMFY_ROOT:-/workspace/ComfyUI}"
HF="${HF_TOKEN:-}"
DM="$COMFY_ROOT/models/diffusion_models"; TE="$COMFY_ROOT/models/text_encoders"; VAE="$COMFY_ROOT/models/vae"
mkdir -p "$DM" "$TE" "$VAE"

"$COMFY_ROOT/venv/bin/pip" install -q -U "huggingface_hub[cli]" 2>/dev/null || \
  pip install -q -U "huggingface_hub[cli]" 2>/dev/null || true
HFCLI=""
for c in "$COMFY_ROOT/venv/bin/hf" "$(command -v hf 2>/dev/null)" \
         "$COMFY_ROOT/venv/bin/huggingface-cli" "$(command -v huggingface-cli 2>/dev/null)"; do
  [ -n "$c" ] && [ -x "$c" ] && { HFCLI="$c"; break; }
done
[ -n "$HFCLI" ] || { echo "!! no hf / huggingface-cli found"; exit 1; }
echo "   using: $HFCLI"

get() { # repo  path-in-repo  destdir
  local repo="$1" path="$2" dest="$3" fn; fn="$(basename "$path")"
  if [ -s "$dest/$fn" ]; then echo "   $fn present, skip"; return; fi
  local stage; stage="$(mktemp -d)"
  "$HFCLI" download "$repo" "$path" --local-dir "$stage" ${HF:+--token "$HF"}
  mv -f "$stage/$path" "$dest/" 2>/dev/null || find "$stage" -name "$fn" -exec mv -f {} "$dest/" \;
  rm -rf "$stage"
}

echo "==> Wan 2.2 TI2V-5B diffusion (~10 GB)"
get Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors "$DM"
echo "==> umt5-xxl text encoder (~6.7 GB)"
get Comfy-Org/Wan_2.1_ComfyUI_repackaged split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors "$TE"
echo "==> Wan 2.2 VAE"
get Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/vae/wan2.2_vae.safetensors "$VAE"

echo "== diffusion_models =="; ls -la "$DM"
echo "== text_encoders =="; ls -la "$TE"
echo "== vae =="; ls -la "$VAE"
echo "DONE — verify: animate_one.py --diagnose, then render with --workflow workflow_wan22_i2v.api.json"
