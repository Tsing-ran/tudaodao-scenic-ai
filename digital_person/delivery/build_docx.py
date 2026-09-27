# -*- coding: utf-8 -*-
"""部署手册 Markdown → docx（可重复执行）。

用法：python delivery/build_docx.py

版式沿用设计文档的 docs/reference.docx（宋体小四正文 / 黑体标题 / A4 学长版式），
但那份参考样式是给设计文档做的、其规范明确「不放代码」，因此没有代码块样式。
本手册有代码块，若不管，Source Code 会继承正文的宋体 + 首行缩进 2 字符 +
1.5 倍行距 + 两端对齐——命令会被缩进和拉开的字距搞乱，评委照着敲容易出错。
故 pandoc 生成后在输出文件上补一次代码块排版（不改 docs/reference.docx 本身）。

截图取自 delivery/manual_images/（由 md 里的 ![](manual_images/x.png) 引用）。
这些图原本是手工插进 docx 的，本脚本会覆盖 docx —— 所以每次执行前先备份一份，
且执行后校验图片数量，缺一张就报错，避免「重建一次就把图冲掉」。
"""
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
MD = ROOT / "delivery" / "部署手册.md"
REF = ROOT / "docs" / "reference.docx"
IMG_DIR = ROOT / "delivery" / "manual_images"
OUT = ROOT / "作品源码" / "部署手册.docx"
TITLE = "景区导览服务 AI 数字人 · 部署手册"
EXPECT_IMAGES = 5


def backup_existing() -> None:
    if not OUT.exists():
        return
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = OUT.with_name(f"{OUT.stem}.bak_{stamp}{OUT.suffix}")
    shutil.copy2(OUT, bak)
    print("backup ->", bak.name)


def run_pandoc() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "pandoc", str(MD), "-o", str(OUT),
        f"--reference-doc={REF}",
        # 图片路径写的是相对 md 的，pandoc 默认按 CWD 找 → 显式给出资源目录
        f"--resource-path={MD.parent}",
        # markdown 里 # 是文档名、## 才是章；降一级让「章」成为真正的一级标题
        "--shift-heading-level-by=-1",
        "--toc", "--toc-depth=2",
        f"--metadata", f"title={TITLE}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        sys.exit(f"pandoc failed:\n{r.stderr}")
    print("pandoc ok ->", OUT)


def verify_images() -> None:
    """图丢了必须炸出来：静默少一张图，评委看到的就是缺图的手册。"""
    doc = Document(str(OUT))
    n = sum(1 for p in doc.paragraphs if "r:embed" in p._p.xml)
    if n != EXPECT_IMAGES:
        sys.exit(f"!! 图片数不对：期望 {EXPECT_IMAGES} 张，实际 {n} 张。"
                 f"检查 {IMG_DIR} 是否齐全、md 里的引用路径是否写错。")
    print(f"  images ok: {n} 张截图全部嵌入")


def style_by_name(doc, name):
    for s in doc.styles:
        if s.name == name:
            return s
    return None


def fix_code_style() -> None:
    doc = Document(str(OUT))

    st = style_by_name(doc, "Source Code")
    if st is None:
        print("  warn: no Source Code style in output, skipped")
        return

    rPr = st.element.get_or_add_rPr()
    rf = rPr.get_or_add_rFonts()
    rf.set(qn("w:ascii"), "Consolas")
    rf.set(qn("w:hAnsi"), "Consolas")
    rf.set(qn("w:eastAsia"), "宋体")   # 代码块内有中文注释，缺 CJK 字体会回落成方框
    st.font.size = Pt(10)
    st.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)

    pf = st.paragraph_format
    pf.first_line_indent = Pt(0)
    pf.left_indent = Pt(12)
    pf.line_spacing = 1.0
    pf.space_before = Pt(3)
    pf.space_after = Pt(3)
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT

    pPr = st.element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), "F4F4F4")
    pPr.append(shd)
    keep = OxmlElement("w:keepLines")
    keep.set(qn("w:val"), "1")
    pPr.append(keep)

    vc = style_by_name(doc, "Verbatim Char")   # 行内 `code`
    if vc is not None:
        vc.font.size = Pt(10.5)

    doc.save(str(OUT))
    print("  code style fixed: Consolas 10 / no indent / single spacing / left / F4F4F4")


if __name__ == "__main__":
    backup_existing()
    run_pandoc()
    fix_code_style()
    verify_images()
    print("done:", OUT)
