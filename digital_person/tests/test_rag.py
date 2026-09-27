"""
手动测试 RAG 问答质量。
运行前必须先执行 scripts/ingest_lingshan.py。

运行方式：
    cd /home/jiale/Desktop/Digital_Person
    python tests/test_rag.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.rag.pipeline import answer

TEST_QUESTIONS = [
    "灵山大佛有多高？",
    "九龙灌浴每天几点有表演？",
    "适合带孩子的游览路线是什么？",
    "灵山梵宫是什么风格的建筑？",
    "从南门进去第一个看到的景点是什么？",
]

if __name__ == "__main__":
    for q in TEST_QUESTIONS:
        print(f"\n问：{q}")
        result = answer(q, scenic_id="lingshan")
        print(f"答：{result['reply']}")
        print(f"   [来源: {result['sources']} | 用了知识库: {result['context_used']}]")
        print("-" * 60)
