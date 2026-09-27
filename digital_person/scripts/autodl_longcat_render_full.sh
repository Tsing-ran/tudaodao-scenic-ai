#!/bin/bash
# 原子：停两路 Ditto 腾显存 → 渲 LongCat(int8+distill,xformers) → 拉回两路 Ditto。
# 杀进程用字面 PID（grep -v grep 滤掉 grep 自身，wrapper cmdline 不含 app.py 故不自杀）。
echo "=== pause LiveTalking (free GPU) ==="
LTPIDS=$(ps -eo pid,cmd | grep -F "app.py --transport rtmp --model ditto" | grep -v grep | awk '{print $1}')
echo "LiveTalking PIDs: $LTPIDS"
for p in $LTPIDS; do kill $p 2>/dev/null && echo "killed $p"; done
sleep 6
echo "GPU after pause:"; nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader

echo "=== render LongCat ==="
bash /root/autodl-tmp/phase0/autodl_longcat_render.sh
RC=$?
echo "render wrapper rc=$RC"

echo "=== restore LiveTalking (两路) ==="
cd /root/autodl-tmp
setsid bash lt_run.sh </dev/null >/root/autodl-tmp/lt.log 2>&1 &
setsid bash lt_run_portrait.sh </dev/null >/root/autodl-tmp/lt_portrait.log 2>&1 &
echo "=== LiveTalking restart issued (各 ~85s 出流) ==="
echo "=== RENDER_FULL DONE ==="
