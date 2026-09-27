"""
软著·文档鉴别材料（设计说明书）生成器。

把已写好的设计文档章节（markdown）+ 全套架构图（PNG）拼装成一份
《设计说明书》PDF：文字按每页50行排版，图占整页插入对应位置。
页眉同源码材料：软件名+版本+页码。>60页时自动取前30+后30。

用法：.venv/bin/python tools/gen_ruanzhu_doc.py
产物：docs/软著申请材料/设计说明书鉴别材料.pdf
"""

import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib import font_manager
from matplotlib.backends.backend_pdf import PdfPages

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "docs" / "软著申请材料"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SOFTWARE_NAME = "基于实体锚定自适应检索增强(EA-RAG)的景区导览AI数字人系统"
VERSION = "V1.0"
LINES_PER_PAGE = 50
MAX_CHARS = 116          # 折行宽度（显示单位：ASCII=1，中文=2）
FRONT_PAGES, BACK_PAGES = 30, 30

D = ROOT / "docs" / "diagrams"
# 章节顺序：(markdown文件 | ("IMG", png路径, 图题))
CONTENT = [
    ROOT / "docs" / "项目背景.md",
    ("IMG", D / "07_用例图.png", "图 2-1 系统用例图"),
    ("IMG", D / "01_系统总体架构.png", "图 3-1 系统总体架构"),
    ("IMG", D / "02_部署架构.png", "图 3-2 部署架构"),
    ROOT / "docs" / "算法设计章节_RAG.md",
    ("IMG", D / "03_RAG全链路流程.png", "图 4-1 RAG 问答全链路流程"),
    ("IMG", D / "08_多智能体分派.png", "图 4-2 多智能体意图分派"),
    ("IMG", ROOT / "tests" / "eval_overview.png", "图 4-3 问答质量综合评测总览"),
    ("IMG", D / "06_数据库ER.png", "图 6-1 数据存储设计"),
    ("IMG", D / "04_SSE流式时序.png", "图 7-1 流式问答时序"),
    ("IMG", D / "05_数字人推流链路.png", "图 7-2 数字人推流链路"),
]


def _setup_font():
    fp = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    font_manager.fontManager.addfont(fp)
    plt.rcParams["font.sans-serif"] = [font_manager.FontProperties(fname=fp).get_name()]
    plt.rcParams["font.family"] = "sans-serif"


def md_to_lines(md: str) -> list[str]:
    """markdown → 纯文本行（轻量清洗：去标记符号，保留结构感）。"""
    out = []
    for ln in md.splitlines():
        ln = ln.rstrip()
        if not ln.strip():
            continue
        if ln.strip().startswith(("```", "$$")):
            continue
        ln = re.sub(r"^#{1,6}\s*", "", ln)            # 标题井号
        ln = ln.replace("**", "").replace("`", "")    # 加粗/代码标记
        ln = re.sub(r"^>\s?", "", ln)                 # 引用
        # 按显示宽度折行（中文按2单位计）
        def units(s): return sum(2 if ord(c) > 0x2E7F else 1 for c in s)
        while units(ln) > MAX_CHARS:
            acc, cut = 0, 0
            for i, c in enumerate(ln):
                acc += 2 if ord(c) > 0x2E7F else 1
                if acc > MAX_CHARS:
                    cut = i
                    break
            out.append(ln[:cut])
            ln = "  " + ln[cut:]
        out.append(ln)
    return out


def build_pages() -> list:
    """返回页列表：文本页=list[str]，图片页=("IMG", path, caption)。"""
    pages, buf = [], []

    def flush():
        nonlocal buf
        while buf:
            pages.append(buf[:LINES_PER_PAGE])
            buf = buf[LINES_PER_PAGE:]

    for item in CONTENT:
        if isinstance(item, tuple):
            flush()
            if item[1].exists():
                pages.append(item)
            else:
                print(f"  ⚠ 缺图跳过: {item[1].name}")
        else:
            buf += md_to_lines(item.read_text(encoding="utf-8"))
    flush()
    return pages


def render(pages: list, selected: list[int], out_pdf: Path):
    with PdfPages(out_pdf) as pdf:
        for pno in selected:
            page = pages[pno]
            fig = plt.figure(figsize=(8.27, 11.69))
            fig.text(0.05, 0.975, f"{SOFTWARE_NAME} {VERSION} · 设计说明书", fontsize=7.5)
            fig.text(0.95, 0.975, f"第 {pno + 1} 页", fontsize=7.5, ha="right")
            fig.lines.append(plt.Line2D([0.05, 0.95], [0.968, 0.968],
                                        transform=fig.transFigure, lw=0.5, color="#888888"))
            if isinstance(page, tuple):                      # 整页图
                _, path, caption = page
                img = mpimg.imread(str(path))
                ax = fig.add_axes([0.06, 0.10, 0.88, 0.82])
                ax.imshow(img)
                ax.axis("off")
                fig.text(0.5, 0.06, caption, fontsize=9, ha="center")
            else:                                            # 文本页
                fig.text(0.05, 0.952, "\n".join(page), fontsize=8.6,
                         va="top", linespacing=1.78)
            pdf.savefig(fig, dpi=150)
            plt.close(fig)


def main():
    _setup_font()
    pages = build_pages()
    n = len(pages)
    if n > FRONT_PAGES + BACK_PAGES:
        selected = list(range(FRONT_PAGES)) + list(range(n - BACK_PAGES, n))
        mode = f"前{FRONT_PAGES}页 + 后{BACK_PAGES}页（共{n}页）"
    else:
        selected = list(range(n))
        mode = f"全部 {n} 页（≤60页）"
    out = OUT_DIR / "设计说明书鉴别材料.pdf"
    render(pages, selected, out)
    print(f"总页数: {n}  提交方式: {mode}")
    print(f"产物: {out}")


if __name__ == "__main__":
    main()
