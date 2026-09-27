#!/bin/bash
# 阶段0：创建 echomimic conda 环境并装依赖（CPU/网络，无 GPU）。
set -e
cd /root/autodl-tmp/phase0/echomimic_v2
CONDA=/root/miniconda3/bin/conda
ENV_DIR=/root/autodl-tmp/envs/echomimic
# 环境装到数据盘（/root/autodl-tmp），缓存也重定向，避免撑爆系统盘 /
export PIP_CACHE_DIR=/root/autodl-tmp/pipcache
export TMPDIR=/root/autodl-tmp/tmp
mkdir -p "$PIP_CACHE_DIR" "$TMPDIR"
if [ ! -x "$ENV_DIR/bin/python" ]; then
  $CONDA create -y -p "$ENV_DIR" python=3.10 2>&1 | tail -2
fi
PIP="$ENV_DIR/bin/pip"
$PIP install -q -U pip
echo "=== torch 2.5.1 cu124 ==="
$PIP install -q torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 xformers==0.0.28.post3 --index-url https://download.pytorch.org/whl/cu124 2>&1 | tail -2
echo "=== torchao nightly ==="
$PIP install -q torchao --index-url https://download.pytorch.org/whl/nightly/cu124 2>&1 | tail -1 || echo "torchao skip"
echo "=== requirements ==="
$PIP install -q -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ 2>&1 | tail -3
$PIP install -q --no-deps facenet_pytorch==2.6.0 -i https://mirrors.aliyun.com/pypi/simple/ 2>&1 | tail -1 || echo "facenet skip"
echo "=== verify ==="
"$ENV_DIR/bin/python" -c "import torch,diffusers,transformers,xformers; print('torch',torch.__version__,'cuda',torch.cuda.is_available())"
echo "=== ENV ALL DONE ==="
