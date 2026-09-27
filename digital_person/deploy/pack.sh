#!/bin/bash
# 在本地执行，打包需要上传的文件
# 用法：bash deploy/pack.sh <服务器IP>
# 例如：bash deploy/pack.sh 47.123.45.67

set -e
SERVER_IP=$1
if [ -z "$SERVER_IP" ]; then
    echo "用法: bash deploy/pack.sh <服务器公网IP>"
    exit 1
fi

echo "=== 打包项目文件 ==="
cd /home/jiale/Desktop/Digital_Person

tar czf /tmp/digital-person.tar.gz \
    backend/ \
    scripts/ \
    示范景区公开资料包/ \
    requirements.cloud.txt \
    requirements.txt \
    .env.example \
    Dockerfile \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude=".venv"

echo "打包完成：$(du -sh /tmp/digital-person.tar.gz | cut -f1)"

echo "=== 上传到服务器 $SERVER_IP ==="
scp /tmp/digital-person.tar.gz root@$SERVER_IP:/root/
scp deploy/setup_server.sh root@$SERVER_IP:/root/

echo "=== 上传完成 ==="
echo "现在 SSH 到服务器执行："
echo "  ssh root@$SERVER_IP"
echo "  bash /root/setup_server.sh"
