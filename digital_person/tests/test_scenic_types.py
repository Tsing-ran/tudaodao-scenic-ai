"""景区类型画像（scenic_type）单测：类型映射、口吻差异、注入正确性、中性兜底。

跑法：cd /home/jiale/Desktop/Digital_Person && .venv/bin/python tests/test_scenic_types.py
不依赖外网/模型，纯逻辑断言。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.rag.scenic_types import (
    scenic_type_of, type_label, type_persona_directive,
    type_reminder_directive, type_reco_guideline,
)
from backend.rag.pipeline import _directive_with_context
from backend.agent.intents import Intent

passed = failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}")


print("\n── 1. 类型映射 ──")
check("灵山 = religious", scenic_type_of("lingshan") == "religious")
check("故宫 = museum", scenic_type_of("gugong") == "museum")
check("黄山 = mountain", scenic_type_of("huangshan") == "mountain")
check("西湖 = urban_open", scenic_type_of("xihu") == "urban_open")
check("拈花湾 = resort_town", scenic_type_of("nihuawan") == "resort_town")
check("兵马俑/莫高窟 = museum", scenic_type_of("bingmayong") == "museum" and scenic_type_of("mogaoku") == "museum")
check("未知景区 → 空类型", scenic_type_of("not_a_scenic") == "")

print("\n── 2. 类型标签 ──")
check("灵山标签=禅意宗教", type_label("lingshan") == "禅意宗教")
check("故宫标签=博物展陈", type_label("gugong") == "博物展陈")
check("未知景区标签为空", type_label("not_a_scenic") == "")

print("\n── 3. 口吻差异（灵山 ≠ 故宫）──")
ls_persona = type_persona_directive("lingshan")
gg_persona = type_persona_directive("gugong")
check("灵山口吻非空且含'禅'", ls_persona and "禅" in ls_persona)
check("故宫口吻非空且含'文博/考据'", gg_persona and ("文博" in gg_persona or "考据" in gg_persona))
check("灵山口吻 ≠ 故宫口吻", ls_persona != gg_persona)

print("\n── 4. 主动提醒差异 ──")
check("灵山提醒含'礼仪/祈福'", any(k in type_reminder_directive("lingshan") for k in ("礼仪", "祈福")))
check("故宫提醒含'预约/文物'", any(k in type_reminder_directive("gugong") for k in ("预约", "文物")))
check("黄山提醒含'索道/日出/天气'", any(k in type_reminder_directive("huangshan") for k in ("索道", "日出", "天气")))

print("\n── 5. 注入正确性：qa 带口吻、不带提醒；navigation 两者都带 ──")
ls_qa = _directive_with_context(Intent.QA, "lingshan")
gg_qa = _directive_with_context(Intent.QA, "gugong")
check("灵山 qa 含口吻", "禅" in ls_qa)
check("故宫 qa 含口吻", ("文博" in gg_qa or "考据" in gg_qa))
check("灵山 qa ≠ 故宫 qa（差异化生效）", ls_qa != gg_qa)
check("qa 不含主动提醒（避免 prompt 膨胀）", "祈福" not in ls_qa)
ls_nav = _directive_with_context(Intent.NAVIGATION, "lingshan")
check("navigation 含主动提醒", any(k in ls_nav for k in ("礼仪", "祈福")))
check("navigation 含口吻", "禅" in ls_nav)

print("\n── 6. 中性兜底：未登记景区注入为空增量（零准确率影响）──")
unknown_qa = _directive_with_context(Intent.QA, "not_a_scenic")
from backend.agent.handlers import intent_directive
check("未登记景区 qa 指令 == 纯意图指令（无类型增量）", unknown_qa == intent_directive(Intent.QA))
check("未登记景区推荐准则为空", type_reco_guideline("not_a_scenic") == "")

print(f"\n{'='*40}\n通过 {passed} / {passed + failed}")
sys.exit(0 if failed == 0 else 1)
