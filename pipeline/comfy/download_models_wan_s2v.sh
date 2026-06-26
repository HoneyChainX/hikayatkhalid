#!/usr/bin/env bash
# Wan 2.2 S2V (Speech-to-Video, audio-driven lip-sync) models for ComfyUI.
# Reuses the umt5 already on the pod. Verified paths via HF API.
#   wan2.2_s2v_14B_fp8_scaled.safetensors  -> diffusion_models/
#   wav2vec2_large_english_fp16.safetensors-> audio_encoders/
#   wan_2.1_vae.safetensors                -> vae/
set -e
COMFY_ROOT="${COMFY_ROOT:-/workspace/ComfyUI}"
HF="${HF_TOKEN:-}"
DM="$COMFY_ROOT/models/diffusion_models"; AE="$COMFY_ROOT/models/audio_encoders"; VAE="$COMFY_ROOT/models/vae"
mkdir -p "$DM" "$AE" "$VAE"
"$COMFY_ROOT/venv/bin/pip" install -q -U "huggingface_hub[cli]" 2>/dev/null || true
HFCLI=""
for c in "$COMFY_ROOT/venv/bin/hf" "$(command -v hf 2>/dev/null)" \
         "$COMFY_ROOT/venv/bin/huggingface-cli" "$(command -v huggingface-cli 2>/dev/null)"; do
  [ -n "$c" ] && [ -x "$c" ] && { HFCLI="$c"; break; }
done
[ -n "$HFCLI" ] || { echo "!! no hf cli"; exit 1; }
get() { local repo="$1" path="$2" dest="$3" fn; fn="$(basename "$path")"
  [ -s "$dest/$fn" ] && { echo "   $fn present, skip"; return; }
  local stage; stage="$(mktemp -d)"
  "$HFCLI" download "$repo" "$path" --local-dir "$stage" ${HF:+--token "$HF"}
  mv -f "$stage/$path" "$dest/" 2>/dev/null || find "$stage" -name "$fn" -exec mv -f {} "$dest/" \;
  rm -rf "$stage"; }
echo "==> Wan 2.2 S2V 14B (fp8, ~16 GB)"
get Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/diffusion_models/wan2.2_s2v_14B_fp8_scaled.safetensors "$DM"
echo "==> wav2vec2 audio encoder"
get Comfy-Org/Wan_2.2_ComfyUI_Repackaged split_files/audio_encoders/wav2vec2_large_english_fp16.safetensors "$AE"
echo "==> Wan 2.1 VAE (S2V uses this one)"
get Comfy-Org/Wan_2.1_ComfyUI_repackaged split_files/vae/wan_2.1_vae.safetensors "$VAE"
echo "== diffusion_models =="; ls -la "$DM"
echo "== audio_encoders =="; ls -la "$AE"
echo "DONE"
