#!/bin/bash
# 修 LongCat env：装 requirements_avatar 缺失的音频依赖（librosa/soundfile/audio-separator/onnxruntime）。
# 关键：①不开 network_turbo（pip 走 tsinghua 直连，turbo 会破坏 PyPI 解析）
#       ②删 libsndfile1(系统库非pip) + tritonserverclient(渲染不需要)；onnxruntime 改 py3.10 兼容版
# flash_attn 放弃，改用已装的 xformers（渲染时把 avatar dit config 切 enable_xformers）。
cd /root/autodl-tmp/phase0/LongCat-Video || exit 9
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy
ENV_DIR=/root/autodl-tmp/envs/longcat
export PIP_CACHE_DIR=/root/autodl-tmp/pipcache TMPDIR=/root/autodl-tmp/tmp
PIP="$ENV_DIR/bin/pip"; PY="$ENV_DIR/bin/python"
TS="https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
grep -viE "^libsndfile1|^onnxruntime|^tritonserverclient" requirements_avatar.txt > /root/autodl-tmp/phase0/lc_avatar_req.txt
echo "onnxruntime==1.20.1" >> /root/autodl-tmp/phase0/lc_avatar_req.txt
echo "=== install audio deps (tsinghua, no turbo) ==="
$PIP install -r /root/autodl-tmp/phase0/lc_avatar_req.txt -i "$TS" --trusted-host mirrors.tuna.tsinghua.edu.cn
echo "REQ_AVATAR_EXIT=$?"
echo "=== verify render deps ==="
$PY -c "import torch,diffusers,transformers,av,librosa,soundfile,xformers; from audio_separator.separator import Separator; print('OK librosa',librosa.__version__,'xformers',xformers.__version__,'audio_separator ok','cuda',torch.cuda.is_available())"
echo "VERIFY2_EXIT=$?"
echo "=== LONGCAT ENVFIX DONE ==="
