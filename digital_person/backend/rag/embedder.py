"""
本地 BGE-M3 嵌入模型封装。

BGE-M3 同时支持稠密向量、稀疏向量、多向量，这里只用稠密向量（dense）。
首次运行会从 HuggingFace 下载模型（约 2.2GB），之后缓存在本地。
"""

import os
from typing import List

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
for _var in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy",
             "HTTP_PROXY", "http_proxy"):
    os.environ.pop(_var, None)

from huggingface_hub import snapshot_download
from FlagEmbedding import BGEM3FlagModel
from backend.core.config import settings

_model: BGEM3FlagModel | None = None


def _ensure_model_downloaded(model_name: str) -> str:
    """下载模型到本地缓存，跳过会导致 403 的无关文件。"""
    local_path = snapshot_download(
        repo_id=model_name,
        ignore_patterns=["*.DS_Store", "imgs/*", "*.h5", "*.ot", "flax_model*", "rust_model*", "tf_model*"],
    )
    return local_path


def get_embedder() -> BGEM3FlagModel:
    global _model
    if _model is None:
        local_path = _ensure_model_downloaded(settings.embedding_model)
        _model = BGEM3FlagModel(
            local_path,
            use_fp16=True,
        )
    return _model


def embed_texts(texts: List[str]) -> List[List[float]]:
    """返回归一化后的稠密向量列表，可直接存入 ChromaDB。"""
    model = get_embedder()
    result = model.encode(
        texts,
        batch_size=32,
        max_length=512,
        return_dense=True,
        return_sparse=False,
        return_colbert_vecs=False,
    )
    return result["dense_vecs"].tolist()
