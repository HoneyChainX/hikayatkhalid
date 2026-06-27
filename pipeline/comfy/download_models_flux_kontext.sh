#!/usr/bin/env bash
# FLUX.1 Kontext (image edit / restyle) models for ComfyUI — the 3D keyframe engine.
# Public fp8 repackage (no license gate). Reuses the t5xxl_fp16 already on the pod.
#    comfyanonymous/flux_text_encoders : clip_l.safetensors        -> text_encoders/
#   Comfy-Org/FLUX.1-Kontext-dev_ComfyUI: flux1-dev-kontext_fp8_scaled.safetensors -> diffusion_models/
#   Comfy-Org/Lumina_Image_2.0_Repackaged: ae.safetensors          -> vae/
#
#   COMFY_ROOT=/workspace/ComfyUI bash pipeline/comfy/download_models_flux_kontext.sh
set -e
COMFY_ROOT="${COMFY_ROOT:-/workspace/ComfyUI}"
HF="${HF_TOKEN:-}"
DM="$COMFY_ROOT/models/diffusion_models"; TE="$COMFY_ROOT/models/text_encoders"; VAE="$COMFY_ROOT/models/vae"
mkdir -p "$DM" "$TE" "$VAE"
"$COMFY_ROOT/venv/bin/pip" install -q -U "huggingface_hub[cli]" 2>/dev/null || true
HFCLI=""
for c in "$COMFY_ROOT/venv/bin/hf" "$(command -v hf 2>/dev/null)" \
         "$COMFY_ROOT/venv/bin/huggingface-cli" "$(command -v huggingface-cli 2>/dev/null)"; do
  [ -n "$c" ] && [ -x "$c" ] && { HFCLI="$c"; break; }
done
[ -n "$HFCLI" ] || { echo "!! no hf cli"; exit 1; }
get() { # repo path destdir
  local repo="$1" path="$2" dest="$3" fn; fn="$(basename "$path")"
  [ -s "$dest/$fn" ] && { echo "   $fn present, skip"; return; }
  local stage; stage="$(mktemp -d)"
  "$HFCLI" download "$repo" "$path" --local-dir "$stage" ${HF:+--token "$HF"}
  mv -f "$stage/$path" "$dest/" 2>/dev/null || find "$stage" -name "$fn" -exec mv -f {} "$dest/" \;
  rm -rf "$stage"
}
echo "==> Flux Kontext diffusion (fp8, ~12 GB)"
get Comfy-Org/flux1-kontext-dev_ComfyUI split_files/diffusion_models/flux1-dev-kontext_fp8_scaled.safetensors "$DM"
echo "==> clip_l text encoder"
get comfyanonymous/flux_text_encoders clip_l.safetensors "$TE"
echo "==> t5xxl_fp16 text encoder (DualCLIPLoader needs it; ~9.8 GB) — not assumed present"
get comfyanonymous/flux_text_encoders t5xxl_fp16.safetensors "$TE"
echo "==> flux VAE (ae.safetensors)"
get Comfy-Org/Lumina_Image_2.0_Repackaged split_files/vae/ae.safetensors "$VAE"
echo "== diffusion_models =="; ls -la "$DM"
echo "== text_encoders =="; ls -la "$TE"
echo "== vae =="; ls -la "$VAE"
echo "DONE"
