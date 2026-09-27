#!/bin/bash
# 演示前一键体检：关键项全绿才开录。用法：bash preflight.sh [--audio]
#   不带参数：进程守护 + 端口 + RAG/桥接健康 + SRS 双流 + GPU + 公网网关（快，~10s）
#   --audio ：额外驱动 /live/say 抓 6s 流测电平 dB，确认数字人真出声（~15s，占 GPU）
CONF=/root/autodl-tmp/supervisord.conf
CTL="/root/miniconda3/bin/supervisorctl -c $CONF"
PY=/root/miniconda3/bin/python
HZ=https://114.55.178.51:8443
PASS=0; FAIL=0; WARN=0
ok(){   echo "  ✓ $1"; PASS=$((PASS+1)); }
bad(){  echo "  ✗ $1"; FAIL=$((FAIL+1)); }
warn(){ echo "  ! $1"; WARN=$((WARN+1)); }

echo "==== 1. supervisor 进程守护 ===="
if $CTL status >/tmp/_sup 2>&1; then
  sed 's/^/    /' /tmp/_sup
  RUN=$(grep -c RUNNING /tmp/_sup); TOT=$(wc -l </tmp/_sup)
  [ "$RUN" -eq "$TOT" ] && [ "$TOT" -ge 6 ] && ok "$RUN/$TOT 服务 RUNNING" || bad "$RUN/$TOT RUNNING（非全绿）"
else
  bad "supervisord 未运行（先跑 dp_up.sh）"; echo; echo "体检中止"; exit 1
fi

echo "==== 2. 端口监听（bash /dev/tcp 直连探测，免 ss 依赖）===="
for p in 8000 6006 8010 8011 1935 1985 8080; do
  if (exec 3<>/dev/tcp/127.0.0.1/$p) 2>/dev/null; then exec 3>&- 2>/dev/null; ok "端口 $p"; else bad "端口 $p 未监听"; fi
done

echo "==== 3. RAG / 桥接 健康 ===="
curl -sf --max-time 5 http://127.0.0.1:8000/health >/dev/null && ok "RAG /health" || bad "RAG /health 不通"
H=$(curl -sf --max-time 5 http://127.0.0.1:6006/live/health 2>/dev/null)
echo "$H" | grep -q 'rag' && ok "桥接 /live/health 通" || bad "桥接 /live/health 不通"

echo "==== 4. SRS 直播双流（出流约需 85s）===="
S=$(curl -sf --max-time 5 http://127.0.0.1:1985/api/v1/streams/ 2>/dev/null)
ACT=$(echo "$S" | $PY -c "import sys,json; d=json.load(sys.stdin); print(sum(1 for s in d.get('streams',[]) if s.get('publish',{}).get('active')))" 2>/dev/null)
[ "${ACT:-0}" -ge 2 ] && ok "$ACT 路推流 active（main+portrait）" \
  || warn "${ACT:-0} 路 active（<2；若刚 dp_up 未满 85s 属正常，稍后复检）"

echo "==== 5. GPU 占用 ===="
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader 2>/dev/null | sed 's/^/    /'
NP=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | grep -c .)
[ "${NP:-0}" -ge 1 ] && ok "$NP 个 GPU 计算进程（LiveTalking）" || warn "无 GPU 进程（LiveTalking 未起或已退）"

echo "==== 6. 公网网关可达（杭州）===="
curl -skf --max-time 8 $HZ/rag/health >/dev/null && ok "$HZ/rag/health 公网可达" \
  || warn "杭州网关暂不可达（查中继 relay_hz / 证书）"

if [ "$1" = "--audio" ]; then
  echo "==== 7. 数字人出声（驱动 /live/say 测电平 dB）===="
  curl -sf --max-time 10 -X POST http://127.0.0.1:6006/live/say -H 'Content-Type: application/json' \
       -d '{"text":"灵山胜境欢迎您，我是您的AI导览数字人。","sessionid":"0","screen":"main"}' >/dev/null \
       && ok "/live/say 已下发" || bad "/live/say 调用失败"
  sleep 3   # 等语音经 TTS→Ditto→RTMP 抵达 FLV
  # 注意：volumedetect 的 mean/max_volume 行是 info 级日志，必须 -loglevel info（error 会吞掉）；
  #       -t 放在 -i 前作输入侧时长，避免对 live chunked FLV 用输出侧 -t 而停滞。
  timeout 20 ffmpeg -hide_banner -loglevel info -t 8 -i http://127.0.0.1:8080/live/livestream.flv \
       -af volumedetect -f null - 2>/tmp/_vol
  MEAN=$(grep mean_volume /tmp/_vol | grep -oE '\-?[0-9.]+ dB' | head -1)
  MAX=$(grep max_volume  /tmp/_vol | grep -oE '\-?[0-9.]+ dB' | head -1)
  if [ -n "$MEAN" ]; then
    echo "    mean=$MEAN  max=$MAX"
    MV=$(echo "$MEAN" | grep -oE '\-?[0-9.]+')
    awk "BEGIN{exit !($MV > -60)}" && ok "数字人有清晰语音（mean $MEAN）" || bad "疑似静音（mean $MEAN）—查 QwenTTS 连接"
  else
    bad "未取到音频电平（流未就绪？稍后重试）"
  fi
fi

echo
echo "==== 体检结果：通过 $PASS · 警告 $WARN · 失败 $FAIL ===="
[ "$FAIL" -eq 0 ] && echo "✅ 关键项全绿，可开录。" || { echo "❌ 有失败项，先修再演。"; exit 1; }
