"""
将西湖、黄山、故宫三个新景区一次性入库。

运行方式：
    cd /home/jiale/Desktop/Digital_Person
    python scripts/ingest_new_scenics.py          # 入库全部三个
    python scripts/ingest_new_scenics.py xihu     # 只入库西湖
"""

import os, sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
for _v in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
    os.environ.pop(_v, None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.rag.indexer import index_documents, clear_scenic

DATA_DIR = Path(__file__).resolve().parent.parent / "示范景区公开资料包"

SCENICS = {
    "xihu": {
        "name": "西湖",
        "docs": [
            DATA_DIR / "杭州西湖：历史、文化、景点特色与个性化游览指南.docx",
            DATA_DIR / "杭州西湖 景点结构化数据集.docx",
        ],
    },
    "huangshan": {
        "name": "黄山",
        "docs": [
            DATA_DIR / "安徽黄山：历史、文化、景点特色与个性化游览指南.docx",
            DATA_DIR / "安徽黄山 景点结构化数据集.docx",
        ],
    },
    "gugong": {
        "name": "故宫",
        "docs": [
            DATA_DIR / "北京故宫博物院：历史、文化、景点特色与个性化游览指南.docx",
            DATA_DIR / "北京故宫博物院 景点结构化数据集.docx",
        ],
    },
}


if __name__ == "__main__":
    from backend.core.config import settings
    mode = settings.deploy_mode
    print(f"部署模式: {mode}（{'DashScope API' if mode == 'cloud' else '本地 BGE-M3'}）\n")

    targets = sys.argv[1:] if len(sys.argv) > 1 else list(SCENICS.keys())
    invalid = [t for t in targets if t not in SCENICS]
    if invalid:
        print(f"未知景区 ID: {invalid}，可选: {list(SCENICS.keys())}")
        sys.exit(1)

    total = 0
    for sid in targets:
        cfg = SCENICS[sid]
        docs = [p for p in cfg["docs"] if p.exists()]
        missing = [p for p in cfg["docs"] if not p.exists()]
        if missing:
            print(f"  警告：以下文件不存在，跳过：{[p.name for p in missing]}")
        if not docs:
            print(f"  ✗ {cfg['name']}：无可用文档，跳过")
            continue

        print(f"清空旧知识库: scenic_{sid}")
        clear_scenic(sid)
        print(f"入库 {cfg['name']}（{len(docs)} 个文档）...")
        count = index_documents(docs, sid)
        print(f"  ✓ {cfg['name']} 入库完成，共 {count} 个 chunk\n")
        total += count

    print(f"全部完成，共入库 {total} 个 chunk")
