#!/bin/bash
# 修复 env：requirements.txt 里 openai/CLIP 的 github zip 拉不到导致整批回滚。
# infer.py 不 import clip → 跳过该行，其余从 aliyun 快装。
cd /root/autodl-tmp/phase0/echomimic_v2 || exit 9
ENV_DIR=/root/autodl-tmp/envs/echomimic
export PIP_CACHE_DIR=/root/autodl-tmp/pipcache TMPDIR=/root/autodl-tmp/tmp
mkdir -p "$PIP_CACHE_DIR" "$TMPDIR"
PIP="$ENV_DIR/bin/pip"
grep -viE "github.com/openai/CLIP" requirements.txt > /root/autodl-tmp/phase0/req_noclip.txt
echo "=== install requirements (no openai-clip) from aliyun ==="
$PIP install -r /root/autodl-tmp/phase0/req_noclip.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com
echo "REQ_EXIT=$?"
$PIP install --no-deps facenet_pytorch==2.6.0 -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com; echo "FACE_EXIT=$?"
echo "=== verify ==="
"$ENV_DIR/bin/python" -c "import torch,diffusers,transformers,xformers,moviepy,omegaconf,av,einops,accelerate,cv2,skimage; print('OK torch',torch.__version__,'cuda',torch.cuda.is_available(),'diffusers',diffusers.__version__)"
echo "VERIFY_EXIT=$?"
echo "=== ENV FIX DONE ==="
