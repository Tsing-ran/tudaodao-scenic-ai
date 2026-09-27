"""
DashScope 云端嵌入（部署到阿里云时使用）。
text-embedding-v3 是通义千问的向量嵌入模型，效果接近 BGE-M3，无需 GPU。
"""

import os
from typing import List
import dashscope
from dashscope import TextEmbedding


def embed_texts_cloud(texts: List[str]) -> List[List[float]]:
    """批量嵌入，DashScope 单次最多 25 条，自动分批。"""
    all_vecs = []
    batch_size = 10
    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        resp = TextEmbedding.call(
            model="text-embedding-v3",
            input=batch,
        )
        vecs = [item["embedding"] for item in resp.output["embeddings"]]
        all_vecs.extend(vecs)
    return all_vecs
