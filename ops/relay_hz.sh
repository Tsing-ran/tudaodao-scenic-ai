#!/bin/bash
# 北京→杭州贡献中继（2026-07-11 起走 SRT）：UDP+ARQ 重传，抗公网 NAT 掐长 TCP 连接。
# 同时转发手机端 livestream 与大屏竖版 livestream2；杭州 SRS srt_to_rtmp 转回 RTMP 分发（FLV/HLS/RTC 不变）。
# 回退：relay_hz.sh.rtmp_bak 为旧 RTMP 直推版，覆盖回本文件并 supervisorctl restart relay_hz 即可。
relay_one() {
  local name="$1"
  while true; do
    ffmpeg -loglevel warning -rw_timeout 8000000 \
      -i "rtmp://127.0.0.1:1935/live/${name}" \
      -c copy -f mpegts -muxdelay 0 -muxpreload 0 -pes_payload_size 384 -flush_packets 1 \
      "srt://114.55.178.51:10080?streamid=#!::r=live/${name},m=publish&latency=500000&connect_timeout=4000"
    echo "[$(date +%H:%M:%S)] ${name} relay exited, restart in 0.5s"
    sleep 0.5
  done
}

relay_one livestream &
relay_one livestream2 &
wait
