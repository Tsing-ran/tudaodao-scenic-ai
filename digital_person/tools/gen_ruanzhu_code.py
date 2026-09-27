"""
软著·源程序鉴别材料生成器。

规范（中国版权保护中心）：
  - 每页 50 行，A4
  - 总页数 >60 时交「前 30 页 + 后 30 页」；≤60 页全交
  - 首页应从软件主入口开始；每页页眉含 软件名称+版本号+页码
  - 惯例：剔除空行，保证每页都是实质代码

文件顺序刻意安排：main.py（入口）→ EA-RAG 检索器（核心创新，确保落在前30页内）
→ RAG 流水线 → 多智能体 → 其余模块 → 桥接层 → 评测脚本。

用法：.venv/bin/python tools/gen_ruanzhu_code.py
产物：docs/软著申请材料/源程序鉴别材料.pdf （另打印总行数=申请表「源程序量」）
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "软著申请材料"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SOFTWARE_NAME = "基于实体锚定自适应检索增强(EA-RAG)的景区导览AI数字人系统"
VERSION = "V1.0"

LINES_PER_PAGE = 50
MAX_UNITS = 110         # 折行宽度（显示单位：ASCII=1，中文=2）
FRONT_PAGES = 30
BACK_PAGES = 30


def _units(s: str) -> int:
    return sum(2 if ord(c) > 0x2E7F else 1 for c in s)


def _wrap(ln: str, max_units: int) -> list[str]:
    """按显示宽度折行（中文按2单位计），避免 CJK 行超出页宽。"""
    out = []
    while _units(ln) > max_units:
        acc, cut = 0, 0
        for i, c in enumerate(ln):
            acc += 2 if ord(c) > 0x2E7F else 1
            if acc > max_units:
                cut = i
                break
        out.append(ln[:cut])
        ln = "    " + ln[cut:]
    out.append(ln)
    return out

# 源码文件顺序（入口在前，EA-RAG 紧随其后保证落在前30页）
SOURCE_ORDER = [
    "backend/main.py",
    "backend/rag/retriever.py",      # ← EA-RAG 核心
    "backend/rag/pipeline.py",
    "backend/rag/indexer.py",
    "backend/rag/loader.py",
    "backend/rag/embedder.py",
    "backend/rag/embedder_dashscope.py",
    "backend/rag/cache.py",
    "backend/rag/streaming.py",
    "backend/agent/orchestrator.py",
    "backend/agent/intents.py",
    "backend/agent/handlers.py",
    "backend/llm/prompts.py",
    "backend/llm/client.py",
    "backend/llm/multimodal.py",
    "backend/api/chat.py",
    "backend/api/knowledge.py",
    "backend/api/multimodal.py",
    "backend/api/analytics.py",
    "backend/api/trip.py",
    "backend/api/digital_human.py",
    "backend/api/asr.py",
    "backend/analytics/crowd.py",
    "backend/analytics/env_context.py",
    "backend/asr/transcriber.py",
    "backend/db/database.py",
    "backend/core/config.py",
    "bridge/server.py",
    "tests/eval_kb.py",
    "tests/eval_run.py",
    "tests/eval_ea_rag.py",
]


def _setup_font():
    for fp in ("/usr/share/fonts/opentype/noto/NotoSansMonoCJKsc-Regular.otf",
               "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"):
        if Path(fp).exists():
            font_manager.fontManager.addfont(fp)
            name = font_manager.FontProperties(fname=fp).get_name()
            plt.rcParams["font.sans-serif"] = [name]
            plt.rcParams["font.family"] = "sans-serif"
            return
    raise RuntimeError("未找到中文字体")


def collect_lines() -> tuple[list[str], int]:
    """汇总源码：剔除空行、折行超长行。返回 (展示行列表, 原始总行数)。"""
    display, raw_total = [], 0
    for rel in SOURCE_ORDER:
        f = ROOT / rel
        if not f.exists():
            print(f"  ⚠ 跳过不存在: {rel}")
            continue
        text = f.read_text(encoding="utf-8")
        raw = text.splitlines()
        raw_total += len(raw)
        display.append(f"==================== {rel} ====================")
        for ln in raw:
            ln = ln.rstrip()
            if not ln.strip():
                continue                       # 软著惯例剔除空行
            display.extend(_wrap(ln, MAX_UNITS))
    return display, raw_total


def paginate(lines: list[str]) -> list[list[str]]:
    return [lines[i:i + LINES_PER_PAGE] for i in range(0, len(lines), LINES_PER_PAGE)]


def render(pages: list[list[str]], selected: list[int], out_pdf: Path):
    """按选定页码渲染 PDF。页眉=软件名+版本+全局页码（保留原页码体现前后30页）。"""
    with PdfPages(out_pdf) as pdf:
        for pno in selected:
            fig = plt.figure(figsize=(8.27, 11.69))   # A4
            fig.text(0.05, 0.975, f"{SOFTWARE_NAME} {VERSION}", fontsize=7.5)
            fig.text(0.95, 0.975, f"第 {pno + 1} 页", fontsize=7.5, ha="right")
            fig.lines.append(plt.Line2D([0.05, 0.95], [0.968, 0.968],
                                        transform=fig.transFigure, lw=0.5, color="#888888"))
            body = "\n".join(pages[pno])
            fig.text(0.05, 0.952, body, fontsize=8.6, va="top", family="sans-serif",
                     linespacing=1.78)
            pdf.savefig(fig)
            plt.close(fig)


def main():
    _setup_font()
    lines, raw_total = collect_lines()
    pages = paginate(lines)
    n = len(pages)
    if n > FRONT_PAGES + BACK_PAGES:
        selected = list(range(FRONT_PAGES)) + list(range(n - BACK_PAGES, n))
        mode = f"前{FRONT_PAGES}页 + 后{BACK_PAGES}页（共{n}页）"
    else:
        selected = list(range(n))
        mode = f"全部 {n} 页（≤60页）"
    out = OUT_DIR / "源程序鉴别材料.pdf"
    render(pages, selected, out)
    print(f"源程序总行数（申请表「源程序量」填这个）: {raw_total}")
    print(f"排版后实质行数: {len(lines)}  总页数: {n}  提交方式: {mode}")
    print(f"产物: {out}")


if __name__ == "__main__":
    main()
