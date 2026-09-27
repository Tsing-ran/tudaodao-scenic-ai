"""
对比 BGE-M3（本地GPU）vs DashScope text-embedding-v3（云端API）的检索效果。
运行前确保灵山知识库已入库（用的是 BGE-M3 入的库）。
"""

import os, sys, time
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
for v in ("ALL_PROXY","all_proxy","HTTPS_PROXY","https_proxy","HTTP_PROXY","http_proxy"):
    os.environ.pop(v, None)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import dashscope
from dashscope import TextEmbedding
from backend.rag.embedder import embed_texts as bge_embed
from backend.rag.retriever import get_collection
from backend.core.config import settings

QUERIES = [
    ("灵山大佛有多高",        "88米"),
    ("九龙灌浴几点有表演",     "10:00"),
    ("适合亲子的游览路线",     "亲子"),
    ("灵山梵宫是什么风格",     "卢浮宫"),
    ("南门进去第一个景点",     "照壁"),
    ("灵山大佛台阶有多少级",   "216"),
    ("拈花湾在哪里",          "禅意小镇"),
    ("祥符禅寺历史",          "玄奘"),
]


def dashscope_embed(texts):
    resp = TextEmbedding.call(
        model=TextEmbedding.Models.text_embedding_v3,
        input=texts,
    )
    return [item["embedding"] for item in resp.output["embeddings"]]


def search(query_vec, top_k=4):
    col = get_collection("lingshan")
    result = col.query(query_embeddings=[query_vec], n_results=top_k,
                       include=["documents"])
    return result["documents"][0]


def check_hit(chunks, keyword):
    return any(keyword in c for c in chunks)


print("=" * 65)
print(f"{'问题':<20} {'关键词':<10} {'BGE-M3':^12} {'DashScope':^12}")
print("=" * 65)

bge_hits = 0
ds_hits = 0
bge_times = []
ds_times = []

for query, keyword in QUERIES:
    # BGE-M3
    t0 = time.time()
    bge_vec = bge_embed([query])[0]
    bge_chunks = search(bge_vec)
    bge_t = time.time() - t0
    bge_ok = check_hit(bge_chunks, keyword)

    # DashScope（注意：DashScope 向量维度可能与 BGE-M3 不同，这里只测 DashScope 自检索）
    t0 = time.time()
    try:
        ds_vec = dashscope_embed([query])[0]
        # 维度不同时无法在同一个 collection 里搜，改为直接用 DashScope 向量搜索
        # 这里测的是"用 DashScope 向量检索 BGE-M3 入的库"的效果（跨维度无意义）
        # 实际云端部署时库也要用 DashScope 重新入库，这里只测 API 速度
        ds_t = time.time() - t0
        ds_ok = "需重入库"
    except Exception as e:
        ds_t = time.time() - t0
        ds_ok = f"错误:{e}"

    bge_times.append(bge_t)
    ds_times.append(ds_t)
    if bge_ok:
        bge_hits += 1

    bge_mark = "✓" if bge_ok else "✗"
    print(f"{query:<20} {keyword:<10} {bge_mark}({bge_t:.2f}s)   {ds_t:.2f}s")

print("=" * 65)
print(f"{'BGE-M3 准确率:':<30} {bge_hits}/{len(QUERIES)} = {bge_hits/len(QUERIES)*100:.0f}%")
print(f"{'BGE-M3 平均检索耗时:':<30} {sum(bge_times)/len(bge_times)*1000:.0f}ms")
print(f"{'DashScope 平均API耗时:':<30} {sum(ds_times)/len(ds_times)*1000:.0f}ms（仅嵌入，不含检索）")
print()
print("注：DashScope 向量是 1536维，BGE-M3 是 1024维，")
print("    云端部署时需用 DashScope 重新入库才能正确对比召回效果。")
