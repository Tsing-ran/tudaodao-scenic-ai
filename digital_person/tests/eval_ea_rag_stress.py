"""
EA-RAG 压力实验（消融的补充）：让机制差距在"难"条件下显形。

背景：常规消融中 anchor/fusion 召回均 100%——知识库小（每景区18~41 chunk），
top10+top10 候选近乎覆盖全库，召回天然饱和。本脚本制造两个"难"条件：

  实验A 候选预算压缩：dense/sparse top_k 10→3（模拟更大知识库 / 更低延迟预算下
        候选占库比骤降的场景），对比 baseline vs EA-RAG 的召回保持能力。
  实验B 门控阈值标定：gate 关，记录每题重排 top1 分 → 离线扫阈值，
        画出「库外拒答率 vs 正常误拒率」权衡曲线，选最优工作点。

运行：.venv/bin/python -u tests/eval_ea_rag_stress.py
产物：tests/ea_rag_stress.json
"""

import os, sys, json, time
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
from backend.rag import retriever
from backend.rag.retriever import retrieve


def _hit(chunks, keywords):
    text = "\n".join(chunks)
    return any(kw in text for kw in keywords)


def _apply(anchor, fusion, gate):
    settings.ea_entity_anchor = anchor
    settings.ea_adaptive_fusion = fusion
    settings.ea_confidence_gate = gate


def recall_on(questions):
    return sum(_hit(retrieve(q["q"], q["scenic_id"]), q["keywords"]) for q in questions)


def main():
    normal = build_coverage_questions() + build_curated_questions()
    adv = ADVERSARIAL_CASES
    ook = [t for t in TRAP_CASES if t["kind"] == "out_of_kb"]
    report = {"generated_at": time.strftime("%Y-%m-%d %H:%M:%S")}

    print("预热...")
    _apply(False, False, False)
    retrieve("预热", "lingshan")

    # ── 实验A：候选预算压缩 top_k 10→3 ─────────────────────────────
    print(f"\n=== 实验A 候选预算压缩（dense/sparse top_k = 3）===")
    orig_d, orig_s = settings.dense_top_k, settings.sparse_top_k
    settings.dense_top_k = settings.sparse_top_k = 3
    rows = {}
    for name, anchor, fusion in [("baseline", False, False), ("EA-RAG", True, True)]:
        _apply(anchor, fusion, False)
        n_hit = recall_on(normal)
        a_hit = recall_on(adv)
        rows[name] = {
            "normal_recall": round(n_hit / len(normal) * 100, 1),
            "adv_recall": round(a_hit / len(adv) * 100, 1),
        }
        print(f"  {name:<10} 正常召回 {rows[name]['normal_recall']}%   "
              f"对抗召回 {rows[name]['adv_recall']}%")
    settings.dense_top_k, settings.sparse_top_k = orig_d, orig_s
    report["budget_stress_k3"] = rows

    # ── 实验B：门控阈值标定（gate关，记录 top1 分，离线扫阈值）──────
    print(f"\n=== 实验B 门控阈值标定 ===")
    _apply(True, True, False)
    normal_scores, ook_scores = [], []
    for q in normal:
        retrieve(q["q"], q["scenic_id"])
        normal_scores.append(retriever.LAST_TOP1_SCORE)
    for t in ook:
        retrieve(t["q"], t["scenic_id"])
        ook_scores.append(retriever.LAST_TOP1_SCORE)

    curve = []
    print(f"  {'阈值':>6} {'库外拒答率':>10} {'正常误拒率':>10}")
    for th in [0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7]:
        ook_refuse = sum(s < th for s in ook_scores) / len(ook_scores) * 100
        false_refuse = sum(s < th for s in normal_scores) / len(normal_scores) * 100
        curve.append({"threshold": th, "ook_refusal": round(ook_refuse, 1),
                      "false_refusal": round(false_refuse, 1)})
        print(f"  {th:>6} {ook_refuse:>9.1f}% {false_refuse:>9.1f}%")
    report["gate_calibration"] = {
        "curve": curve,
        "normal_scores_min": round(min(normal_scores), 4),
        "ook_scores": [round(s, 4) for s in ook_scores],
    }

    _apply(True, True, True)
    out = ROOT / "tests" / "ea_rag_stress.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n报告: {out}")


if __name__ == "__main__":
    main()
