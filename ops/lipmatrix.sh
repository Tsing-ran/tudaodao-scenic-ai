#!/bin/bash
# 矩阵测试：多个形象同台词，录流→嘴部网格图。用法: lipmatrix.sh <avatar_id> <tag> [scenic=lingshan]
AID=${1:?avatar_id}
TAG=${2:?tag}
SCENIC=${3:-lingshan}
set -e
curl -s -X POST http://localhost:6006/live/avatar -H 'Content-Type: application/json' \
  -d "{\"avatar_id\":\"$AID\",\"scenic_id\":\"$SCENIC\",\"sessionid\":\"0\",\"screen\":\"portrait\"}" | head -c 200
echo
sleep 4
ffmpeg -y -loglevel error -i rtmp://localhost/live/livestream2 -t 14 /root/autodl-tmp/lm_$TAG.mp4 &
REC=$!
sleep 3
curl -s -X POST http://localhost:6006/live/say -H 'Content-Type: application/json' \
  -d '{"sessionid":"0","text":"WELCOME! HAHAHA! OPEN WIDE! HELLO EVERYBODY!","scenic_id":"lingshan","screen":"portrait","interrupt":true}'
echo
wait $REC
# 嘴部区域按人脸大致位置裁（各底图构图相近：面部上 1/3 居中）
ffmpeg -y -loglevel error -i /root/autodl-tmp/lm_$TAG.mp4 -vf "fps=8,crop=260:160:230:380,tile=8x8" -frames:v 1 /root/autodl-tmp/mtile_$TAG.png
echo TILE-DONE $TAG
