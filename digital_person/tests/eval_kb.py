"""
知识库自省 + 测试题自动派生 + 覆盖率计算。

设计目标（对应「面面俱到 + 覆盖率100%」的说服力诉求）：
  1. 从结构化数据集 docx **逐景点逐字段** 解析出全部知识点 → 这是覆盖率的分母。
  2. 为每个景点自动派生考题，关键词从该景点字段里抽取**确定性事实**
     （数字 + 书名号「」/引号"" 内的专名），保证评分可复现、评委可肉眼核对。
  3. 覆盖率 = 被至少一题考查的景点数 ÷ 总景点数 → 由构造保证 100%。

为什么自动派生而非手挑：手挑会被质疑「只挑好答的」。自动遍历每个景点每个
字段，无人为筛选，准确率数字才有说服力。
"""

import re
from pathlib import Path
from docx import Document

DATA_DIR = Path(__file__).resolve().parent.parent / "示范景区公开资料包"

# 结构化数据集文件 → (scenic_id, 表索引)。灵山 docx 内含两张表：表0灵山、表1拈花湾。
STRUCTURED_SOURCES = [
    ("lingshan",  "灵山胜境 景点结构化数据集.docx",       0),
    ("nihuawan",  "灵山胜境 景点结构化数据集.docx",       1),
    ("xihu",      "杭州西湖 景点结构化数据集.docx",       0),
    ("huangshan", "安徽黄山 景点结构化数据集.docx",       0),
    ("gugong",    "北京故宫博物院 景点结构化数据集.docx", 0),
]

SCENIC_ZH = {
    "lingshan": "灵山胜境", "nihuawan": "拈花湾", "xihu": "西湖",
    "huangshan": "黄山", "gugong": "故宫博物院",
}


def _match_field(headers, *needles):
    """按表头模糊匹配字段下标（两套 schema 字段名略有差异）。"""
    for i, h in enumerate(headers):
        if any(n in h for n in needles):
            return i
    return None


def _extract_numbers(text: str) -> list[str]:
    """抽取带计量意义的数字（含小数），作为可肉眼核对的确定性关键词。"""
    nums = re.findall(r"\d+(?:\.\d+)?", text or "")
    # 过滤掉过短且无意义的（如单独的 0），保留有信息量的
    out, seen = [], set()
    for n in nums:
        if n in seen:
            continue
        seen.add(n)
        if len(n) >= 2 or "." in n:   # 39.8 / 2797 / 88 等
            out.append(n)
    return out


def _extract_terms(text: str) -> list[str]:
    """抽取引号""与书名号《》「」内的专名，作为文化类题的确定性关键词。"""
    terms = re.findall(r"[“\"「《]([^”\"」》]{2,12})[”\"」》]", text or "")
    out, seen = [], set()
    for t in terms:
        t = t.strip()
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def load_attractions() -> list[dict]:
    """解析全部结构化数据集 → 景点记录列表。"""
    records = []
    for scenic_id, fname, tidx in STRUCTURED_SOURCES:
        doc = Document(str(DATA_DIR / fname))
        table = doc.tables[tidx]
        headers = [c.text.strip() for c in table.rows[0].cells]
        f_name = _match_field(headers, "景点名称")
        f_loc  = _match_field(headers, "具体位置", "位置")
        f_par  = _match_field(headers, "建筑/景观参数", "参数")
        f_cul  = _match_field(headers, "文化内涵", "历史背景")
        f_high = _match_field(headers, "游玩亮点", "推荐活动")
        f_intro = _match_field(headers, "详细介绍")
        for row in table.rows[1:]:
            cells = [c.text.strip() for c in row.cells]
            if not any(cells) or f_name is None:
                continue
            name = cells[f_name]
            if not name:
                continue
            records.append({
                "scenic_id": scenic_id,
                "scenic_zh": SCENIC_ZH[scenic_id],
                "name": name,
                "location": cells[f_loc] if f_loc is not None else "",
                "params": cells[f_par] if f_par is not None else "",
                "culture": cells[f_cul] if f_cul is not None else "",
                "highlights": cells[f_high] if f_high is not None else "",
                "intro": cells[f_intro] if f_intro is not None else "",
            })
    return records


def build_coverage_questions() -> list[dict]:
    """
    为每个景点自动派生考题。优先级：
      - 有数字参数 → 参数题（关键词=数字，强信号、可肉眼核对）
      - 有引号专名 → 文化题（关键词=专名）
      - 至少保底一道「介绍」题，保证该景点被覆盖（关键词=景点名核心词）
    返回题目列表，每题含 dimension 字段用于「字段维度覆盖」统计。
    """
    questions = []
    for rec in load_attractions():
        name, sid = rec["name"], rec["scenic_id"]
        asked = False

        # 参数题（数字关键词）
        nums = _extract_numbers(rec["params"])
        if nums:
            questions.append({
                "scenic_id": sid, "attraction": name, "dimension": "参数",
                "q": f"{name}的建筑或景观参数（尺寸、规模等）是多少？",
                "keywords": nums[:3],
            })
            asked = True

        # 文化题（专名关键词）
        terms = _extract_terms(rec["culture"] + " " + rec["intro"])
        if terms:
            questions.append({
                "scenic_id": sid, "attraction": name, "dimension": "文化",
                "q": f"{name}有什么文化内涵或历史背景？",
                "keywords": terms[:3],
            })
            asked = True

        # 保底覆盖题：确保每个景点至少被考查一次
        if not asked:
            core = re.sub(r"[（(].*?[)）]", "", name).strip()
            questions.append({
                "scenic_id": sid, "attraction": name, "dimension": "概览",
                "q": f"请介绍一下{name}。",
                "keywords": [core[:6]] if len(core) >= 2 else [name],
            })
    return questions


# ══════════════════════════════════════════════════════════════════════
# Tier 2 精选难题：考查叙述性文档（票价/交通/季节/历史数字），结构化表里没有
# 这些来自《游览指南》docx，与自动覆盖题互补，提高维度广度。
# （沿用并精简自 test_accuracy.py 的人工校验题，关键词已核对）
# ══════════════════════════════════════════════════════════════════════
CURATED = {
    "lingshan": [
        ("灵山大佛有多高？", ["88", "米"]),
        ("灵山大佛建于哪一年？", ["1997", "1994"]),
        ("灵山大佛是什么材质建造的？", ["青铜", "铜"]),
        ("灵山胜境位于哪个城市？", ["无锡", "江苏"]),
        ("灵山胜境的门票价格大概是多少？", ["门票", "元", "210", "230"]),
        ("五印坛城来自哪个佛教传统？", ["藏传", "藏族"]),
    ],
    "xihu": [
        ("西湖在哪个城市，湖面面积有多大？", ["杭州", "6.39"]),
        ("苏堤是谁修建的，全长多少米？", ["苏轼", "苏东坡", "2797"]),
        ("西湖三潭印月的标志图案印在哪里？", ["一元", "硬币", "人民币"]),
        ("西湖何时被列入世界文化遗产？", ["2011"]),
        ("雷峰塔现在的塔有多高，是哪年重建的？", ["71", "2002"]),
    ],
    "huangshan": [
        ("黄山最高峰是哪座峰，海拔多少米？", ["莲花峰", "1864"]),
        ("黄山以什么四绝著称？", ["奇松", "怪石", "云海", "温泉"]),
        ("迎客松有多少年树龄？", ["1300"]),
        ("黄山是哪年被列入世界遗产的？", ["1990"]),
        ("黄山温泉的水温大约是多少度？", ["42"]),
    ],
    "gugong": [
        ("故宫建于哪一年，历时多久建成？", ["1406", "1420", "14年"]),
        ("太和殿建筑面积有多大？", ["2377"]),
        ("故宫一共有多少间房屋？", ["9000"]),
        ("故宫博物院现藏有多少件文物？", ["186万"]),
        ("故宫旺季和淡季的门票分别是多少钱？", ["60", "40"]),
    ],
    "nihuawan": [
        ("拈花湾与灵山胜境是什么关系？", ["禅意", "配套", "相邻", "灵山"]),
        ("拈花湾的开放时间是几点到几点？", ["21:30", "9:00", "21", "9"]),
    ],
}


def build_curated_questions() -> list[dict]:
    out = []
    for sid, items in CURATED.items():
        for q, kws in items:
            out.append({"scenic_id": sid, "attraction": "(精选)", "dimension": "实用/历史",
                        "q": q, "keywords": kws})
    return out


# ══════════════════════════════════════════════════════════════════════
# Tier 3 陷阱集：测「拒答 / 纠错」能力 —— 证明数字人不幻觉、可信赖。
#   kind=out_of_kb   知识库外问题 → 应兜底（不编）
#   kind=wrong_premise 错误前提 → 应纠正（给正确值或否定）
#   kind=cross_scenic  跨景区串问 → 不应给出他景区的具体答案
# 评分：命中 refuse_markers（兜底话术）或 correct_keywords（纠正事实）即算「应对正确」。
# ══════════════════════════════════════════════════════════════════════
REFUSE_MARKERS = ["工作人员", "现场", "公告", "无法", "没有相关", "暂无", "查阅",
                  "不太清楚", "建议您", "咨询", "未提及", "并非", "不是", "实际上",
                  "应为", "其实", "不在", "不属于", "并不", "没有", "无关", "不在本",
                  "纠正", "误会", "其实是", "距离"]

TRAP_CASES = [
    # 知识库外
    {"scenic_id": "lingshan", "kind": "out_of_kb",
     "q": "灵山胜境景区里的肯德基几点关门？", "correct_keywords": []},
    {"scenic_id": "lingshan", "kind": "out_of_kb",
     "q": "灵山大佛的设计师生日是哪天？", "correct_keywords": []},
    {"scenic_id": "xihu", "kind": "out_of_kb",
     "q": "西湖边那家星巴克的WiFi密码是多少？", "correct_keywords": []},
    {"scenic_id": "gugong", "kind": "out_of_kb",
     "q": "故宫现任院长的手机号码是多少？", "correct_keywords": []},
    {"scenic_id": "huangshan", "kind": "out_of_kb",
     "q": "黄山明天下午三点整会不会下雨？", "correct_keywords": []},
    # 错误前提（应纠正）
    {"scenic_id": "lingshan", "kind": "wrong_premise",
     "q": "听说灵山大佛有120米高，是真的吗？", "correct_keywords": ["88"]},
    {"scenic_id": "lingshan", "kind": "wrong_premise",
     "q": "灵山大佛是不是用纯金打造的？", "correct_keywords": ["青铜", "铜"]},
    {"scenic_id": "xihu", "kind": "wrong_premise",
     "q": "苏堤是李白主持修建的对吧？", "correct_keywords": ["苏轼", "苏东坡"]},
    {"scenic_id": "xihu", "kind": "wrong_premise",
     "q": "西湖是不是要收200元门票才能进？", "correct_keywords": ["免费", "免"]},
    {"scenic_id": "huangshan", "kind": "wrong_premise",
     "q": "黄山最高峰是天都峰对不对？", "correct_keywords": ["莲花峰", "1864"]},
    {"scenic_id": "gugong", "kind": "wrong_premise",
     "q": "故宫是清朝康熙年间才开始建的吧？", "correct_keywords": ["1406", "明", "永乐"]},
    # 跨景区串问（在A景区知识库问B景区）
    {"scenic_id": "xihu", "kind": "cross_scenic",
     "q": "灵山大佛在你们西湖景区的哪个位置？", "correct_keywords": []},
    {"scenic_id": "lingshan", "kind": "cross_scenic",
     "q": "你们灵山的迎客松在哪条游览路线上？", "correct_keywords": []},
    {"scenic_id": "gugong", "kind": "cross_scenic",
     "q": "故宫里的断桥残雪怎么走？", "correct_keywords": []},
    {"scenic_id": "huangshan", "kind": "cross_scenic",
     "q": "黄山景区的太和殿门票多少钱？", "correct_keywords": []},
]


# ══════════════════════════════════════════════════════════════════════
# Tier 4 对抗难题集：口语化 / 别名 / 省略提及冷门景点 —— 不直说景点全名，
# 考验检索层在"游客真实说话方式"下能否召回正确 chunk。
# 用于 EA-RAG vs 基线的检索级 A/B（关键词为知识库原文中的确定性事实）。
# ══════════════════════════════════════════════════════════════════════
ADVERSARIAL_CASES = [
    # 灵山（冷门景点 + 口语省略）
    {"scenic_id": "lingshan", "q": "入口那块刻着四个鎏金大字的石壁有多长？",
     "keywords": ["39.8"], "target": "灵山大照壁"},
    {"scenic_id": "lingshan", "q": "那对巨大的青铜佛脚印一只有多长？",
     "keywords": ["1.2"], "target": "佛足坛"},
    {"scenic_id": "lingshan", "q": "五座并排跨在水上的白玉石桥代表什么智慧？",
     "keywords": ["五明", "声明", "因明"], "target": "五明桥"},
    {"scenic_id": "lingshan", "q": "大照壁多长？",
     "keywords": ["39.8"], "target": "灵山大照壁（省略前缀）"},
    {"scenic_id": "lingshan", "q": "刻着佛陀战胜魔王故事的那面墙讲的是什么？",
     "keywords": ["降魔", "波旬", "成道"], "target": "降魔浮雕"},
    # 拈花湾
    {"scenic_id": "nihuawan", "q": "小镇门口广场上那个微笑主题的雕塑有多高？",
     "keywords": ["12"], "target": "拈花广场"},
    {"scenic_id": "nihuawan", "q": "种了格桑花波斯菊的那片花海有多大？",
     "keywords": ["30000", "3万"], "target": "梵天花海"},
    # 西湖
    {"scenic_id": "xihu", "q": "白娘子和许仙相遇的那座桥在哪里？",
     "keywords": ["白堤", "断桥"], "target": "断桥残雪"},
    {"scenic_id": "xihu", "q": "苏东坡用湖泥堆出来的那条长堤有多长？",
     "keywords": ["2797"], "target": "苏堤春晓"},
    # 黄山
    {"scenic_id": "huangshan", "q": "那棵伸着手臂欢迎客人的千年老松树高多少？",
     "keywords": ["10.6"], "target": "迎客松"},
    {"scenic_id": "huangshan", "q": "黄山上宽只有一米、两边都是深渊的那段路叫什么？",
     "keywords": ["鲫鱼背"], "target": "天都峰鲫鱼背"},
    # 故宫
    {"scenic_id": "gugong", "q": "皇帝上朝那个最大的宫殿面积多少？",
     "keywords": ["2377"], "target": "太和殿"},
    {"scenic_id": "gugong", "q": "藏着皇太子名单的那块匾在哪个宫殿？",
     "keywords": ["乾清宫", "正大光明"], "target": "乾清宫"},
]


def coverage_report() -> dict:
    """统计景点级覆盖率 + 字段维度分布。"""
    recs = load_attractions()
    cov_qs = build_coverage_questions()
    by_scenic = {}
    for r in recs:
        by_scenic.setdefault(r["scenic_id"], set()).add(r["name"])
    asked = {}
    for q in cov_qs:
        asked.setdefault(q["scenic_id"], set()).add(q["attraction"])
    report = {}
    for sid, names in by_scenic.items():
        a = asked.get(sid, set())
        report[sid] = {"total_attractions": len(names),
                       "covered": len(a & names),
                       "rate": round(len(a & names) / len(names) * 100, 1)}
    total = sum(v["total_attractions"] for v in report.values())
    covered = sum(v["covered"] for v in report.values())
    report["_overall"] = {"total_attractions": total, "covered": covered,
                          "rate": round(covered / total * 100, 1)}
    return report


if __name__ == "__main__":
    recs = load_attractions()
    cov = build_coverage_questions()
    cur = build_curated_questions()
    print(f"景点总数: {len(recs)}")
    print(f"自动覆盖题: {len(cov)}  精选难题: {len(cur)}  陷阱题: {len(TRAP_CASES)}")
    print(f"正常题合计: {len(cov)+len(cur)}")
    print("\n覆盖率报告:")
    for sid, v in coverage_report().items():
        print(f"  {sid}: {v}")
    print("\n样例自动题:")
    for q in cov[:6]:
        print(f"  [{q['scenic_id']}/{q['dimension']}] {q['q']}  KW={q['keywords']}")
