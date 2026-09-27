"""
RAG 综合评测运行器 —— 一条命令产出可进 PPT/演示视频的硬证据。

产出指标：
  · 准确率           Σ命中 / 题数            （事实正确性）
  · 有效回答率        正确 ∩ 首句延迟≤阈值     （又对又快，合并准确率+延迟两条红线）
  · 首句/整段延迟     p50 / p95               （数字人「开口时刻」才是感知延迟）
  · 景点覆盖率        被考查景点 / 总景点      （由构造保证 100%，证明面面俱到）
  · 拒答纠错率        陷阱题应对正确 / 陷阱题数 （证明不幻觉、可信赖）
  · 消融对比          有RAG vs 无RAG 准确率    （证明 RAG 真在干活，不是模型本来就会）

运行：
    cd /home/jiale/Desktop/Digital_Person
    .venv/bin/python tests/eval_run.py                  # 全量（~105正常题×2 + 15陷阱，约20-30min）
    .venv/bin/python tests/eval_run.py --scenic xihu    # 只测某景区（快速验证）
    .venv/bin/python tests/eval_run.py --limit 8        # 每景区限8题（冒烟）
    .venv/bin/python tests/eval_run.py --no-ablation    # 跳过无RAG对照（省一半时间）
    .venv/bin/python tests/eval_run.py --threshold 3.0  # 有效回答率的首句延迟阈值（秒）

产物：
    tests/eval_report.json   完整逐题明细（供人工复核 / 答辩取证）
    tests/eval_overview.png  一张总览图（直接进 PPT 和演示视频）
"""

import os, sys, json, time, argparse, asyncio, statistics
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
for _v in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
    os.environ.pop(_v, None)
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
sys.path.insert(0, str(ROOT))

from tests.eval_kb import (
    build_coverage_questions, build_curated_questions, coverage_report,
    TRAP_CASES, REFUSE_MARKERS, SCENIC_ZH,
)
from backend.rag import pipeline


# ── 评测期间禁用答案缓存：每题都要真实冷测（否则消融第二轮会命中第一轮缓存）──
pipeline.answer_cache.get = lambda *a, **k: None
pipeline.answer_cache.set = lambda *a, **k: None


def _hit(reply: str, keywords: list[str]) -> bool:
    """任一关键词命中即算正确（确定性、可肉眼核对）。"""
    return any(kw in reply for kw in keywords) if keywords else False


async def _ask_stream(q: str, scenic_id: str) -> dict:
    """跑一题流式问答，记录首句延迟 / 整段延迟 / 全文 / 意图。"""
    t0 = time.time()
    first_sentence_t = None
    intent = None
    full = ""
    async for ev in pipeline.answer_stream(q, scenic_id, session_id="eval"):
        if ev["type"] == "intent":
            intent = ev.get("value")
        elif ev["type"] == "sentence" and first_sentence_t is None:
            first_sentence_t = time.time() - t0
        elif ev["type"] == "end":
            full = ev["full_text"]
    total = time.time() - t0
    if first_sentence_t is None:
        first_sentence_t = total
    return {"reply": full, "first_latency": first_sentence_t,
            "total_latency": total, "intent": intent}


# ── 消融：把检索函数替换成返回空，模拟「无 RAG」（裸 LLM 凭参数记忆答）──
_orig_retrieve = pipeline.retrieve
_orig_retrieve_async = getattr(pipeline, "retrieve_async", None)


def _disable_rag():
    pipeline.retrieve = lambda *a, **k: []
    if _orig_retrieve_async:
        async def _empty(*a, **k):
            return []
        pipeline.retrieve_async = _empty


def _enable_rag():
    pipeline.retrieve = _orig_retrieve
    if _orig_retrieve_async:
        pipeline.retrieve_async = _orig_retrieve_async


def run_normal(questions, threshold, label="有RAG"):
    """跑正常题集，返回逐题结果 + 汇总。"""
    rows = []
    print(f"\n{'='*64}\n  {label}  正常题评测（{len(questions)} 题，有效阈值首句≤{threshold}s）\n{'='*64}")
    for i, q in enumerate(questions, 1):
        try:
            r = asyncio.run(_ask_stream(q["q"], q["scenic_id"]))
            hit = _hit(r["reply"], q["keywords"])
            valid = hit and r["first_latency"] <= threshold
            rows.append({**q, **r, "hit": hit, "valid": valid})
            mark = "✓" if hit else "✗"
            vmark = "⚡" if valid else " "
            print(f"  [{i:03d}] {mark}{vmark} 首句{r['first_latency']:.1f}s "
                  f"[{q['scenic_id']}/{q['dimension']}] {q['q'][:30]}")
            if not hit:
                print(f"        期望KW={q['keywords']}  答:{r['reply'][:60]}")
        except Exception as e:
            print(f"  [{i:03d}] ✗ ERROR {e}")
            rows.append({**q, "reply": f"ERROR:{e}", "hit": False, "valid": False,
                         "first_latency": 0, "total_latency": 0, "intent": None})
    return rows


def run_traps(traps):
    rows = []
    print(f"\n{'='*64}\n  陷阱题评测（{len(traps)} 题：拒答 / 纠错能力）\n{'='*64}")
    for i, t in enumerate(traps, 1):
        try:
            r = asyncio.run(_ask_stream(t["q"], t["scenic_id"]))
            reply = r["reply"]
            refused = any(m in reply for m in REFUSE_MARKERS)
            corrected = _hit(reply, t.get("correct_keywords", []))
            ok = refused or corrected
            rows.append({**t, "reply": reply, "refused": refused,
                         "corrected": corrected, "ok": ok,
                         "first_latency": r["first_latency"]})
            print(f"  [{i:02d}] {'✓' if ok else '✗'} [{t['kind']}] {t['q'][:32]}")
            if not ok:
                print(f"        答:{reply[:80]}")
        except Exception as e:
            print(f"  [{i:02d}] ✗ ERROR {e}")
            rows.append({**t, "reply": f"ERROR:{e}", "ok": False})
    return rows


def summarize(rows):
    n = len(rows)
    if n == 0:
        return {}
    hits = sum(r["hit"] for r in rows)
    valids = sum(r["valid"] for r in rows)
    firsts = [r["first_latency"] for r in rows if r.get("first_latency")]
    totals = [r["total_latency"] for r in rows if r.get("total_latency")]
    def pct(x): return round(x / n * 100, 1)
    def p(vals, q):
        if not vals: return 0.0
        vals = sorted(vals)
        k = max(0, min(len(vals) - 1, int(round(q * (len(vals) - 1)))))
        return round(vals[k], 2)
    # 各景区准确率
    by_scenic = {}
    for r in rows:
        d = by_scenic.setdefault(r["scenic_id"], [0, 0])
        d[0] += int(r["hit"]); d[1] += 1
    scenic_acc = {s: round(h / t * 100, 1) for s, (h, t) in by_scenic.items()}
    return {
        "n": n, "accuracy": pct(hits), "valid_rate": pct(valids),
        "first_p50": p(firsts, .5), "first_p95": p(firsts, .95),
        "total_p50": p(totals, .5), "total_p95": p(totals, .95),
        "scenic_accuracy": scenic_acc,
    }


def make_chart(report, out_png, threshold):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    # 直接按文件路径注册 CJK 字体，避免「按family名找不到」导致中文显示成方框
    for fp in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
               "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"):
        if Path(fp).exists():
            font_manager.fontManager.addfont(fp)
            plt.rcParams["font.sans-serif"] = [font_manager.FontProperties(fname=fp).get_name()]
            break
    plt.rcParams["axes.unicode_minus"] = False

    main = report["rag"]; ablt = report.get("ablation"); trap = report["trap"]
    cov = report["coverage"]["_overall"]["rate"]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle("景区导览 RAG 数字人 · 问答质量综合评测", fontsize=16, fontweight="bold")

    # 1) 核心指标
    ax = axes[0, 0]
    labels = ["准确率", f"有效回答率\n(正确∩首句≤{threshold}s)", "拒答纠错率", "景点覆盖率"]
    vals = [main["accuracy"], main["valid_rate"], trap["rate"], cov]
    bars = ax.bar(labels, vals, color=["#2E86DE", "#27AE60", "#E67E22", "#8E44AD"])
    ax.axhline(90, ls="--", c="red", lw=1.2); ax.text(3.4, 91, "90%红线", color="red", fontsize=9)
    ax.set_ylim(0, 105); ax.set_ylabel("%"); ax.set_title("核心指标")
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+1, f"{v}%", ha="center", fontsize=10, fontweight="bold")

    # 2) 消融对比
    ax = axes[0, 1]
    if ablt:
        bars = ax.bar(["无 RAG\n(裸LLM)", "有 RAG\n(本系统)"], [ablt["accuracy"], main["accuracy"]],
                      color=["#BDC3C7", "#2E86DE"])
        ax.set_ylim(0, 105); ax.set_ylabel("准确率 %"); ax.set_title("消融实验：RAG 的贡献")
        for b, v in zip(bars, [ablt["accuracy"], main["accuracy"]]):
            ax.text(b.get_x()+b.get_width()/2, v+1, f"{v}%", ha="center", fontsize=11, fontweight="bold")
        gain = round(main["accuracy"] - ablt["accuracy"], 1)
        ax.text(0.5, 50, f"+{gain}%\nRAG净增益", ha="center", color="#C0392B", fontsize=13, fontweight="bold")
    else:
        ax.text(0.5, 0.5, "（已跳过消融对比）", ha="center", va="center"); ax.axis("off")

    # 3) 延迟
    ax = axes[1, 0]
    labels = ["首句 p50", "首句 p95", "整段 p50", "整段 p95"]
    vals = [main["first_p50"], main["first_p95"], main["total_p50"], main["total_p95"]]
    bars = ax.bar(labels, vals, color=["#27AE60", "#52BE80", "#5DADE2", "#85C1E9"])
    ax.axhline(5, ls="--", c="red", lw=1.2); ax.text(3.3, 5.1, "5s红线", color="red", fontsize=9)
    ax.axhline(threshold, ls=":", c="#E67E22", lw=1.2)
    ax.set_ylabel("秒"); ax.set_title("响应延迟（首句=数字人开口时刻）")
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+0.05, f"{v}s", ha="center", fontsize=10, fontweight="bold")

    # 4) 各景区准确率
    ax = axes[1, 1]
    sa = main["scenic_accuracy"]
    names = [SCENIC_ZH.get(s, s) for s in sa]
    vals = list(sa.values())
    bars = ax.bar(names, vals, color="#16A085")
    ax.axhline(90, ls="--", c="red", lw=1.2)
    ax.set_ylim(0, 105); ax.set_ylabel("准确率 %"); ax.set_title("各景区准确率（插拔式知识库泛化）")
    for b, v in zip(bars, vals):
        ax.text(b.get_x()+b.get_width()/2, v+1, f"{v}%", ha="center", fontsize=9, fontweight="bold")

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_png, dpi=140)
    print(f"\n总览图已保存: {out_png}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenic", nargs="*", help="只测指定景区")
    ap.add_argument("--limit", type=int, default=0, help="每景区最多题数（冒烟用）")
    ap.add_argument("--threshold", type=float, default=3.0, help="有效回答率的首句延迟阈值(秒)")
    ap.add_argument("--no-ablation", action="store_true", help="跳过无RAG对照")
    ap.add_argument("--no-trap", action="store_true", help="跳过陷阱题")
    args = ap.parse_args()

    questions = build_coverage_questions() + build_curated_questions()
    traps = TRAP_CASES
    if args.scenic:
        questions = [q for q in questions if q["scenic_id"] in args.scenic]
        traps = [t for t in traps if t["scenic_id"] in args.scenic]
    if args.limit:
        per = {}
        kept = []
        for q in questions:
            c = per.get(q["scenic_id"], 0)
            if c < args.limit:
                kept.append(q); per[q["scenic_id"]] = c + 1
        questions = kept

    # 预热：首次调用要加载 BGE-M3 + Reranker 模型（冷启动 ~10s），生产环境服务常驻是热的，
    # 这一刀不计入延迟统计，否则 p95 被冷启动污染、不代表真实体验。
    if questions:
        print("预热中（加载嵌入/重排模型，不计时）...")
        try:
            asyncio.run(_ask_stream(questions[0]["q"], questions[0]["scenic_id"]))
        except Exception as e:
            print(f"  预热异常（忽略）: {e}")

    t_start = time.time()
    rag_rows = run_normal(questions, args.threshold, "有RAG")
    rag_sum = summarize(rag_rows)

    abl_sum = None
    abl_rows = []
    if not args.no_ablation:
        _disable_rag()
        abl_rows = run_normal(questions, args.threshold, "无RAG(消融)")
        abl_sum = summarize(abl_rows)
        _enable_rag()

    trap_rows = []
    trap_sum = {"rate": 0.0, "n": 0}
    if not args.no_trap:
        trap_rows = run_traps(traps)
        ok = sum(r["ok"] for r in trap_rows)
        trap_sum = {"rate": round(ok / len(trap_rows) * 100, 1) if trap_rows else 0.0,
                    "n": len(trap_rows), "ok": ok}

    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t_start, 1),
        "threshold_s": args.threshold,
        "coverage": coverage_report(),
        "rag": rag_sum, "ablation": abl_sum, "trap": trap_sum,
        "detail": {"rag": rag_rows, "ablation": abl_rows, "trap": trap_rows},
    }

    # ── 终端汇总 ──
    print(f"\n{'#'*64}\n  综合评测结果\n{'#'*64}")
    print(f"  景点覆盖率   : {report['coverage']['_overall']['rate']}%  "
          f"({report['coverage']['_overall']['covered']}/{report['coverage']['_overall']['total_attractions']} 景点)")
    print(f"  准确率       : {rag_sum['accuracy']}%   ({rag_sum['n']} 题)")
    print(f"  有效回答率   : {rag_sum['valid_rate']}%   (正确且首句≤{args.threshold}s)")
    print(f"  首句延迟     : p50={rag_sum['first_p50']}s  p95={rag_sum['first_p95']}s")
    print(f"  整段延迟     : p50={rag_sum['total_p50']}s  p95={rag_sum['total_p95']}s")
    if abl_sum:
        print(f"  消融对比     : 无RAG={abl_sum['accuracy']}%  →  有RAG={rag_sum['accuracy']}%  "
              f"(+{round(rag_sum['accuracy']-abl_sum['accuracy'],1)}%)")
    if trap_rows:
        print(f"  拒答纠错率   : {trap_sum['rate']}%   ({trap_sum['ok']}/{trap_sum['n']} 陷阱题)")
    print(f"  各景区准确率 : {rag_sum['scenic_accuracy']}")
    print(f"  总耗时       : {report['elapsed_sec']}s")

    out_json = ROOT / "tests" / "eval_report.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n详细报告已保存: {out_json}")
    make_chart(report, ROOT / "tests" / "eval_overview.png", args.threshold)


if __name__ == "__main__":
    main()
