#!/bin/bash
# 拉起全栈：启动 supervisord（若未运行），它按 supervisord.conf 自启并保活 6 个服务。
# 开机后跑这一条即可。GPU 服务由此【显式】拉起——不会在开机/登录时自动抢 GPU，留给 SAM3 训练/ComfyUI。
CONF=/root/autodl-tmp/supervisord.conf
SOCK=/root/autodl-tmp/supervisor.sock
SUP=/root/miniconda3/bin/supervisord
CTL="/root/miniconda3/bin/supervisorctl -c $CONF"

if [ -S "$SOCK" ] && $CTL pid >/dev/null 2>&1; then
  echo "supervisord 已在运行 → 确保所有服务启动："
  $CTL start all
else
  echo "启动 supervisord ..."
  "$SUP" -c "$CONF"
  sleep 3
fi
echo
$CTL status
echo
echo "两路 LiveTalking 各约 85s 出流；约 90s 后跑：bash /root/autodl-tmp/preflight.sh"
