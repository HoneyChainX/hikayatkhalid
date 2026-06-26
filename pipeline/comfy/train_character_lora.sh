#!/usr/bin/env bash
# Step 2 of the RTX character-LoRA path: train a locked-identity Flux LoRA for one
# character from its dataset (build/lora/<char>/NN.png + NN.txt).
#
#   CHAR=khalid DATASET_DIR=build/lora/khalid bash pipeline/comfy/train_character_lora.sh
#
# Target: a rented/owned NVIDIA RTX with ~24 GB VRAM (RTX 4090 / A5000 / A100).
# ~30-60 min on a 4090. Output LoRA is copied into ComfyUI/models/loras for keyframing.
set -euo pipefail

CHAR="${CHAR:?set CHAR=khalid|noor|teta}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DATASET_DIR="${DATASET_DIR:-$ROOT/build/lora/$CHAR}"
STEPS="${STEPS:-2000}"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/build/lora/$CHAR/out}"
COMFY_ROOT="${COMFY_ROOT:-$HOME/ComfyUI}"
TOOLKIT="${TOOLKIT_DIR:-$HOME/ai-toolkit}"

case "$CHAR" in
  khalid) TRIGGER="kh4lidboy" ;;
  noor)   TRIGGER="n00rgirl" ;;
  teta)   TRIGGER="t3tagran" ;;
  *) echo "unknown CHAR=$CHAR"; exit 1 ;;
esac

# sanity: dataset must have matched NN.png + NN.txt pairs
imgs=$(find "$DATASET_DIR" -maxdepth 1 -name '*.png' | wc -l)
caps=$(find "$DATASET_DIR" -maxdepth 1 -name '*.txt' | wc -l)
echo "==> $CHAR  dataset=$DATASET_DIR  images=$imgs  captions=$caps  trigger=$TRIGGER  steps=$STEPS"
[ "$imgs" -ge 8 ] || { echo "!! need >=8 rendered NN.png (have $imgs). Render them first "         "(lora_dataset.py prepared the prompts/captions)."; exit 1; }

echo "==> ai-toolkit"
[ -d "$TOOLKIT" ] || git clone https://github.com/ostris/ai-toolkit "$TOOLKIT"
cd "$TOOLKIT"
git submodule update --init --recursive || true
python3 -m venv venv && source venv/bin/activate
pip install --upgrade pip >/dev/null
pip install torch --index-url https://download.pytorch.org/whl/cu124 || pip install torch
pip install -r requirements.txt

echo "==> fill config from template"
mkdir -p "$OUTPUT_DIR"
CFG="$OUTPUT_DIR/${CHAR}_flux_lora.yaml"
sed -e "s#__CHAR__#$CHAR#g" -e "s#__TRIGGER__#$TRIGGER#g" \
    -e "s#__DATASET_DIR__#$DATASET_DIR#g" -e "s#__OUTPUT_DIR__#$OUTPUT_DIR#g" \
    -e "s#__STEPS__#$STEPS#g" \
    "$ROOT/pipeline/comfy/ai_toolkit_flux_lora.yaml" > "$CFG"
echo "   wrote $CFG"

# FLUX.1-dev is gated — accept the license on HF and export HF_TOKEN before running.
[ -n "${HF_TOKEN:-}" ] && huggingface-cli login --token "$HF_TOKEN" || \
  echo "   (set HF_TOKEN if FLUX.1-dev download is gated)"

echo "==> train"
python run.py "$CFG"

echo "==> install LoRA into ComfyUI"
mkdir -p "$COMFY_ROOT/models/loras"
LORA=$(find "$OUTPUT_DIR" -name '*.safetensors' | sort | tail -1)
if [ -n "$LORA" ]; then
  cp "$LORA" "$COMFY_ROOT/models/loras/${CHAR}_lora.safetensors"
  echo "✅ $CHAR LoRA -> $COMFY_ROOT/models/loras/${CHAR}_lora.safetensors  (trigger: $TRIGGER)"
  echo "   Use '$TRIGGER' in keyframe prompts to summon this exact character, then animate."
else
  echo "!! no .safetensors produced — check the training log above."; exit 1
fi
