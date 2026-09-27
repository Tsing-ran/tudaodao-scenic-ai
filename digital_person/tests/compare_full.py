"""
完整对比：BGE-M3 vs DashScope
1. 用 DashScope 把灵山文档重新入一个独立的 collection
2. 用同一批问题分别走两套完整 RAG 流水线
3. 对比答案质量和耗时
"""

import os, sys, time, uuid
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
for v in ("ALL_PROXY","all_proxy","HTTPS_PROXY","https_proxy","HTTP_PROXY","http_proxy"):
    os.environ.pop(v, None)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import dashscope
dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY", "")

import chromadb
from dashscope import TextEmbedding
from backend.rag.loader import load_docx_as_chunks
from backend.rag.embedder import embed_texts as bge_embed
from backend.llm.client import chat
from backend.llm.prompts import build_system_prompt
from backend.core.config import settings
from pathlib import Path

DATA_DIR = Path("示范景区公开资料包")
DOCS = [
    DATA_DIR / "灵山胜境：历史、文化、景点特色与个性化游览指南.docx",
    DATA_DIR / "灵山胜境 景点结构化数据集.docx",
]

# ── 建 DashScope 知识库 ───────────────────────────────────────────
def ds_embed(texts):
    import dashscope as _ds
    _ds.api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    all_vecs = []
    for i in range(0, len(texts), 10):
        batch = texts[i:i+10]
        resp = TextEmbedding.call(model="text-embedding-v3", input=batch)
        if resp.output is None:
            raise RuntimeError(f"DashScope 嵌入失败: {resp.status_code} {resp.message}")
        all_vecs.extend([item["embedding"] for item in resp.output["embeddings"]])
    return all_vecs

def build_ds_collection():
    client = chromadb.PersistentClient(path=str(settings.vector_store_dir))
    try:
        client.delete_collection("scenic_lingshan_ds")
    except Exception:
        pass
    col = client.create_collection("scenic_lingshan_ds",
                                    metadata={"hnsw:space": "cosine"})
    all_chunks = []
    for doc in DOCS:
        if doc.exists():
            all_chunks.extend(load_docx_as_chunks(doc))
    texts = [c["text"] for c in all_chunks]
    print(f"  DashScope 入库中（{len(texts)} 个 chunk）...")
    t0 = time.time()
    vecs = ds_embed(texts)
    col.add(ids=[str(uuid.uuid4()) for _ in texts], documents=texts,
            embeddings=vecs,
            metadatas=[{"source": c["source"]} for c in all_chunks])
    print(f"  入库完成，耗时 {time.time()-t0:.1f}s")
    return col

def get_bge_collection():
    client = chromadb.PersistentClient(path=str(settings.vector_store_dir))
    return client.get_collection("scenic_lingshan")

# ── 检索 ─────────────────────────────────────────────────────────
def search(col, query_vec, top_k=6):
    r = col.query(query_embeddings=[query_vec], n_results=top_k,
                  include=["documents"])
    return r["documents"][0]

# ── 问答 ─────────────────────────────────────────────────────────
QUESTIONS = [
    "灵山大佛有多高？",
    "九龙灌浴每天几点有表演？",
    "灵山大佛台阶有多少级？",
    "拈花湾适合什么类型的游客？",
    "灵山梵宫被称为什么？",
]

def answer_with(col, embed_fn, query):
    vec = embed_fn([query])[0]
    chunks = search(col, vec)
    prompt = build_system_prompt("灵山胜境", "灵山小慧", chunks)
    return chat(prompt, [], query)


print("=" * 70)
print("建立 DashScope 知识库（首次运行需调用 API）...")
ds_col = build_ds_collection()
bge_col = get_bge_collection()
print()

for q in QUESTIONS:
    print(f"问：{q}")

    t0 = time.time()
    bge_ans = answer_with(bge_col, bge_embed, q)
    bge_t = time.time() - t0

    t0 = time.time()
    ds_ans = answer_with(ds_col, ds_embed, q)
    ds_t = time.time() - t0

    print(f"  BGE-M3  ({bge_t:.1f}s)：{bge_ans[:80]}...")
    print(f"  DashScope({ds_t:.1f}s)：{ds_ans[:80]}...")
    print()
