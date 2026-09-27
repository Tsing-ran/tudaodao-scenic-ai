"""
管理端知识库内容管理 · roundtrip 测试（FAQ/文本 CRUD + RAG 增量同步）。

运行：cd /home/jiale/Desktop/Digital_Person && DEPLOY_MODE=cloud .venv/bin/python tests/test_kb_manage.py
覆盖：FAQ 增/查/改/删 + 每步 RAG collection 按稳定 id 同步核验；文本段落同理；docs 列表。
用真实 SQLite + ChromaDB（cloud 模式 DashScope 嵌入），测试条目用 test_ 前缀景区并清理。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
import os
for _v in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
    os.environ.pop(_v, None)
os.environ.setdefault("DEPLOY_MODE", "cloud")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.db.database import init_db
from backend.api.kb_manage import router
from backend.rag.retriever import get_collection

SCENIC = "test_kbm"
init_db()
app = FastAPI(); app.include_router(router)
client = TestClient(app)
col = get_collection(SCENIC)

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1; print(f"  ✅ {name}")
    else:
        failed += 1; print(f"  ❌ {name}  {detail}")


def in_rag(item_id: str) -> bool:
    return bool(col.get(ids=[item_id])["ids"])


print("【FAQ CRUD + RAG 同步】")
r = client.post("/kb/faq", json={"scenic_id": SCENIC, "question": "测试问题X", "answer": "测试答案Y", "category": "c"})
check("新增返回 id+synced", r.status_code == 200 and r.json().get("synced"), r.text)
fid = r.json()["id"]
check("RAG 已同步 faq_id", in_rag(f"faq_{fid}"))
check("列表含新条目", any(i["id"] == fid for i in client.get(f"/kb/faq?scenic_id={SCENIC}").json()["items"]))
client.put(f"/kb/faq/{fid}", json={"scenic_id": SCENIC, "question": "改后问题Z", "answer": "改后答案", "category": "c"})
doc = col.get(ids=[f"faq_{fid}"])["documents"][0]
check("编辑后 RAG 文档更新", "改后问题Z" in doc, doc)
client.delete(f"/kb/faq/{fid}")
check("删除后 RAG 移除", not in_rag(f"faq_{fid}"))
check("删除后列表无此条", not any(i["id"] == fid for i in client.get(f"/kb/faq?scenic_id={SCENIC}").json()["items"]))
check("删除不存在的 404", client.delete(f"/kb/faq/{fid}").status_code == 404)

print("【文本段落 CRUD + RAG 同步】")
r = client.post("/kb/text", json={"scenic_id": SCENIC, "title": "标题T", "content": "正文内容", "category": "c"})
tid = r.json()["id"]
check("新增文本 synced", r.json().get("synced"))
check("RAG 已同步 text_id", in_rag(f"text_{tid}"))
client.delete(f"/kb/text/{tid}")
check("删除后 RAG 移除", not in_rag(f"text_{tid}"))

print("【docs 列表】")
check("docs 端点可用", "docs" in client.get(f"/kb/docs?scenic_id={SCENIC}").json())

# 清理测试 collection
import chromadb
from backend.core.config import settings
try:
    chromadb.PersistentClient(path=str(settings.vector_store_dir)).delete_collection(f"scenic_{SCENIC}")
except Exception:
    pass

print(f"\n{'='*40}\n通过 {passed} / {passed + failed}")
sys.exit(0 if failed == 0 else 1)
