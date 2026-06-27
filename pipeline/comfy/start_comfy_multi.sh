#!/usr/bin/env bash
# Launch one ComfyUI per GPU for parallel rendering. Uses this pod's http-exposed
# ports (default "8188 19123"; override with COMFY_PORTS="8188 19123 ...").
# GPU i -> PORTS[i], reachable at https://<podid>-<port>.proxy.runpod.net
set -uo pipefail
COMFY_ROOT="${COMFY_ROOT:-/workspace/comfy-s2v}"
read -r -a PORTS <<< "${COMFY_PORTS:-8188 19123}"
cd "$COMFY_ROOT"
N=$(nvidia-smi -L 2>/dev/null | wc -l); [ "$N" -ge 1 ] || N=1
echo "GPUs detected: $N   ports: ${PORTS[*]}"
for i in $(seq 0 $((N-1))); do
  p="${PORTS[$i]:-$((8188+i))}"
  if curl -sf "http://127.0.0.1:$p/object_info" >/dev/null 2>&1; then
    echo "  port $p already serving ComfyUI — leaving GPU$i as-is"; continue
  fi
  CUDA_VISIBLE_DEVICES="$i" nohup venv/bin/python3 main.py --listen 0.0.0.0 --port "$p" \
    > "/workspace/comfy_gpu$i.log" 2>&1 &
  echo "  GPU$i -> :$p (pid $!)  log=/workspace/comfy_gpu$i.log"
done
echo "waiting for readiness..."
for i in $(seq 0 $((N-1))); do
  p="${PORTS[$i]:-$((8188+i))}"
  for _ in $(seq 1 150); do
    curl -sf "http://127.0.0.1:$p/object_info" >/dev/null 2>&1 && { echo "  READY :$p"; break; }
    sleep 3
  done
done
echo "DONE — GPUs serving on ${PORTS[*]}"
