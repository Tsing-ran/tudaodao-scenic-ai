"""知识库自检（管理端「知识库体检」）：从已入库 chunk 自动出题 → 跑完整 RAG 链路 →
关键词命中评分 → 返回准确率报告。

设计要点（回应"换了知识库还能保 90% 吗"的评审拷问）：
  1. 题目从 ChromaDB 现有 chunk 现场派生，不依赖任何景区专属文件——任意新上传的
     知识库都能自检，坐实"换库不换码"。
  2. 评分关键词由程序**确定性抽取**（数字 + 引号/书名号内专名），可复现、可肉眼核对；
     LLM（qwen-flash）只负责把 chunk 组织成自然的游客问法，不参与评分。
  3. 全程不写 conversations、不进答案缓存——测试流量不污染运营分析数据。
成本提示：每题 2 次 LLM 调用（出题 flash + 答题 plus），sample 默认 6、上限 10。
"""
import re
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.rag.retriever import get_collection, retrieve
from backend.rag.pipeline import get_scenic_config
from backend.llm.prompts import build_system_prompt
from backend.llm.client import chat, extract_emotion

router = APIRouter(prefix="/kb", tags=["knowledge-base"])

_QGEN_PROMPT = (
    "你是景区知识库测试出题员。根据用户给出的资料片段，出一道游客口吻的事实性问题，"
    "该问题的正确答案必须包含关键词：{keywords}。"
    "只输出问题本身（不超过30字），不要提到「资料」「文中」「片段」等字眼。"
)


def _extract_numbers(text: str) -> list[str]:
    """抽取有计量意义的数字（≥2位或含小数点），与 tests/eval_kb.py 同口径。"""
    out, seen = [], set()
    for n in re.findall(r"\d+(?:\.\d+)?", text or ""):
        if n not in seen and (len(n) >= 2 or "." in n):
            seen.add(n)
            out.append(n)
    return out


def _extract_terms(text: str) -> list[str]:
    """抽取引号“”与书名号《》「」内 2-12 字专名。"""
    out, seen = [], set()
    for t in re.findall(r"[“\"「《]([^”\"」》]{2,12})[”\"」》]", text or ""):
        t = t.strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def pick_fact_chunks(docs: list[str], sample: int) -> list[dict]:
    """筛出含确定性事实的 chunk，均匀取样，附带抽好的关键词。

    数字优先于专名（强信号、无歧义）；每题最多 3 个关键词，命中任一即算通过。
    均匀间隔取样（而非随机）保证同一知识库两次体检结果可复现。
    """
    candidates = []
    for d in docs:
        nums, terms = _extract_numbers(d), _extract_terms(d)
        kws = (nums[:2] + terms[:1]) if nums else terms[:3]
        if kws:
            candidates.append({"chunk": d, "keywords": kws[:3],
                               "kw_type": "数字事实" if nums else "专名事实"})
    if not candidates:
        return []
    if len(candidates) <= sample:
        return candidates
    step = len(candidates) / sample
    return [candidates[int(i * step)] for i in range(sample)]


def _gen_question(chunk: str, keywords: list[str]) -> str:
    """qwen-flash 把 chunk 组织成自然问法；失败时回退为首行主题模板题。"""
    try:
        q = chat(_QGEN_PROMPT.format(keywords="、".join(keywords)),
                 [], chunk[:500], fast=True).strip().strip("「」\"“”")
        if 5 <= len(q) <= 60:
            return q
    except Exception:
        pass
    topic = (chunk.split("\n")[0] or "该内容")[:20]
    return f"请介绍一下{topic}的具体情况。"


class SelfTestIn(BaseModel):
    scenic_id: str = "lingshan"
    sample: int = Field(default=6, ge=1, le=10)


@router.post("/self-test")
def kb_self_test(body: SelfTestIn):
    """知识库体检：自动出题→RAG 答题→关键词评分。同步返回，约 5-10s/题。"""
    collection = get_collection(body.scenic_id)
    total_chunks = collection.count()
    if total_chunks == 0:
        raise HTTPException(status_code=404, detail=f"知识库 {body.scenic_id} 为空，请先上传文档")

    docs = collection.get(limit=500, include=["documents"])["documents"] or []
    cases = pick_fact_chunks(docs, body.sample)
    if not cases:
        raise HTTPException(status_code=422, detail="知识库中未找到含确定性事实（数字/专名）的内容，无法自动出题")

    cfg = get_scenic_config(body.scenic_id)
    t0 = time.time()
    items, passed = [], 0
    for case in cases:
        question = _gen_question(case["chunk"], case["keywords"])
        # 走与游客问答完全相同的检索+生成链路，但不落 conversations、不进缓存
        q0 = time.time()
        context_chunks = retrieve(question, body.scenic_id)
        system_prompt = build_system_prompt(
            cfg["name"], cfg["guide_name"], context_chunks, "zh")
        try:
            reply, _ = extract_emotion(chat(system_prompt, [], question, fast=False))
        except Exception as exc:
            items.append({"question": question, "keywords": case["keywords"],
                          "hit_keywords": [], "passed": False, "score": 0.0,
                          "kw_type": case["kw_type"], "retrieved": len(context_chunks),
                          "source": _chunk_source(context_chunks),
                          "duration_ms": int((time.time() - q0) * 1000),
                          "answer": f"（答题失败：{exc}）"})
            continue
        hits = [k for k in case["keywords"] if k in reply]
        ok = len(hits) > 0
        passed += ok
        items.append({"question": question, "keywords": case["keywords"],
                      "hit_keywords": hits, "passed": ok,
                      "score": round(len(hits) / len(case["keywords"]), 2),
                      "kw_type": case["kw_type"], "retrieved": len(context_chunks),
                      "source": _chunk_source(context_chunks),
                      "duration_ms": int((time.time() - q0) * 1000),
                      "answer": reply})

    # 按题型聚合通过率（数字事实 vs 专名事实），暴露知识库对硬事实/专名的掌握差异
    by_type: dict[str, dict] = {}
    for it in items:
        b = by_type.setdefault(it["kw_type"], {"total": 0, "passed": 0})
        b["total"] += 1
        b["passed"] += 1 if it["passed"] else 0
    by_type_out = [
        {"type": k, "total": v["total"], "passed": v["passed"],
         "accuracy": round(v["passed"] / v["total"] * 100, 1) if v["total"] else 0.0}
        for k, v in by_type.items()
    ]
    durs = [it["duration_ms"] for it in items] or [0]

    return {
        "scenic_id": body.scenic_id,
        "total_chunks": total_chunks,
        "sample": len(items),
        "passed": passed,
        "failed": len(items) - passed,
        "accuracy": round(passed / len(items) * 100, 1),
        "duration_s": round(time.time() - t0, 1),
        "avg_duration_ms": int(sum(durs) / len(durs)),
        "by_type": by_type_out,
        "items": items,
    }


def _chunk_source(chunks: list[str]) -> str:
    """从命中的首个片段推断来源标签，用于报告展示。"""
    if not chunks:
        return "未检索到相关内容"
    top = chunks[0]
    if top.startswith("问："):
        return "FAQ 问答"
    head = top.split("|", 1)[0].strip() if "|" in top else top.split("\n", 1)[0].strip()
    return (head[:20] + "…") if len(head) > 20 else (head or "知识片段")
