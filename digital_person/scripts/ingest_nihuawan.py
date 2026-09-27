"""
把拈花湾禅意小镇的数据入库（scenic_id=nihuawan）。
数据来源：结构化数据集 docx 中的第二张表（拈花湾景点数据集）。
"""

import os, sys, uuid
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
for _v in ("ALL_PROXY","all_proxy","HTTPS_PROXY","https_proxy","HTTP_PROXY","http_proxy"):
    os.environ.pop(_v, None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from docx import Document
import chromadb
from backend.core.config import settings

SCENIC_ID = "nihuawan"
DOCX = Path(__file__).resolve().parent.parent / "示范景区公开资料包" / "灵山胜境 景点结构化数据集.docx"


def extract_nihuawan_chunks() -> list[dict]:
    """提取 docx 中的拈花湾表格，转成文本 chunk。"""
    doc = Document(DOCX)
    # Table[1] 是拈花湾子表
    table = doc.tables[1]
    headers = [c.text.strip() for c in table.rows[0].cells]
    chunks = []
    for row in table.rows[1:]:
        values = [c.text.strip() for c in row.cells]
        if not any(values):
            continue
        # 每行转为"字段: 值 | 字段: 值 | ..."格式
        pairs = [f"{h}: {v}" for h, v in zip(headers, values) if v]
        text = " | ".join(pairs)
        if text:
            chunks.append({"text": text, "source": "拈花湾景点结构化数据集"})
    return chunks


def _embed(texts):
    from backend.core.config import settings
    if settings.deploy_mode == "cloud":
        from backend.rag.embedder_dashscope import embed_texts_cloud
        return embed_texts_cloud(texts)
    from backend.rag.embedder import embed_texts
    return embed_texts(texts)


if __name__ == "__main__":
    from backend.core.config import settings
    mode = settings.deploy_mode
    print(f"部署模式: {mode}")

    client = chromadb.PersistentClient(path=str(settings.vector_store_dir))
    try:
        client.delete_collection(f"scenic_{SCENIC_ID}")
        print(f"已清空旧知识库: {SCENIC_ID}")
    except Exception:
        pass

    col = client.create_collection(f"scenic_{SCENIC_ID}", metadata={"hnsw:space": "cosine"})
    chunks = extract_nihuawan_chunks()
    print(f"提取到 {len(chunks)} 个 chunk，嵌入中...")

    texts = [c["text"] for c in chunks]
    vecs = _embed(texts)
    col.add(
        ids=[str(uuid.uuid4()) for _ in texts],
        documents=texts,
        embeddings=vecs,
        metadatas=[{"source": c["source"]} for c in chunks],
    )
    print(f"拈花湾入库完成，共 {len(texts)} 个 chunk")
