# Reproducible ComfyUI image for Hikayat Khalid animation (Path B).
# Use it two ways:
#   • GPU POD  — run it on a RunPod/Vast pod; ComfyUI serves on :8188, then drive
#     it with pipeline/comfy/animate_episode.py (COMFY_URL=https://<pod>-8188...).
#   • SERVERLESS — built on runpod-workers/worker-comfyui, so it also works as a
#     RunPod Serverless endpoint that accepts {"input": {"workflow": <api json>,
#     "images": [...]}} and returns the rendered clip (pay per render).
#
#   docker build -t hikayat-comfy -f pipeline/comfy/Dockerfile .
#
# Models are big; pre-bake them here OR mount a network volume and skip the pulls.
FROM runpod/worker-comfyui:latest-base

# --- custom nodes ---
WORKDIR /comfyui/custom_nodes
RUN for r in \
      https://github.com/city96/ComfyUI-GGUF \
      https://github.com/kijai/ComfyUI-KJNodes \
      https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite ; do \
      git clone --depth 1 "$r" && \
      ([ -f "$(basename $r)/requirements.txt" ] && pip install -r "$(basename $r)/requirements.txt" || true) ; \
    done

# --- models (LTX-2.3 GGUF + distilled LoRA + VAE + T5). Pick a quant for your VRAM.
# Comment these out and use a RunPod network volume to avoid a huge image.
WORKDIR /comfyui
RUN pip install "huggingface_hub[cli]" && \
    huggingface-cli download unsloth/LTX-2.3-GGUF LTX-2.3-Q8_0.gguf --local-dir models/unet || true && \
    huggingface-cli download Lightricks/LTX-2.3 ltx-2.3-22b-distilled-lora-384-1.1.safetensors --local-dir models/loras || true && \
    huggingface-cli download city96/t5-v1_1-xxl-encoder-gguf t5-v1_1-xxl-encoder-Q8_0.gguf --local-dir models/text_encoders || true

# bake the workflow template so serverless requests can reference it
COPY pipeline/comfy/workflow_ltx2_i2v.api.json /comfyui/hikayat_workflow.api.json

# POD mode entrypoint (serverless base already defines its own handler CMD)
EXPOSE 8188
