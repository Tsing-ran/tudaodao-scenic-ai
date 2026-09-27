"""HTTP 准确率测试器：打已在跑的 RAG 服务（本地 14B），复用 test_accuracy 题库+判分。"""
import sys, time, importlib.util, statistics
import httpx

spec = importlib.util.spec_from_file_location("ta", "str(__import__('pathlib').Path(__file__).resolve().parent / 'test_accuracy.py')")
ta = importlib.util.module_from_spec(spec); spec.loader.exec_module(ta)
TEST_CASES, check = ta.TEST_CASES, ta.check_keywords

def ask(q, sid):
    r = httpx.post("__import__('os').environ.get('RAG_BASE','http://127.0.0.1:8000')/chat",
                   json={"session_id": "acc", "message": q, "scenic_id": sid},
                   timeout=120, trust_env=False)
    return r.json().get("reply", "")

scenics = sys.argv[1:] or list(TEST_CASES.keys())
grand_hit = grand_tot = 0
times = []
for sid in scenics:
    cases = TEST_CASES.get(sid) or []
    hits = 0
    print(f"\n=== {sid} ({len(cases)}题) ===")
    for i, tc in enumerate(cases, 1):
        t0 = time.time()
        try:
            reply = ask(tc["q"], sid)
        except Exception as e:
            reply = f"[ERR {e}]"
        el = time.time() - t0
        times.append(el)
        hit = check(reply, tc["keywords"])
        hits += int(hit)
        print(f"  [{i:02d}] {'OK ' if hit else 'MISS'} ({el:.1f}s) {tc['q'][:28]}")
        if not hit:
            print(f"       want{tc['keywords']} got: {reply[:90]}")
    print(f"  >>> {sid}: {hits}/{len(cases)} = {hits/len(cases)*100:.1f}%")
    grand_hit += hits; grand_tot += len(cases)

print(f"\n{'='*50}")
print(f"总命中: {grand_hit}/{grand_tot} = {grand_hit/grand_tot*100:.1f}%   ({'>=90 通过' if grand_hit/grand_tot>=0.9 else '未达标'})")
print(f"全句生成延迟: 中位 {statistics.median(times):.1f}s | 均值 {sum(times)/len(times):.1f}s | max {max(times):.1f}s")
