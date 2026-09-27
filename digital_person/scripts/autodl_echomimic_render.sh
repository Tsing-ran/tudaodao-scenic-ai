#!/bin/bash
# 阶段0：渲染一条 EchoMimicV2 半身手势样片（标准 infer.py）。
# EchoMimicV2 实测可在 V100 16G 跑 → 18.5G 空闲足够，无需停 LiveTalking（带 expandable_segments 防峰值）。
cd /root/autodl-tmp/phase0/echomimic_v2 || exit 9
export FFMPEG_PATH=/usr/bin
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
mkdir -p assets/halfbody_demo/audio/chinese
cp -f /root/autodl-tmp/phase0/phase0_short.wav assets/halfbody_demo/audio/chinese/phase0_short.wav
PY=/root/autodl-tmp/envs/echomimic/bin/python
echo "=== GPU before ==="; nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
echo "=== RENDER START ==="; date
$PY infer.py --config configs/prompts/infer.yaml \
  -W 768 -H 768 -L 144 --steps 30 --cfg 2.5 --fps 24 \
  --refimg_name natural_bk_openhand/0035.png \
  --audio_name chinese/phase0_short.wav \
  --pose_name 01
echo "=== RENDER EXIT=$? ==="; date
echo "=== output mp4 ==="
find outputs -name "*.mp4" -printf "%T+ %s %p\n" 2>/dev/null | sort | tail -5
