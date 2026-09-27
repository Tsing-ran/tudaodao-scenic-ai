"""
EA-RAG 消融实验：检索级 A/B 对比（不调 LLM，快、便宜、指标纯净）。

为什么测"检索级"而非端到端：EA-RAG 改的是检索编排层，直接度量
「正确事实是否被召回进 top-k chunk」最能隔离算法本身的贡献——
召回对了，LLM 几乎必答对（端到端105题已另行验证）。

指标：
  · 召回命中率 Recall@k —— 任一期望关键词出现在返回的 top-k chunk 中
  · 误拒率 False-Refusal —— 正常题被门控误判为"无信息"的比例（应≈0）
  · 拒答率 Refusal@OOK   —— 知识库外陷阱题被正确判空的比例（越高越好）

消融配置（逐机制叠加）：
  baseline   全关（原始拼接去重行为）
  +anchor    仅实体锚定
  +fusion    仅自适应融合
  EA-RAG     全开（含门控）

运行：
    .venv/bin/python tests/eval_ea_rag.py            # 全量消融
    .venv/bin/python tests/eval_ea_rag.py --quick    # 只跑对抗集（快速验证）
"""

import os, sys, json, time, argparse
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
for _v in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
    os.environ.pop(_v, None)
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
sys.path.insert(0, str(ROOT))

from tests.eval_kb import (
    build_coverage_questions, build_curated_questions,
    ADVERSARIAL_CASES, TRAP_CASES,
)
from backend.core.config import settings
from backend.rag.retriever import retrieve

CONFIGS = [
    # (名称, entity_anchor, adaptive_fusion, confidence_gate)
    ("baseline", False, False, False),
    ("+anchor",  True,  False, False),
    ("+fusion",  False, True,  False),
    ("EA-RAG",   True,  True,  True),
]


def _apply(anchor: bool, fusion: bool, gate: bool):
    settings.ea_entity_anchor = anchor
    settings.ea_adaptive_fusion = fusion
    settings.ea_confidence_gate = gate


def _recall_hit(chunks: list[str], keywords: list[str]) -> bool:
    """任一关键词出现在任一召回 chunk 中即算召回命中。"""
    text = "\n".join(chunks)
    return any(kw in text for kw in keywords)


def run_config(name: str, normal: list[dict], adv: list[dict], ook: list[dict]) -> dict:
    """跑一个配置：正常题 + 对抗题召回率，正常题误拒率，知识库外拒答率。"""
    n_hit = n_refused = 0
    for q in normal:
        chunks = retrieve(q["q"], q["scenic_id"])
        if not chunks:
            n_refused += 1
        elif _recall_hit(chunks, q["keywords"]):
            n_hit += 1

    a_hit = 0
    adv_miss = []
    for q in adv:
        chunks = retrieve(q["q"], q["scenic_id"])
        if chunks and _recall_hit(chunks, q["keywords"]):
            a_hit += 1
        else:
            adv_miss.append(q["target"])

    o_refused = 0
    for t in ook:
        chunks = retrieve(t["q"], t["scenic_id"])
        if not chunks:
            o_refused += 1

    r = {
        "normal_recall": round(n_hit / len(normal) * 100, 1) if normal else 0,
        "false_refusal": round(n_refused / len(normal) * 100, 1) if normal else 0,
        "adv_recall": round(a_hit / len(adv) * 100, 1) if adv else 0,
        "ook_refusal": round(o_refused / len(ook) * 100, 1) if ook else 0,
        "adv_miss": adv_miss,
    }
    print(f"  {name:<10} 正常召回 {r['normal_recall']:>5}%   对抗召回 {r['adv_recall']:>5}%   "
          f"误拒 {r['false_refusal']:>4}%   库外拒答 {r['ook_refusal']:>5}%")
    if adv_miss:
        print(f"  {'':<10} 对抗漏检: {adv_miss}")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="只跑对抗集")
    args = ap.parse_args()

    normal = [] if args.quick else build_coverage_questions() + build_curated_questions()
    adv = ADVERSARIAL_CASES
    ook = [t for t in TRAP_CASES if t["kind"] == "out_of_kb"]

    print(f"题量：正常 {len(normal)} / 对抗 {len(adv)} / 知识库外 {len(ook)}")
    print("预热（加载嵌入与重排模型）...")
    _apply(False, False, False)
    retrieve("预热", "lingshan")

    results = {}
    t0 = time.time()
    print(f"\n{'='*84}")
    for name, anchor, fusion, gate in CONFIGS:
        _apply(anchor, fusion, gate)
        results[name] = run_config(name, normal, adv, ook)
    print(f"{'='*84}")
    print(f"总耗时 {time.time()-t0:.0f}s")

    # 恢复默认全开
    _apply(True, True, True)

    out = ROOT / "tests" / "ea_rag_ablation.json"
    out.write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "n_normal": len(normal), "n_adv": len(adv), "n_ook": len(ook),
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"报告已保存: {out}")


if __name__ == "__main__":
    main()
