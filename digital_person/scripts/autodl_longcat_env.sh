#!/bin/bash
# LongCat env：py3.10 + torch2.6/cu124 + flash_attn(预编译wheel,失败回退xformers) + requirements。
set +e
cd /root/autodl-tmp/phase0/LongCat-Video || exit 9
CONDA=/root/miniconda3/bin/conda
ENV_DIR=/root/autodl-tmp/envs/longcat
export PIP_CACHE_DIR=/root/autodl-tmp/pipcache TMPDIR=/root/autodl-tmp/tmp
mkdir -p "$PIP_CACHE_DIR" "$TMPDIR"
[ -x "$ENV_DIR/bin/python" ] || $CONDA create -y -p "$ENV_DIR" python=3.10 2>&1 | tail -2
PIP="$ENV_DIR/bin/pip"; PY="$ENV_DIR/bin/python"
$PIP install -q -U pip ninja packaging psutil

echo "=== torch 2.6.0 cu124 (SJTU 镜像) ==="
$PIP install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://mirror.sjtu.edu.cn/pytorch-wheels/cu124 2>&1 | tail -3
$PY -c "import torch;print('torch',torch.__version__)" 2>/dev/null || {
  echo "SJTU 失败，回退官方源"; $PIP install torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124 2>&1 | tail -3; }

echo "=== flash_attn 预编译 wheel ==="
source /etc/network_turbo 2>/dev/null
FA=https://github.com/Dao-AILab/flash-attention/releases/download/v2.7.4.post1/flash_attn-2.7.4.post1+cu12torch2.6cxx11abiFALSE-cp310-cp310-linux_x86_64.whl
$PIP install "$FA" 2>&1 | tail -3
$PY -c "import flash_attn;print('flash_attn',flash_attn.__version__)" 2>/dev/null && echo "FLASH_OK" || {
  echo "FLASH_WHEEL_FAIL -> 装 xformers 兜底（渲染时把 dit config 的 attention 改 xformers）"
  $PIP install xformers==0.0.29.post3 --index-url https://download.pytorch.org/whl/cu124 2>&1 | tail -2; }

echo "=== requirements (剔 flash-attn 行，tsinghua) ==="
grep -viE "^flash.attn|^flash_attn" requirements.txt > /root/autodl-tmp/phase0/lc_req.txt
$PIP install -r /root/autodl-tmp/phase0/lc_req.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple --trusted-host mirrors.tuna.tsinghua.edu.cn 2>&1 | tail -3
$PIP install -r requirements_avatar.txt -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple --trusted-host mirrors.tuna.tsinghua.edu.cn 2>&1 | tail -3

echo "=== verify ==="
$PY -c "import torch,diffusers,transformers,av,librosa; import importlib; fa=importlib.util.find_spec('flash_attn') is not None; xf=importlib.util.find_spec('xformers') is not None; print('OK torch',torch.__version__,'cuda',torch.cuda.is_available(),'diffusers',diffusers.__version__,'flash_attn',fa,'xformers',xf)"
echo "VERIFY_EXIT=$?"
echo "=== LONGCAT ENV DONE ==="
