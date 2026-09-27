"""
准确率测试：验证 RAG 问答在各景区的准确率 ≥ 90%。

运行方式：
    cd /home/jiale/Desktop/Digital_Person
    python tests/test_accuracy.py                     # 测试全部景区
    python tests/test_accuracy.py lingshan            # 只测灵山
    python tests/test_accuracy.py lingshan xihu       # 测多个景区

评分标准（人工打分时参考）：
    2 分 = 完全正确（关键数字/事实无误，覆盖核心信息）
    1 分 = 部分正确（主要意思对但有遗漏或不精确）
    0 分 = 错误/胡编（关键信息错误或与知识库矛盾）

准确率 = 得分总和 / (题目数 × 2) × 100%
合格线 = 90%
"""

import os, sys, json, time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
for _v in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
    os.environ.pop(_v, None)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ══════════════════════════════════════════════════════════════════════
# 测试题库
# ══════════════════════════════════════════════════════════════════════

TEST_CASES = {

# ─── 灵山胜境（20 题）─────────────────────────────────────────────────
"lingshan": [
    # 核心景点
    {"q": "灵山大佛有多高？",
     "keywords": ["88", "米"], "ref": "88米（连底座总高约101.5米）"},

    {"q": "灵山胜境位于哪个城市？",
     "keywords": ["无锡", "江苏"], "ref": "无锡市滨湖区"},

    {"q": "梵宫是什么建筑，有什么特色？",
     "keywords": ["梵宫", "佛教"], "ref": "灵山梵宫是综合性佛教文化建筑，面积7.2万平方米，融合多种宗教艺术"},

    {"q": "九龙灌浴的表演时间是什么时候？",
     "keywords": ["九龙灌浴", "时间", "表演"], "ref": "每天多场，具体时间见景区公告（约9:00/11:00/14:00/16:00等）"},

    {"q": "拈花湾与灵山胜境是什么关系？",
     "keywords": ["拈花湾", "禅意", "配套"], "ref": "拈花湾是灵山胜境配套的禅意小镇，两者相邻可一起游览"},

    # 历史文化
    {"q": "灵山大佛建于哪一年？",
     "keywords": ["1997", "1994"], "ref": "1994年开工，1997年建成开放"},

    {"q": "灵山胜境主要体现哪种宗教文化？",
     "keywords": ["佛教"], "ref": "佛教文化，以佛教主题景观为核心"},

    {"q": "灵山大佛是什么材质建造的？",
     "keywords": ["青铜", "铜"], "ref": "青铜铸造"},

    {"q": "五印坛城是什么，来自哪个佛教传统？",
     "keywords": ["坛城", "藏传", "藏族"], "ref": "五印坛城是藏传佛教的宗教建筑"},

    {"q": "请介绍一下灵山胜境的地理位置。",
     "keywords": ["太湖", "无锡", "马山"], "ref": "位于无锡马山半岛，毗邻太湖"},

    # 实用信息
    {"q": "灵山胜境的门票价格大概是多少？",
     "keywords": ["门票", "元"], "ref": "成人票约210-230元（旺季）"},

    {"q": "去灵山胜境如何乘坐公共交通？",
     "keywords": ["公交", "地铁", "马山"], "ref": "可乘公交或自驾至马山景区"},

    {"q": "灵山胜境全年最佳游览季节是什么？",
     "keywords": ["春", "秋", "四月", "季节"], "ref": "春秋两季最佳，四月花期和九月重阳前后"},

    {"q": "小灵山有哪些可以参观的内容？",
     "keywords": ["小灵山", "寺庙", "古迹"], "ref": "小灵山上有古寺庙遗址和自然风光"},

    {"q": "灵山胜境有哪些适合家庭亲子的游览路线？",
     "keywords": ["亲子", "路线", "景点"], "ref": "梵宫、九龙灌浴、大佛广场等，全程约半天"},

    # 景点细节
    {"q": "祥符禅寺在灵山的历史地位是什么？",
     "keywords": ["祥符禅寺", "禅寺", "历史"], "ref": "祥符禅寺是灵山最古老的寺庙之一，有千年历史"},

    {"q": "灵山胜境内的音乐喷泉表演在哪里举行？",
     "keywords": ["喷泉", "大佛广场", "音乐"], "ref": "大佛广场（五智门前）有大型音乐喷泉表演"},

    {"q": "参观梵宫内部需要额外购票吗？",
     "keywords": ["梵宫", "门票", "免费", "购票"], "ref": "梵宫内部参观需在大门票之上另购票"},

    {"q": "灵山胜境景区面积大约是多少？",
     "keywords": ["面积", "平方", "公顷"], "ref": "核心景区约1平方千米，连同拈花湾共约20平方千米"},

    {"q": "在灵山胜境可以参与哪些佛教体验活动？",
     "keywords": ["礼佛", "祈福", "香", "体验"], "ref": "可进行礼佛祈福、撞钟、上香等宗教体验活动"},
],

# ─── 西湖（8 题）─────────────────────────────────────────────────────
"xihu": [
    {"q": "西湖在哪个城市，湖面面积有多大？",
     "keywords": ["杭州", "6.39", "平方千米"], "ref": "杭州，面积约6.39平方千米"},

    {"q": "断桥残雪景名是怎么来的？",
     "keywords": ["雪", "断", "断桥"], "ref": "雪后初晴，桥上积雪融化，远望若断若续，故名断桥残雪"},

    {"q": "苏堤是谁修建的，全长多少米？",
     "keywords": ["苏轼", "苏东坡", "2797"], "ref": "北宋苏轼主持疏浚西湖时以湖泥堆筑，全长2797米"},

    {"q": "西湖三潭印月的标志图案印在哪里？",
     "keywords": ["一元", "硬币", "人民币"], "ref": "印于人民币一元硬币背面"},

    {"q": "去西湖的门票价格是多少？",
     "keywords": ["免费", "西湖环湖", "免"], "ref": "西湖环湖及苏堤、白堤均免费开放"},

    {"q": "西湖何时被列入世界文化遗产？",
     "keywords": ["2011", "世界文化遗产"], "ref": "2011年西湖文化景观列入世界文化遗产名录"},

    {"q": "曲院风荷公园里种了多少种荷花？",
     "keywords": ["200", "品种", "荷花"], "ref": "种植荷花品种逾200种"},

    {"q": "雷峰塔现在的塔有多高，是哪年重建的？",
     "keywords": ["71", "2002"], "ref": "现塔高71.679米，2002年重建"},
],

# ─── 黄山（8 题）─────────────────────────────────────────────────────
"huangshan": [
    {"q": "黄山最高峰是哪座峰，海拔多少米？",
     "keywords": ["莲花峰", "1864"], "ref": "莲花峰，海拔1864.8米"},

    {"q": "黄山以什么四绝著称？",
     "keywords": ["奇松", "怪石", "云海", "温泉"], "ref": "奇松、怪石、云海、温泉四绝"},

    {"q": "迎客松有多少年树龄，树高多少米？",
     "keywords": ["1300", "10.6", "树龄"], "ref": "树龄逾1300年，树高10.6米"},

    {"q": "黄山是哪年被列入世界遗产的？",
     "keywords": ["1990", "世界遗产"], "ref": "1990年列入世界文化与自然双重遗产"},

    {"q": "黄山旺季门票是多少钱？",
     "keywords": ["230", "旺季"], "ref": "旺季（3-11月）230元/人"},

    {"q": "西海大峡谷有多深，栈道有多长？",
     "keywords": ["600", "5千米", "5公里", "栈道"], "ref": "最深约600米，栈道总长约5千米"},

    {"q": "天都峰上的\"鲫鱼背\"是什么？",
     "keywords": ["鲫鱼背", "绝壁", "险", "1米"], "ref": "两侧万丈深渊、宽仅1米的绝壁脊背路段，为黄山第一险"},

    {"q": "黄山温泉的水温大约是多少度？",
     "keywords": ["42", "℃", "度"], "ref": "泉水温度约42℃，常年稳定"},
],

# ─── 故宫（8 题）─────────────────────────────────────────────────────
"gugong": [
    {"q": "故宫建于哪一年，历时多久建成？",
     "keywords": ["1406", "1420", "14年"], "ref": "1406年开工，1420年建成，历时14年"},

    {"q": "太和殿建筑面积有多大，高度是多少？",
     "keywords": ["2377", "26.92", "高"], "ref": "建筑面积2377平方米，高26.92米"},

    {"q": "故宫一共有多少间房屋？",
     "keywords": ["9000", "房屋", "间"], "ref": "共有大小房屋9000余间"},

    {"q": "乾清宫\"正大光明\"匾的背后藏着什么秘密？",
     "keywords": ["秘密立储", "皇太子", "立储"], "ref": "匾后藏存皇太子名单密函，即清代秘密立储制度"},

    {"q": "故宫博物院现藏有多少件文物？",
     "keywords": ["186万", "文物"], "ref": "现藏文物约186万件"},

    {"q": "故宫旺季和淡季的门票分别是多少钱？",
     "keywords": ["60", "40", "旺季", "淡季"], "ref": "旺季（4-10月）60元，淡季（11-3月）40元"},

    {"q": "养心殿在清朝有什么重要的政治意义？",
     "keywords": ["养心殿", "雍正", "政治", "理政", "垂帘"], "ref": "雍正起为清代政治中心，后有慈禧垂帘听政"},

    {"q": "故宫钟表馆的钟表整点演示每天几点举行？",
     "keywords": ["10:00", "14:00", "10点", "14点", "两点"], "ref": "每天10:00和14:00举行钟表整点演示"},
],

}


# ══════════════════════════════════════════════════════════════════════
# 测试运行器
# ══════════════════════════════════════════════════════════════════════

def check_keywords(reply: str, keywords: list[str]) -> bool:
    """自动检查关键词命中（辅助判断，最终以人工打分为准）。"""
    return any(kw in reply for kw in keywords)


def run_tests(scenic_ids: list[str]) -> dict:
    from backend.rag.pipeline import answer

    results = {}
    grand_total = grand_hit = 0

    for sid in scenic_ids:
        cases = TEST_CASES.get(sid)
        if not cases:
            print(f"⚠️  没有 {sid} 的测试题，跳过")
            continue

        print(f"\n{'='*60}")
        print(f"  景区: {sid}  （{len(cases)} 题）")
        print(f"{'='*60}")

        hits = 0
        scenic_results = []
        for i, tc in enumerate(cases, 1):
            t0 = time.time()
            try:
                res = answer(tc["q"], sid, session_id="accuracy_test")
                reply = res["reply"]
                elapsed = time.time() - t0
                hit = check_keywords(reply, tc["keywords"])
                hits += int(hit)
                mark = "✓" if hit else "✗"
                print(f"  [{i:02d}] {mark} ({elapsed:.1f}s) Q: {tc['q'][:40]}")
                if not hit:
                    print(f"       期望关键词: {tc['keywords']}")
                    print(f"       回答摘要: {reply[:100]}...")
                scenic_results.append({
                    "q": tc["q"], "ref": tc["ref"],
                    "reply": reply, "hit": hit, "elapsed": elapsed,
                })
            except Exception as e:
                print(f"  [{i:02d}] ✗ ERROR: {e}")
                scenic_results.append({"q": tc["q"], "error": str(e), "hit": False})

        rate = hits / len(cases) * 100
        status = "✅ 通过" if rate >= 90 else "❌ 未达标"
        print(f"\n  自动命中率: {hits}/{len(cases)} = {rate:.1f}%  {status}")
        print(f"  （注：自动判断仅供参考，人工打分更准确）")
        results[sid] = {"cases": scenic_results, "auto_rate": rate, "hits": hits, "total": len(cases)}
        grand_total += len(cases)
        grand_hit += hits

    if len(scenic_ids) > 1:
        overall = grand_hit / grand_total * 100
        print(f"\n{'='*60}")
        print(f"  综合自动命中率: {grand_hit}/{grand_total} = {overall:.1f}%")
        print(f"{'='*60}")

    return results


def save_report(results: dict, path: Path):
    """保存详细测试报告（JSON），供人工复核。"""
    report = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "scenic_results": results,
        "summary": {
            sid: {"auto_rate": v["auto_rate"], "hits": v["hits"], "total": v["total"]}
            for sid, v in results.items()
        },
    }
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n详细报告已保存: {path}")


if __name__ == "__main__":
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

    scenic_ids = sys.argv[1:] if len(sys.argv) > 1 else list(TEST_CASES.keys())
    unknown = [s for s in scenic_ids if s not in TEST_CASES]
    if unknown:
        print(f"未知景区: {unknown}")
        print(f"可用: {list(TEST_CASES.keys())}")
        sys.exit(1)

    print(f"开始准确率测试，景区: {scenic_ids}")
    results = run_tests(scenic_ids)

    report_path = Path(__file__).resolve().parent / "accuracy_report.json"
    save_report(results, report_path)
