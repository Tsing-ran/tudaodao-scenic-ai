#!/bin/bash
# 加速：装 accelerate（让 int8 DiT 走 meta-device 初始化、不在内存铺完整 fp32）→ 重启渲染。
echo "=== kill current render (literal PIDs) ==="
for pid in $(ps -eo pid,cmd | grep -E "run_demo_avatar|render_full.sh|autodl_longcat_render.sh|torchrun" | grep -v grep | awk '{print $1}'); do kill -9 "$pid" 2>/dev/null && echo "killed $pid"; done
sleep 5
ENV_DIR=/root/autodl-tmp/envs/longcat
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy
export PIP_CACHE_DIR=/root/autodl-tmp/pipcache TMPDIR=/root/autodl-tmp/tmp
echo "=== install accelerate ==="
"$ENV_DIR/bin/pip" install -q accelerate -i https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple --trusted-host mirrors.tuna.tsinghua.edu.cn 2>&1 | tail -2
"$ENV_DIR/bin/python" -c "import accelerate; print('accelerate OK', accelerate.__version__)"
echo "=== ACCEL READY ==="
