"""首句延迟测试：打桥接 /live/ask_stream，测「请求→第一句下发」墙钟(=数字人开口时刻)。"""
import time, json, statistics
import httpx

QS = [
    ("灵山大佛有多高", "qa"),
    ("梵宫有什么特色", "qa"),
    ("帮我推荐半天游览路线", "route"),
    ("带孩子适合怎么玩", "recommend"),
    ("九龙灌浴表演什么时候", "qa"),
]

def ttfs(q):
    t0 = time.time()
    first = None
    fsms = None
    with httpx.stream("POST", "http://127.0.0.1:6006/live/ask_stream",
                      json={"sessionid": "0", "message": q, "scenic_id": "lingshan"},
                      timeout=60, trust_env=False) as r:
        for line in r.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            try:
                evt = json.loads(line[5:].strip())
            except Exception:
                continue
            if evt.get("type") == "sentence" and first is None:
                first = time.time() - t0
            if "first_sentence_ms" in evt and fsms is None:
                fsms = evt["first_sentence_ms"]
            if evt.get("type") in ("done", "end"):
                break
    return first, fsms

# 预热一次
ttfs("你好")
print("query                    TTFS(墙钟)  first_sentence_ms")
firsts = []
for q, kind in QS:
    for run in (1, 2):
        f, ms = ttfs(q)
        if f: firsts.append(f)
        print(f"  [{kind:9}] {q[:12]:14} run{run}: {f:.2f}s   {ms}")
print(f"\n首句墙钟延迟(纯RAG+TTS首音, 不含ASR/网络): 中位 {statistics.median(firsts):.2f}s | 均值 {sum(firsts)/len(firsts):.2f}s | max {max(firsts):.2f}s")
