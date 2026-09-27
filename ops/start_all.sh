#!/bin/bash
# 一键拉起全栈（实例重置后进程全失 → 重跑此脚本）。SRS → LiveTalking×2(16:9+9:16) → RAG → 桥接
set +e
echo "[1/5] SRS"; cd /root/autodl-tmp/srs/trunk
pgrep -f "objs/srs -c" >/dev/null || setsid ./objs/srs -c conf/srs_dp.conf </dev/null >/root/autodl-tmp/srs.log 2>&1 &
sleep 2
echo "[2/5] LiveTalking 16:9(手机端,8010)"; pgrep -f "livestream2" >/dev/null; HAS_P=$?
pgrep -f "app.py --transport rtmp" | grep -v "$(pgrep -f livestream2)" >/dev/null 2>&1
grep -q . <<< "$(pgrep -f "push_url rtmp://localhost/live/livestream$")" 2>/dev/null || setsid bash /root/autodl-tmp/lt_run.sh </dev/null >/root/autodl-tmp/lt.log 2>&1 &
echo "[3/5] LiveTalking 9:16(大屏,8011)"; [ $HAS_P -eq 0 ] || setsid bash /root/autodl-tmp/lt_run_portrait.sh </dev/null >/root/autodl-tmp/lt_portrait.log 2>&1 &
echo "[4/5] RAG(8000)"; cd /root/autodl-tmp/Digital_Person
pgrep -f "uvicorn backend.main" >/dev/null || DEPLOY_MODE=cloud setsid /root/miniconda3/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 </dev/null >/root/autodl-tmp/rag.log 2>&1 &
sleep 1
echo "[5/5] 桥接(6006, 含竖版 base)"; pgrep -f "uvicorn bridge.server" >/dev/null || RAG_BASE=http://127.0.0.1:8000 LIVETALKING_BASE=http://127.0.0.1:8010 LIVETALKING_BASE_2=http://127.0.0.1:8011 setsid /root/miniconda3/bin/python -m uvicorn bridge.server:app --host 0.0.0.0 --port 6006 </dev/null >/root/autodl-tmp/bridge.log 2>&1 &
echo "全部已发起。两个 LiveTalking 各需 ~85s 出流。"
echo "[6/6] 中继→杭州网关(114.55.178.51)，掉线自动重连"; pgrep -f relay_hz.sh >/dev/null || setsid bash /root/autodl-tmp/relay_hz.sh </dev/null >>/root/autodl-tmp/relay_hz.log 2>&1 &
