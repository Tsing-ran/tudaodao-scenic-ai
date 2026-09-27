"""热拔插换形象 — 桥接解析器 + 后端诚实目录的纯逻辑回归测试。

跑法：.venv/bin/python tests/test_avatar_hotswap.py
（纯逻辑，不需起服务；端到端直播热切已在 AutoDL 实测，见进度日志 2026-06-15。）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bridge.server import (AVATAR_MAP, DEFAULT_AVATAR, _live_avatar_candidates,
                           _ASPECT)

ok = 0
fail = 0


def check(name, cond):
    global ok, fail
    if cond:
        ok += 1
        print(f"  ✅ {name}")
    else:
        fail += 1
        print(f"  ❌ {name}")


print("== AVATAR_MAP 接线（10 身份 + 6 换装）==")
for i in ("F1_modern", "F2_hanfu", "M1_modern", "M4_business"):
    check(f"{i} → 自身 base", AVATAR_MAP.get(i) == i)
for o, base in (("outfit_qipao", "sweet_outfit_qipao"),
                ("outfit_coat", "sweet_outfit_coat")):
    check(f"{o} → {base}", AVATAR_MAP.get(o) == base)
check("female_sweet → sweet_bob_ditto", AVATAR_MAP.get("female_sweet") == "sweet_bob_ditto")

print("== _ASPECT 屏幕比例 ==")
check("main → 16x9", _ASPECT["main"] == "16x9")
check("portrait → 9x16", _ASPECT["portrait"] == "9x16")

print("== 身份库解析 <id>__<scenic>__<aspect> ==")
c = _live_avatar_candidates("F2_hanfu", "lingshan", "main")
check("F2_hanfu/lingshan/main 首选 __16x9", c[0] == "F2_hanfu__lingshan__16x9")
c = _live_avatar_candidates("F2_hanfu", "gugong", "portrait")
check("F2_hanfu/gugong/portrait 首选 __9x16", c[0] == "F2_hanfu__gugong__9x16")
check("缺景区回落灵山同比例在候选内", "F2_hanfu__lingshan__9x16" in c)

print("== sweet 传统命名兼容 ==")
c = _live_avatar_candidates("female_sweet", "lingshan", "main")
check("female_sweet/main 含 _bg_lingshan", "sweet_bob_ditto_bg_lingshan" in c)
c = _live_avatar_candidates("female_sweet", "lingshan", "portrait")
check("female_sweet/portrait 含 _portrait_lingshan", "sweet_bob_ditto_portrait_lingshan" in c)

print("== 换装解析（同脸带景）==")
c = _live_avatar_candidates("outfit_qipao", "lingshan", "main")
check("outfit_qipao/main 首选 sweet_outfit_qipao__lingshan__16x9",
      c[0] == "sweet_outfit_qipao__lingshan__16x9")

print("== 候选保序去重 + 兜底 ==")
c = _live_avatar_candidates("F1_modern", "lingshan", "main")
check("候选无重复", len(c) == len(set(c)))
check("末位含 DEFAULT_AVATAR 兜底", DEFAULT_AVATAR in c)
c = _live_avatar_candidates("不存在的id", "lingshan", "main")
check("未知 id base 回落 DEFAULT", c[-1] == DEFAULT_AVATAR)

print("== 后端诚实目录（文件系统真值）==")
try:
    from backend.api.digital_human import _effective_avatars, _ditto_ready, _DITTO_DIR
    av = _effective_avatars()
    check("_effective_avatars 不崩、返回非空", isinstance(av, list) and len(av) > 0)
    if _DITTO_DIR:
        # 有 ditto 目录时：ready 形象必不带 coming_soon；反之亦然
        bad = [a for a in av if a.get("ready") and a.get("coming_soon")]
        check("ready 与 coming_soon 互斥", not bad)
        # guofeng/male_casual 无 ditto 底板 → 必 coming_soon
        gf = next((a for a in av if a["id"] == "female_guofeng"), {})
        check("female_guofeng 无底板→coming_soon", gf.get("coming_soon") is True)
    else:
        print("  (跳过 ready 断言：本机无 ditto_avatars 目录)")
except Exception as e:
    check(f"后端目录导入/执行 异常: {e}", False)

print(f"\n{'='*40}\n通过 {ok} / 失败 {fail}")
sys.exit(1 if fail else 0)
