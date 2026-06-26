#!/usr/bin/env bash
# Persistent ComfyUI launcher. RunPod's ~/start_comfy.sh lives in ephemeral /root and
# disappears on every pod restart; this one is in the repo on the /workspace volume.
#   COMFY_ROOT=/workspace/ComfyUI bash pipeline/comfy/start_comfy.sh
set -euo pipefail
COMFY_ROOT="${COMFY_ROOT:-/workspace/ComfyUI}"
cd "$COMFY_ROOT"
nohup venv/bin/python3 main.py --listen 0.0.0.0 --port 8188 > /workspace/comfy.log 2>&1 &
echo "ComfyUI starting (pid $!) — waiting for readiness…"
for _ in $(seq 1 120); do
  if curl -sf http://127.0.0.1:8188/object_info >/dev/null 2>&1; then echo "READY on :8188"; exit 0; fi
  sleep 3
done
echo "!! ComfyUI did not become ready in time — check /workspace/comfy.log"; exit 1
