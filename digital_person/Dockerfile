FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# 先装依赖（利用 Docker 缓存层）
COPY requirements.cloud.txt .
RUN uv pip install --system -r requirements.cloud.txt \
    --index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 复制代码
COPY backend/ ./backend/
COPY vector_store/ ./vector_store/

ENV DEPLOY_MODE=cloud
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
