#!/usr/bin/env python3
"""
Step 1 of the RTX character-LoRA path: prepare a training DATASET for one character
from its locked reference art (assets/characters/<char>_ref.png).

A good character LoRA needs ~20-30 images of the SAME character in varied angles,
expressions and crops, each with a caption that starts with a unique trigger token.
This script writes the dataset scaffold — the curated variation prompts + per-image
caption .txt files (ai-toolkit/kohya format) + a manifest — so you only have to render
the images (identity-preserving) and train.

    python3 pipeline/comfy/lora_dataset.py --char khalid
    # -> build/lora/khalid/{prompts.jsonl, 01.txt ... 24.txt, README}

RENDER the 24 images (keeping identity from the reference) with **Flux Kontext** in
ComfyUI on the GPU box (load assets/characters/<char>_ref.png as the Kontext input,
use each prompt, save as build/lora/<char>/NN.png). Then: train_character_lora.sh.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# unique, rare trigger token per character (avoid real words so the LoRA binds cleanly)
TRIGGER = {"khalid": "kh4lidboy", "noor": "n00rgirl", "teta": "t3tagran"}
BASECAP = {
    "khalid": "a young Arab Muslim boy in a black thobe with gold embroidery and an olive-and-gold kufi cap",
    "noor": "a little Arab Muslim girl in a soft-blue headscarf and light-blue dress",
    "teta": "an elderly Arab Muslim grandmother with round glasses, a cream hijab and olive-and-maroon clothes",
}
# 24 varied views — angles × expressions × crops. Identity stays locked (Kontext from ref);
# only pose/expression/crop change, which is exactly what a character LoRA should learn.
VARIATIONS = [
    "front view, neutral friendly expression, full body, plain background",
    "front view, warm smile, full body, plain background",
    "three-quarter left view, neutral expression, full body, plain background",
    "three-quarter right view, gentle smile, full body, plain background",
    "side profile view, calm expression, full body, plain background",
    "front view, talking with mouth slightly open, half body, plain background",
    "front view, surprised wide-eyed expression, half body, plain background",
    "front view, thoughtful expression looking up, half body, plain background",
    "three-quarter view, laughing happily, half body, plain background",
    "front view, gentle caring expression, close-up portrait, plain background",
    "three-quarter left, neutral, close-up portrait, plain background",
    "three-quarter right, smiling, close-up portrait, plain background",
    "front view, waving one hand, full body, plain background",
    "front view, both hands clasped, full body, plain background",
    "three-quarter view, arms relaxed at sides, full body, plain background",
    "front view, sitting cross-legged, full body, plain background",
    "front view, pointing forward, half body, plain background",
    "side view, walking pose, full body, plain background",
    "front view, slightly sad gentle expression, half body, plain background",
    "front view, curious expression, close-up portrait, plain background",
    "three-quarter view, warm grandmotherly smile, half body, plain background",
    "front view, eyes closed peaceful expression, close-up, plain background",
    "front view, cheerful big smile, full body, plain background",
    "three-quarter view, neutral, full body, soft studio background",
]
STYLE = ("flat 2D vector cartoon children's storybook illustration, clean bold outlines, "
         "smooth flat colors, soft warm palette, consistent character design")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--char", required=True, choices=list(TRIGGER))
    args = ap.parse_args()
    char = args.char
    trig, base = TRIGGER[char], BASECAP[char]
    ref = ROOT / "assets" / "characters" / f"{char}_ref.png"
    out = ROOT / "build" / "lora" / char
    out.mkdir(parents=True, exist_ok=True)

    manifest = []
    for i, v in enumerate(VARIATIONS, 1):
        # render prompt (identity from the ref image + this variation)
        render_prompt = f"{STYLE}. {base}. {v}. no text, no watermark."
        # training caption (what the LoRA reads): trigger + light description
        caption = f"{trig}, {base}, {v.split(',')[0]}"
        (out / f"{i:02d}.txt").write_text(caption, encoding="utf-8")
        manifest.append({"index": i, "image": f"{i:02d}.png", "caption": caption,
                         "render_prompt": render_prompt})

    (out / "prompts.jsonl").write_text(
        "\n".join(json.dumps(m, ensure_ascii=False) for m in manifest) + "\n", encoding="utf-8")
    (out / "README.md").write_text(
        f"# LoRA dataset — {char}  (trigger: `{trig}`)\n\n"
        f"Reference: `{ref.relative_to(ROOT)}`\n\n"
        f"1. Render each prompt in `prompts.jsonl` with **Flux Kontext** in ComfyUI, using the "
        f"reference above as the Kontext image so identity stays locked. Save as `NN.png` here "
        f"(matching the `NN.txt` captions).\n"
        f"2. Aim for 20-24 clean images; delete any off-model ones (quality > quantity).\n"
        f"3. Train: `CHAR={char} DATASET_DIR=build/lora/{char} bash pipeline/comfy/train_character_lora.sh`\n\n"
        f"The captions already start with the trigger `{trig}` — use that token in your keyframe "
        f"prompts to summon this exact character.\n", encoding="utf-8")

    print(f"✅ dataset scaffold for {char} -> {out.relative_to(ROOT)}")
    print(f"   trigger token: {trig}")
    print(f"   {len(VARIATIONS)} caption files + prompts.jsonl written.")
    if not ref.exists():
        print(f"   ⚠ reference {ref} not found — add it before rendering.")
    print(f"   next: render NN.png with Flux Kontext (identity from the ref), then train_character_lora.sh")


if __name__ == "__main__":
    main()
