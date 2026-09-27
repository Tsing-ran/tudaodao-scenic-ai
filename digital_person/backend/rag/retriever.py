"""
EA-RAG 检索器（Entity-Anchored Adaptive RAG，自研编排层算法）。

在「稠密(BGE-M3) + 稀疏(BM25) → 重排(BGE-Reranker)」基线之上，叠加三个自研机制
（均可经 settings.ea_* 独立开关，供消融实验）：

  ① 实体锚定 Entity Anchoring
     景区知识库的景点名表是已知先验（结构化 chunk 含"景点名称: X"）。
     query 与景点名做最长公共子串匹配，命中则该景点的 chunk 在融合分上加锚定加成。
     解决真实漏检：游客说"光明顶"，稠密检索却召回其他景点的 chunk。

  ② 查询特征自适应融合 Adaptive Fusion
     基线是 dense/sparse 候选简单拼接（隐式等权）。改为加权 RRF（倒数排名融合），
     权重按 query 特征动态调整：含数字/量词特征 → BM25 权重↑（精确匹配强）；
     口语化长句 → dense 权重↑（语义理解强）。

  ③ 置信度门控 Confidence Gating
     Reranker top1 分数（normalize 后 0~1）本身就是"知识库里有没有答案"的置信度，
     基线白白丢弃。低于阈值 → 返回空召回，触发兜底话术——把"拒答"从纯靠
     prompt 自觉，变成有数学依据的门控。

延迟优化（沿袭基线）：
- 云端模式 retrieve_async() 用 asyncio.gather 让 DashScope embed 和 BM25 并行
"""

import asyncio
import os
import re
from difflib import SequenceMatcher
from typing import List

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
for _var in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy",
             "HTTP_PROXY", "http_proxy"):
    os.environ.pop(_var, None)

import chromadb
from rank_bm25 import BM25Okapi

from backend.core.config import settings

_reranker = None

# RRF 平滑常数（业界标准取 60）；锚定加成约为 RRF rank1 分值的 1.2 倍，
# 足以把命中景点的 chunk 顶进前排，又不至于完全压过相关性排序
_RRF_K = 60
_ANCHOR_BONUS = 0.02

LAST_TOP1_SCORE: float = 0.0   # 最近一次检索的重排 top1 分（门控标定/可观测性用）


def get_reranker():
    global _reranker
    if _reranker is None:
        from huggingface_hub import snapshot_download
        from FlagEmbedding import FlagReranker
        local_path = snapshot_download(
            repo_id=settings.reranker_model,
            ignore_patterns=["*.DS_Store", "imgs/*", "*.h5", "flax_model*",
                             "rust_model*", "tf_model*"],
        )
        _reranker = FlagReranker(local_path, use_fp16=True)
    return _reranker


def get_collection(scenic_id: str) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(settings.vector_store_dir))
    return client.get_or_create_collection(
        name=f"scenic_{scenic_id}",
        metadata={"hnsw:space": "cosine"},
    )


def _embed_query_sync(query: str) -> List[float]:
    if settings.deploy_mode == "cloud":
        from backend.rag.embedder_dashscope import embed_texts_cloud
        return embed_texts_cloud([query])[0]
    from backend.rag.embedder import embed_texts
    return embed_texts([query])[0]


def _bm25_search(query: str, all_docs: List[str], top_k: int) -> List[str]:
    tokenized = [list(d) for d in all_docs]
    bm25 = BM25Okapi(tokenized)
    scores = bm25.get_scores(list(query))
    top_k = min(top_k, len(all_docs))
    indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [all_docs[i] for i in indices]


def _dense_search(query_vec: List[float], collection: chromadb.Collection,
                  dense_k: int) -> List[str]:
    result = collection.query(
        query_embeddings=[query_vec],
        n_results=dense_k,
        include=["documents"],
    )
    return result["documents"][0]


# ══════════════════════════════════════════════════════════════════════
# ① 实体锚定
# ══════════════════════════════════════════════════════════════════════

_entity_cache: dict[str, list[str]] = {}
_ENTITY_PATTERN = re.compile(r"景点名称[:：]\s*([^|\n]+)")


def _get_entities(scenic_id: str, all_docs: List[str]) -> list[str]:
    """从结构化 chunk 中提取该景区全部景点名（每景区缓存一次）。"""
    if scenic_id not in _entity_cache:
        names = []
        for d in all_docs:
            m = _ENTITY_PATTERN.search(d)
            if m:
                name = m.group(1).strip()
                if name and name not in names:
                    names.append(name)
        _entity_cache[scenic_id] = names
    return _entity_cache[scenic_id]


def invalidate_entity_cache(scenic_id: str | None = None) -> None:
    """知识库更新后调用，清空景点名缓存。"""
    if scenic_id is None:
        _entity_cache.clear()
    else:
        _entity_cache.pop(scenic_id, None)


def _match_entities(query: str, entities: list[str]) -> list[str]:
    """
    query 与景点名匹配。匹配条件（满足其一）：
      - 景点名完整出现在 query 中；
      - 最长公共子串 ≥ max(2, 景点名长度的一半)——容忍口语省略
        （"大照壁多长" 命中 "灵山大照壁"）。
    """
    matched = []
    for ent in entities:
        if ent in query:
            matched.append(ent)
            continue
        m = SequenceMatcher(None, query, ent).find_longest_match(
            0, len(query), 0, len(ent))
        if m.size >= max(2, len(ent) // 2):
            matched.append(ent)
    return matched


# ══════════════════════════════════════════════════════════════════════
# ② 查询特征自适应融合（加权 RRF）
# ══════════════════════════════════════════════════════════════════════

# 数字/量词类问题特征：精确匹配（BM25）更可靠
_FACTUAL_PATTERN = re.compile(
    r"\d|几|多少|哪一?年|多高|多大|多长|多宽|多深|多重|面积|高度|长度|票价|价格")


def _fusion_weights(query: str) -> tuple[float, float]:
    """返回 (w_dense, w_sparse)。默认等权；按 query 特征自适应。"""
    if not settings.ea_adaptive_fusion:
        return 1.0, 1.0
    w_dense, w_sparse = 1.0, 1.0
    if _FACTUAL_PATTERN.search(query):
        w_sparse = 1.4          # 数字/量词 → 关键词精确匹配更重要
    elif len(query) >= 18:
        w_dense = 1.3           # 口语化长句 → 语义理解更重要
    return w_dense, w_sparse


def _fuse(query: str, dense_docs: List[str], sparse_docs: List[str],
          all_docs: List[str], scenic_id: str) -> List[str]:
    """
    加权 RRF 融合 + 实体锚定加成，返回按融合分排序的候选。
    关闭两机制时退化为基线行为（等权 RRF ≈ 原拼接去重的排序版）。
    """
    w_dense, w_sparse = _fusion_weights(query)

    scores: dict[str, float] = {}
    for rank, doc in enumerate(dense_docs):
        scores[doc] = scores.get(doc, 0.0) + w_dense / (_RRF_K + rank + 1)
    for rank, doc in enumerate(sparse_docs):
        scores[doc] = scores.get(doc, 0.0) + w_sparse / (_RRF_K + rank + 1)

    if settings.ea_entity_anchor:
        matched = _match_entities(query, _get_entities(scenic_id, all_docs))
        if matched:
            # 命中景点的 chunk 加锚定加成；不在候选里的也补进来（兜住漏检）
            for doc in all_docs:
                if any(ent in doc for ent in matched):
                    scores[doc] = scores.get(doc, 0.0) + _ANCHOR_BONUS

    return [d for d, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)]


# ══════════════════════════════════════════════════════════════════════
# ③ 置信度门控 + 主检索入口
# ══════════════════════════════════════════════════════════════════════

def retrieve(query: str, scenic_id: str) -> List[str]:
    """同步检索（本地模式 + 兜底）。管理端「检索设置」可按景区覆盖策略/top_k/阈值。"""
    from backend.rag.retrieval_config import get_overrides
    ov = get_overrides(scenic_id)
    final_k = ov.top_k or settings.rerank_top_k

    collection = get_collection(scenic_id)
    total_docs = collection.count()
    if total_docs == 0:
        return []

    all_docs: List[str] = collection.get(include=["documents"])["documents"]

    if ov.strategy == "keyword":          # 仅 BM25（管理员显式选择）
        dense_docs = []
    else:
        query_vec = _embed_query_sync(query)
        dense_k = min(settings.dense_top_k, total_docs)
        dense_docs = _dense_search(query_vec, collection, dense_k)

    if ov.strategy == "semantic":         # 仅稠密（管理员显式选择）
        sparse_docs = []
    else:
        sparse_docs = _bm25_search(query, all_docs, settings.sparse_top_k)

    candidates = _fuse(query, dense_docs, sparse_docs, all_docs, scenic_id)

    if settings.deploy_mode == "cloud":
        return candidates[:final_k]

    reranker = get_reranker()
    # 候选可能因锚定补漏而变多，重排只精算前 16 条控制延迟
    candidates = candidates[:16]
    pairs = [[query, doc] for doc in candidates]
    rerank_scores = reranker.compute_score(pairs, normalize=True)
    if not isinstance(rerank_scores, list):
        rerank_scores = [rerank_scores]
    ranked = sorted(zip(rerank_scores, candidates), key=lambda x: x[0], reverse=True)

    global LAST_TOP1_SCORE
    LAST_TOP1_SCORE = ranked[0][0] if ranked else 0.0  # 供门控阈值标定实验读取

    # 置信度门控：连最相关的候选都低于阈值 → 知识库无此信息，触发兜底
    gate = ov.threshold if ov.threshold is not None else settings.ea_gate_threshold
    if settings.ea_confidence_gate and ranked and ranked[0][0] < gate:
        return []

    return [doc for _, doc in ranked[:final_k]]


async def retrieve_async(query: str, scenic_id: str) -> List[str]:
    """
    异步检索（云端模式专用）。

    关键优化：DashScope embed（~400ms 网络IO）和 BM25（~30ms CPU）并行执行。
    云端无 reranker，门控不生效（融合与锚定生效）。
    """
    from backend.rag.retrieval_config import get_overrides
    ov = get_overrides(scenic_id)
    final_k = ov.top_k or settings.rerank_top_k

    collection = get_collection(scenic_id)
    total_docs = collection.count()
    if total_docs == 0:
        return []

    # 提前取所有文档（BM25 需要），这一步很快（本地 SQLite）
    all_docs: List[str] = collection.get(include=["documents"])["documents"]

    loop = asyncio.get_event_loop()

    # 并行：embed（网络IO）+ BM25（CPU）
    query_vec, sparse_docs = await asyncio.gather(
        loop.run_in_executor(None, _embed_query_sync, query),
        loop.run_in_executor(None, _bm25_search, query, all_docs, settings.sparse_top_k),
    )

    if ov.strategy == "semantic":
        sparse_docs = []

    if ov.strategy == "keyword":
        dense_docs = []
    else:
        dense_k = min(settings.dense_top_k, total_docs)
        dense_docs = _dense_search(query_vec, collection, dense_k)

    candidates = _fuse(query, dense_docs, sparse_docs, all_docs, scenic_id)
    return candidates[:final_k]
