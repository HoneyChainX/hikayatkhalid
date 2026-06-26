#!/usr/bin/env bash
# Fix the "0 models installed" blocker: download the LTX-Video 0.9.5 image-to-video
# models into ComfyUI. Verified files (docs.comfy.org/tutorials/video/ltxv):
#   ltx-video-2b-v0.9.5.safetensors  (~9 GB)   -> models/checkpoints/
#   t5xxl_fp16.safetensors           (~9.5 GB) -> models/text_encoders/
#
#   COMFY_ROOT=/workspace/ComfyUI HF_TOKEN=... bash pipeline/comfy/download_models_ltx.sh
set -euo pipefail
COMFY_ROOT="${COMFY_ROOT:-/workspace/ComfyUI}"
HF="${HF_TOKEN:-}"
CK="$COMFY_ROOT/models/checkpoints"
TE="$COMFY_ROOT/models/text_encoders"
mkdir -p "$CK" "$TE"

"$COMFY_ROOT/venv/bin/pip" install -q -U "huggingface_hub[cli]" 2>/dev/null || \
  pip install -q -U "huggingface_hub[cli]" 2>/dev/null || true
# Prefer the new `hf` CLI — `huggingface-cli` is deprecated and now fails on some hub versions.
HFCLI=""
for c in "$COMFY_ROOT/venv/bin/hf" "$(command -v hf 2>/dev/null)" \
         "$COMFY_ROOT/venv/bin/huggingface-cli" "$(command -v huggingface-cli 2>/dev/null)"; do
  [ -n "$c" ] && [ -x "$c" ] && { HFCLI="$c"; break; }
done
[ -n "$HFCLI" ] || { echo "!! no hf / huggingface-cli found"; exit 1; }
echo "   using: $HFCLI"

echo "==> LTX-Video 2B checkpoint (~9 GB)"
if [ ! -s "$CK/ltx-video-2b-v0.9.5.safetensors" ]; then
  "$HFCLI" download Lightricks/LTX-Video ltx-video-2b-v0.9.5.safetensors \
    --local-dir "$CK" ${HF:+--token "$HF"}
else echo "   already present, skip"; fi

echo "==> T5-XXL fp16 text encoder (~9.5 GB)"
if [ ! -s "$TE/t5xxl_fp16.safetensors" ]; then
  stage="$(mktemp -d)"
  "$HFCLI" download Comfy-Org/mochi_preview_repackaged \
    split_files/text_encoders/t5xxl_fp16.safetensors --local-dir "$stage" ${HF:+--token "$HF"}
  mv -f "$stage/split_files/text_encoders/t5xxl_fp16.safetensors" "$TE/"
  rm -rf "$stage"
else echo "   already present, skip"; fi

echo "== checkpoints =="; ls -la "$CK"
echo "== text_encoders =="; ls -la "$TE"
echo "DONE — verify: python3 pipeline/comfy/animate_one.py --diagnose  (expect 1 checkpoint + 1 t5)"
