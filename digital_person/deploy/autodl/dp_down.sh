#!/bin/bash
# 全停：停掉所有服务 + supervisord 本体，释放 GPU 给训练/ComfyUI。
# killasgroup 已确保子进程（ffmpeg 等）一并清理。
CONF=/root/autodl-tmp/supervisord.conf
CTL="/root/miniconda3/bin/supervisorctl -c $CONF"

$CTL shutdown && echo "已发停机，等待进程退出 ..." && sleep 4
echo
echo "== 残留 GPU 计算进程（应为空；若非空请核对 cmdline 后手动清，勿碰训练）=="
nvidia-smi --query-compute-apps=pid,used_memory,process_name --format=csv,noheader 2>/dev/null || true
