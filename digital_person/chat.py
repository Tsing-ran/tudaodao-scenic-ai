"""
命令行对话框，直接运行即可和灵山导游聊天。

运行方式：
    cd /home/jiale/Desktop/Digital_Person
    source .venv/bin/activate
    python chat.py
"""

import os
import sys

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
for _var in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy",
             "HTTP_PROXY", "http_proxy"):
    os.environ.pop(_var, None)

sys.path.insert(0, os.path.dirname(__file__))

from backend.rag.pipeline import answer

SCENIC_ID = "lingshan"
history = []

print("=" * 50)
print("  灵山胜境 AI 导游（输入 q 退出）")
print("=" * 50)

while True:
    try:
        user_input = input("\n你：").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n再见！")
        break

    if not user_input:
        continue
    if user_input.lower() in ("q", "quit", "exit", "退出"):
        print("导游：祝您游览愉快，再见！")
        break

    result = answer(user_input, scenic_id=SCENIC_ID, history=history)
    print(f"\n导游：{result['reply']}")

    # 保留对话历史（最近6轮，避免过长）
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": result["reply"]})
    history = history[-12:]
