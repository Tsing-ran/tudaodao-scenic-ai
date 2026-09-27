#!/bin/bash
cd /root/autodl-tmp/LiveTalking
unset http_proxy https_proxy all_proxy ALL_PROXY
: ${DASHSCOPE_API_KEY:?set DASHSCOPE_API_KEY first}
export DITTO_ROOT=/root/autodl-tmp/ditto-talkinghead
export DITTO_DATA_ROOT=/root/autodl-tmp/ditto-talkinghead/checkpoints/ditto_trt_4090D
export DITTO_CFG_PKL=/root/autodl-tmp/ditto-talkinghead/checkpoints/ditto_cfg/v0.4_hubert_cfg_trt_online.pkl
export LD_LIBRARY_PATH=/root/autodl-tmp/cudnn8_extracted/nvidia/cudnn/lib
exec /root/miniconda3/envs/lt/bin/python app.py --transport rtmp --model ditto   --avatar_id dh_lingshan__lingshan__16x9 --tts qwentts --REF_FILE Serena   --push_url rtmp://localhost/live/livestream
