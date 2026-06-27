#!/usr/bin/env bash
# GGUF-quantized Wan 2.2 S2V (fits a 24GB GPU -> no offloading) + ALL its deps, so this
# is self-contained on a blank volume (no "already on the pod" assumptions):
#   unet/        Wan2.2-S2V-14B-Q5_K_M.gguf      (~10 GB)
#   text_encoders/ umt5_xxl_fp8_e4m3fn_scaled    (CLIPLoader type=wan)
#   audio_encoders/wav2vec2_large_english_fp16   (AudioEncoderLoader)
#   vae/         wan_2.1_vae.safetensors         (S2V uses the 2.1 VAE)
#   COMFY_ROOT=/workspace/ComfyUI bash pipeline/comfy/download_models_wan_s2v_gguf.sh
set -e
COMFY_ROOT="${COMFY_ROOT:-/workspace/ComfyUI}"
HF="${HF_TOKEN:-}"
UNET="$COMFY_ROOT/models/unet"; TE="$COMFY_ROOT/models/text_encoders"
AE="$COMFY_ROOT/models/audio_encoders"; VAE="$COMFY_ROOT/models/vae"
mkdir -p "$UNET" "$TE" "$AE" "$VAE"
"$COMFY_ROOT/venv/bin/pip" install -q -U "huggingface_hub[cli]" 2>/dev/null || true
HFCLI=""
for c in "$COMFY_ROOT/venv/bin/hf" "$(command -v hf 2>/dev/null)" \
         "$COMFY_ROOT/venv/bin/huggingface-cli" "$(command -v huggingface-cli 2>/dev/null)"; do
  [ -n "$c" ] && [ -x "$c" ] && { HFCLI="$c"; break; }
done
[ -n "$HFCLI" ] || { echo "!! no hf cli"; exit 1; }
get() { # repo path destdir  -> flattens any split_files/ path to destdir
  local repo="$1" path="$2" dest="$3" fn; fn="$(basename "$path")"
  [ -s "$dest/$fn" ] && { echo "   $fn present, skip"; return; }
  local stage; stage="$(mktemp -d)"
  "$HFCLI" download "$repo" "$path" --local-dir "$stage" ${HF:+--token "$HF"}
  mv -f "$stage/$path" "$dest/" 2>/dev/null || find "$stage" -name "$fn" -exec mv -f {} "$dest/" \;
  rm -rf "$stage"; }

G="${WAN_S2V_GGUF:-Wan2.2-S2V-14B-Q5_K_M.gguf}"
echo "==> $G (~10 GB)"
[ -s "$UNET/$G" ] || "$HFCLI" download QuantStack/Wan2.2-S2V-14B-GGUF "$G" --local-dir "$UNET" ${HF:+--token "$HF"}
echo "==> umt5 text encoder (CLIPLoader type=wan)"
get Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors "$TE"
echo "==> wav2vec2 audio encoder"
get Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/audio_encoders/wav2vec2_large_english_fp16.safetensors "$AE"
echo "==> Wan 2.1 VAE (S2V uses this one)"
get Comfy-Org/Wan_2.1_ComfyUI_repackaged split_files/vae/wan_2.1_vae.safetensors "$VAE"
echo "== unet =="; ls -la "$UNET"/*.gguf
echo "== text_encoders =="; ls -la "$TE"
echo "DONE"
