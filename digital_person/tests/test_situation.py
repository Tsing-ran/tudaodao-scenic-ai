"""自身情况标签（Phase B）单元测试 —— 独立脚本，无需网络/GPU/服务。

跑法：.venv/bin/python tests/test_situation.py

核心断言 = back-compat：situation 为 None / 全默认时，**缓存键与系统 prompt 与改动前逐字节一致**
→ 老画像/未选向导的存量用户行为零变化、缓存零失效、准确率零影响。非默认情境则得到
独立缓存键 + 注入"因人而异"指令，不串答。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.rag.pipeline import _situation_dict, _situation_key, _cache_query
from backend.llm.prompts import _build_situation_directive, build_system_prompt
from backend.api.chat import Situation
from backend.api.recommend import _sit_labels

passed = 0


def check(name, cond):
    global passed
    assert cond, f"FAIL: {name}"
    passed += 1
    print(f"  ✓ {name}")


print("== 缓存键 back-compat（最关键）==")
OLD = "adult::auto::大佛多高"   # 改动前的键格式
check("None → 键与历史逐字节一致", _cache_query("adult", "auto", _situation_key(None), "大佛多高") == OLD)
default_sit = _situation_dict(Situation())
check("全默认 Situation → sit_key 为空", _situation_key(default_sit) == "")
check("全默认 → 键与历史逐字节一致", _cache_query("adult", "auto", _situation_key(default_sit), "大佛多高") == OLD)
check("非 lingshan 组合也一致", _cache_query("senior", "en", _situation_key(None), "how tall") == "senior::en::how tall")

print("== 非默认情境 → 独立键 + 确定性 ==")
sit = _situation_dict(Situation(mobility="wheelchair", purpose="pray"))
k = _situation_key(sit)
check("仅非默认维度入键、维度序固定", k == "mobility=wheelchair,purpose=pray")
# 输入维度顺序不同 → 键相同（确定性，靠 _SIT_DIMS 顺序而非输入顺序）
k2 = _situation_key(_situation_dict(Situation(purpose="pray", mobility="wheelchair")))
check("键与输入字段顺序无关", k == k2)
key_full = _cache_query("adult", "auto", k, "大佛多高")
check("含情境的键格式正确", key_full == "adult::auto::mobility=wheelchair,purpose=pray::大佛多高")
check("非默认键 != 历史键（不串答）", key_full != OLD)
check("部分默认 → 仅非默认维度", _situation_key(_situation_dict(Situation(age="elder"))) == "age=elder")

print("== dict / pydantic 归一化等价 ==")
check("dict 与模型归一化等价",
      _situation_key({"age": "youth", "pace": "day", "mobility": "wheelchair", "purpose": "relax", "first_time": "first"})
      == "mobility=wheelchair")

print("== 情境指令注入 ==")
check("None → 空指令", _build_situation_directive(None) == "")
check("全默认 → 空指令", _build_situation_directive(default_sit) == "")
d = _build_situation_directive(sit)
check("非默认 → 含轮椅指令", "无障碍" in d and "无台阶" in d)
check("非默认 → 含祈福指令", "祈福" in d)
d_elder = _build_situation_directive(_situation_dict(Situation(age="elder")))
check("年长指令讲游客本人（#2，不混入轮椅专属语）", "年长" in d_elder and "只推荐无台阶" not in d_elder)

# 体力轴裁决（#1）：hiker 单独保留挑战；长辈在场（group=senior 或 age=elder）让位稳妥，消解对冲
_hiker = _situation_dict(Situation(mobility="hiker"))
check("hiker 单独 → 保留挑战徒步", "挑战" in _build_situation_directive(_hiker, "adult"))
_d_sh = _build_situation_directive(_hiker, "senior")
check("hiker + group=senior → 让位稳妥（消解体力轴对冲）", "稳妥" in _d_sh and "更有挑战的玩法" not in _d_sh)
_d_eh = _build_situation_directive(_situation_dict(Situation(mobility="hiker", age="elder")), "adult")
check("hiker + age=elder → 让位稳妥", "稳妥" in _d_eh and "更有挑战的玩法" not in _d_eh)

print("== 系统 prompt byte-identity（零准确率影响）==")
ctx = ["灵山大佛高 88 米。| 来源A"]
p_none = build_system_prompt("灵山胜境", "g", ctx, "auto", "", "adult", situation=None)
p_def = build_system_prompt("灵山胜境", "g", ctx, "auto", "", "adult", situation=default_sit)
p_old = build_system_prompt("灵山胜境", "g", ctx, "auto", "", "adult")   # 不传 situation（存量调用）
check("situation=None 的 prompt 与不传 situation 逐字节一致", p_none == p_old)
check("全默认 situation 的 prompt 也逐字节一致", p_def == p_old)
check("默认 prompt 不含「因人而异」标记", "因人而异" not in p_none)
p_sit = build_system_prompt("灵山胜境", "g", ctx, "auto", "", "adult",
                            situation=_situation_dict(Situation(mobility="wheelchair")))
check("非默认 prompt 注入「因人而异」+ 无障碍", "因人而异" in p_sit and "无障碍" in p_sit)
# group_type 与 situation 正交：senior 人格 + wheelchair 情境同时在
p_both = build_system_prompt("灵山胜境", "g", ctx, "auto", "", "senior",
                             situation=_situation_dict(Situation(purpose="pray")))
check("group 人格与 situation 指令并存", "老年长辈" in p_both and "祈福" in p_both)

print("== recommend 标签 ==")
check("None → 空标签", _sit_labels(None) == [])
check("全默认 → 空标签", _sit_labels(default_sit) == [])
check("非默认 → 人话标签（序固定）",
      _sit_labels(_situation_dict(Situation(mobility="wheelchair", purpose="pray"))) == ["需无障碍", "祈福参拜"])

print(f"\n✅ test_situation: {passed}/{passed} 通过")
