#!/bin/bash
# Rebuild Ditto TRT engines natively for RTX 4090 D (Ada) from official ONNX.
# Output goes to a NEW dir; the live Ampere_Plus engines are untouched (safe rollback).
trap 'echo BUILD_FAIL' ERR
set -e
cd /root/autodl-tmp/ditto-talkinghead
export HF_ENDPOINT=https://hf-mirror.com
echo "[1/2] downloading ditto_onnx (2.5GB) via hf-mirror..."
/root/miniconda3/envs/lt/bin/python - <<'EOF'
from huggingface_hub import snapshot_download
snapshot_download('digital-avatar/ditto-talkinghead',
                  allow_patterns=['ditto_onnx/*'],
                  local_dir='./checkpoints')
print('download ok')
EOF
echo "[2/2] converting ONNX -> TRT (native Ada build)..."
export PATH=/root/miniconda3/envs/lt/bin:$PATH
export LD_LIBRARY_PATH=/root/autodl-tmp/cudnn8_extracted/nvidia/cudnn/lib
/root/miniconda3/envs/lt/bin/python scripts/cvt_onnx_to_trt.py \
  --onnx_dir ./checkpoints/ditto_onnx \
  --trt_dir  ./checkpoints/ditto_trt_4090D
echo BUILD_DONE
