"""
把灵山胜境的三个文档一次性入库。
- 本地模式（DEPLOY_MODE=local）：用本地 BGE-M3 嵌入
- 云端模式（DEPLOY_MODE=cloud）：用 DashScope text-embedding-v3

运行方式：
    cd /home/jiale/Desktop/Digital_Person
    python scripts/ingest_lingshan.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# 清除 SOCKS 代理（本地开发环境存在，云端不需要）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
for _proxy_var in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy",
                   "HTTP_PROXY", "http_proxy"):
    os.environ.pop(_proxy_var, None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.rag.indexer import index_documents, clear_scenic

SCENIC_ID = "lingshan"
DATA_DIR = Path(__file__).resolve().parent.parent / "示范景区公开资料包"

DOCS = [
    DATA_DIR / "灵山胜境：历史、文化、景点特色与个性化游览指南.docx",
    DATA_DIR / "灵山胜境 景点结构化数据集.docx",
]

if __name__ == "__main__":
    from backend.core.config import settings
    mode = settings.deploy_mode
    print(f"部署模式: {mode}（{'DashScope API' if mode == 'cloud' else '本地 BGE-M3'}）")
    print(f"清空旧知识库: {SCENIC_ID}")
    clear_scenic(SCENIC_ID)

    msg = "DashScope API 入库中..." if mode == "cloud" else "开始入库（首次运行会下载 BGE-M3 模型约 2.2GB）..."
    print(msg)
    count = index_documents([p for p in DOCS if p.exists()], SCENIC_ID)
    print(f"入库完成，共 {count} 个 chunk")
