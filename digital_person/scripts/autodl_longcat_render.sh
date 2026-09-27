#!/bin/bash
# LongCat-Video-Avatar-1.5 单图+音频渲染（int8+distill，单卡）。480p 省显存先验质量。
cd /root/autodl-tmp/phase0/LongCat-Video || exit 9
ENV_DIR=/root/autodl-tmp/envs/longcat
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PY="$ENV_DIR/bin/python"
echo "=== GPU before ==="; nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
echo "=== RENDER START ==="; date
"$ENV_DIR/bin/torchrun" --nproc_per_node=1 run_demo_avatar_single_audio_to_video.py \
  --context_parallel_size=1 \
  --checkpoint_dir=./weights/LongCat-Video-Avatar-1.5 \
  --stage_1=ai2v \
  --input_json=assets/avatar/single_ours/lingshan.json \
  --use_distill --model_type avatar-v1.5 --use_int8 \
  --resolution 480p --output_dir outputs_ours
echo "=== RENDER EXIT=$? ==="; date
find outputs_ours outputs -name "*.mp4" -newermt "-60 min" -printf "%T+ %s %p\n" 2>/dev/null | sort | tail -5
echo "=== LONGCAT RENDER DONE ==="
