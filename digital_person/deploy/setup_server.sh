#!/bin/bash
# 在 ECS 服务器上执行，完成全部部署（非交互式，Ubuntu 24.04 / Python 3.12）
# 用法：bash /root/setup_server.sh
set -e

echo "======================================"
echo "  景区导览AI数字人 - 服务器部署脚本"
echo "======================================"

# ── 1. 系统依赖 ───────────────────────────────────────────────────
echo "[1/6] 安装系统依赖..."
apt-get update -q
apt-get install -y -q python3-venv python3-pip curl git

# ── 2. 安装 uv ────────────────────────────────────────────────────
echo "[2/6] 安装 uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# ── 3. 解压代码 ───────────────────────────────────────────────────
echo "[3/6] 解压项目..."
mkdir -p /root/digital-person
cd /root
tar xzf /root/digital-person.tar.gz -C /root/digital-person --strip-components=0
cd /root/digital-person

# ── 4. 创建虚拟环境 + 安装依赖 ───────────────────────────────────
echo "[4/6] 安装 Python 依赖（云端轻量版，无 torch）..."
python3 -m venv .venv
.venv/bin/pip install uv -q
.venv/bin/python -m uv pip install -r requirements.cloud.txt \
    --index-url https://mirrors.aliyun.com/pypi/simple/ \
    --trusted-host mirrors.aliyun.com

# ── 5. 写入环境变量（由 pack_and_deploy.sh 提前写好） ─────────────
echo "[5/6] 验证环境变量..."
if [ ! -f .env ]; then
    echo "ERROR: .env 文件不存在，请先上传"
    exit 1
fi
grep -q "DEPLOY_MODE=cloud" .env || sed -i 's/DEPLOY_MODE=local/DEPLOY_MODE=cloud/' .env
echo "  DEPLOY_MODE=$(grep DEPLOY_MODE .env)"

# ── 6. 入库 + 启动服务 ────────────────────────────────────────────
echo "[6/6] 知识库入库..."
.venv/bin/python scripts/ingest_lingshan.py

echo "配置并启动 systemd 服务..."
cat > /etc/systemd/system/digital-person.service << 'SERVICE'
[Unit]
Description=景区导览AI数字人
After=network.target

[Service]
Type=simple
WorkingDirectory=/root/digital-person
ExecStart=/root/digital-person/.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable digital-person
systemctl restart digital-person

sleep 3
PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || echo "116.62.136.211")
echo ""
echo "======================================"
echo "  部署完成！"
echo "  API 地址：http://$PUBLIC_IP:8000"
echo "  健康检查：http://$PUBLIC_IP:8000/health"
echo "  接口文档：http://$PUBLIC_IP:8000/docs"
echo "======================================"
echo "查看日志：journalctl -u digital-person -f"
