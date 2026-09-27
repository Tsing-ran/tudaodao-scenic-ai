#!/bin/bash
# 切换直播数字人形象（两路 16:9+9:16 一起换）。用法：switch_avatar.sh <avatar_id> [scenic=lingshan]
# avatar_id 见形象库（F1_modern/M1_modern…）；底图须已在 data/ditto_avatars/<id>__<scenic>__{16x9,9x16}.png
AID=${1:?用法: switch_avatar.sh <avatar_id> [scenic]}
SCENIC=${2:-lingshan}
D=/root/autodl-tmp/LiveTalking/data/ditto_avatars
A16="${AID}__${SCENIC}__16x9"; A9="${AID}__${SCENIC}__9x16"
[ -f "$D/$A16.png" ] || { echo "❌ 缺 $A16.png"; exit 1; }
[ -f "$D/$A9.png" ]  || { echo "❌ 缺 $A9.png"; exit 1; }
# 男声 Ethan / 女声 Serena（按 id 首字母）
case "$AID" in M*) VOICE=Ethan;; *) VOICE=Serena;; esac
# 杀两路 LiveTalking（字面 PID，避 pgrep 自杀）
for P in $(ps -eo pid,cmd | grep -F "app.py --transport rtmp" | grep -v grep | grep "envs/lt/bin/python" | awk "{print \$1}"); do kill $P 2>/dev/null; done
sleep 4
export DASHSCOPE_API_KEY=$(grep DASHSCOPE_API_KEY /root/autodl-tmp/Digital_Person/.env | cut -d= -f2)
export DITTO_ROOT=/root/autodl-tmp/ditto-talkinghead
export DITTO_DATA_ROOT=$DITTO_ROOT/checkpoints/ditto_trt_4090D
export DITTO_CFG_PKL=$DITTO_ROOT/checkpoints/ditto_cfg/v0.4_hubert_cfg_trt_online.pkl
export LD_LIBRARY_PATH=/root/autodl-tmp/cudnn8_extracted/nvidia/cudnn/lib
cd /root/autodl-tmp/LiveTalking
setsid /root/miniconda3/envs/lt/bin/python app.py --transport rtmp --model ditto --avatar_id "$A16" --tts qwentts --REF_FILE $VOICE --push_url rtmp://localhost/live/livestream </dev/null >/root/autodl-tmp/lt.log 2>&1 &
setsid /root/miniconda3/envs/lt/bin/python app.py --transport rtmp --model ditto --avatar_id "$A9" --listenport 8011 --tts qwentts --REF_FILE $VOICE --push_url rtmp://localhost/live/livestream2 </dev/null >/root/autodl-tmp/lt_portrait.log 2>&1 &
echo "✅ 已切到 $AID @ $SCENIC（音色 $VOICE），两路重启中 ~85s 出流"
