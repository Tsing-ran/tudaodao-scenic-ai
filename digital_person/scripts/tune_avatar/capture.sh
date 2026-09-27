#!/bin/bash
# 抓拍一个参数点：喂固定 wav → 抓 SRS FLV → 抽帧 → 算指标。
# 用法: capture.sh <LABEL> [REC_SEC]
# 前置：SRS+LiveTalking 已起、/tmp/tune/test.wav 已生成、params.json 已写好(热加载)。
set -e
LABEL="$1"
REC=${2:-14}
BASE=/tmp/tune
LT=http://localhost:8010      # LiveTalking app 端口
FLV=http://localhost:8080/live/livestream.flv
FR="$BASE/frames_$LABEL"
rm -rf "$FR"; mkdir -p "$FR"

# 打断上一轮 → 录制 FLV → 0.8s 后喂固定音频（留 RTMP 缓冲）
curl -s -X POST "$LT/interrupt_talk" -H 'Content-Type: application/json' -d '{"sessionid":0}' >/dev/null 2>&1 || true
sleep 0.5
ffmpeg -y -loglevel error -i "$FLV" -t "$REC" -c copy "$BASE/$LABEL.flv" &
FFPID=$!
sleep 0.8
curl -s -F "sessionid=0" -F "file=@$BASE/test.wav" "$LT/humanaudio" >/dev/null
wait $FFPID

# 跳过头 2.5s(RTMP 缓冲+起播过渡)，抽 3fps 帧
ffmpeg -y -loglevel error -ss 2.5 -i "$BASE/$LABEL.flv" -vf fps=3 "$FR/f_%03d.png"
N=$(ls "$FR" | wc -l)
echo "[$LABEL] 抽帧 $N 张 → $FR"
~/miniconda3/envs/livetalking/bin/python /home/jiale/Desktop/Digital_Person/scripts/tune_avatar/metrics.py "$FR"
