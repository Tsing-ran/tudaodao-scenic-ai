#!/bin/bash
# 阿里云 ECS 一键部署脚本
# 在 ECS 服务器上运行：bash deploy.sh

set -e

echo "=== 景区导览AI数字人 - 云端部署 ==="

# 1. 安装 Docker
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker && systemctl start docker
fi

# 2. 克隆代码（或从本地 scp 过来）
# git clone <你的仓库> digital-person
# cd digital-person

# 3. 写入环境变量
cat > .env.cloud << EOF
DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}
DEPLOY_MODE=cloud
EOF

# 4. 构建并启动
docker build -t digital-person:latest .
docker run -d \
    --name digital-person \
    --restart always \
    -p 8000:8000 \
    --env-file .env.cloud \
    -v $(pwd)/vector_store:/app/vector_store \
    -v $(pwd)/knowledge_base:/app/knowledge_base \
    digital-person:latest

echo "=== 部署完成，服务运行在 http://$(curl -s ifconfig.me):8000 ==="
