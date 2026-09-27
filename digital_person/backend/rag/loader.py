"""
文档加载与分块。

两种文档类型处理策略不同：
- 叙述性文档（游览指南）：按段落+滑动窗口分块，保留语义连贯性
- 结构化表格（景点数据集）：每行作为一个独立 chunk，保证字段完整
"""

from pathlib import Path
from typing import List
from docx import Document as DocxDocument


def _load_docx_paragraphs(path: Path) -> List[str]:
    doc = DocxDocument(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    # 提取表格内容
    for table in doc.tables:
        headers = [cell.text.strip() for cell in table.rows[0].cells]
        for row in table.rows[1:]:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                # 把每行拼成"字段名: 值"格式，方便语义检索
                row_text = " | ".join(
                    f"{h}: {v}" for h, v in zip(headers, cells) if v
                )
                paragraphs.append(row_text)
    return paragraphs


def chunk_paragraphs(
    paragraphs: List[str],
    chunk_size: int = 512,
    overlap: int = 128,
) -> List[str]:
    """把段落列表合并成目标 token 量的 chunk，相邻 chunk 有重叠。"""
    chunks: List[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) <= chunk_size:
            current = current + "\n" + para if current else para
        else:
            if current:
                chunks.append(current.strip())
            # 用上一个 chunk 的末尾作为重叠部分
            overlap_text = current[-overlap:] if len(current) > overlap else current
            current = overlap_text + "\n" + para if overlap_text else para
    if current.strip():
        chunks.append(current.strip())
    return chunks


def load_docx_as_chunks(
    path: Path,
    chunk_size: int = 512,
    overlap: int = 128,
) -> List[dict]:
    """加载 docx，返回 [{text, source}] 列表。"""
    paragraphs = _load_docx_paragraphs(path)
    chunks = chunk_paragraphs(paragraphs, chunk_size, overlap)
    return [{"text": c, "source": path.name} for c in chunks]


def _load_pdf_paragraphs(path: Path) -> List[str]:
    """逐页抽取 PDF 文本 → 段落。用 pymupdf(fitz)：中文/CID 字体抽取远胜 pypdf。
    无文本层的 PDF（扫描件/字体轮廓化）抽不出文字 → 返回空（上传仍登记，状态标 unsupported）。"""
    import fitz  # pymupdf
    paragraphs: List[str] = []
    with fitz.open(str(path)) as doc:
        for page in doc:
            for block in page.get_text().split("\n\n"):
                block = " ".join(block.split())  # 压平多余空白/换行
                if len(block.strip()) >= 2:
                    paragraphs.append(block.strip())
    return paragraphs


def _load_text_paragraphs(path: Path) -> List[str]:
    """txt/md：按空行切段落。"""
    raw = path.read_text(encoding="utf-8", errors="ignore")
    return [b.strip() for b in raw.split("\n\n") if b.strip()]


# 支持的上传文档格式 → 段落抽取器
SUPPORTED_SUFFIXES = {".docx", ".pdf", ".txt", ".md", ".markdown"}


def load_file_as_chunks(
    path: Path,
    chunk_size: int = 512,
    overlap: int = 128,
) -> List[dict]:
    """按后缀分派加载任意支持格式（docx/pdf/txt/md），返回 [{text, source}]。
    不支持的格式返回空列表（上传仍登记、只是不入 RAG）。"""
    suffix = path.suffix.lower()
    if suffix == ".docx":
        paragraphs = _load_docx_paragraphs(path)
    elif suffix == ".pdf":
        paragraphs = _load_pdf_paragraphs(path)
    elif suffix in (".txt", ".md", ".markdown"):
        paragraphs = _load_text_paragraphs(path)
    else:
        return []
    chunks = chunk_paragraphs(paragraphs, chunk_size, overlap)
    return [{"text": c, "source": path.name} for c in chunks]
