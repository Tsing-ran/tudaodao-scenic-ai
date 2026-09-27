"""故宫专属数字人身份（dh_gugong）注册与智能默认 — Phase 1 回归。

跑法：cd /home/jiale/Desktop/Digital_Person && .venv/bin/python tests/test_gugong_avatar.py
纯逻辑 + 文件系统真值，不依赖外网/GPU。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.api.digital_human import (
    _AVATAR_PRESETS, _DITTO_BASE, _effective_avatars, _scenic_default_config,
    _SCENIC_BOUND_AVATAR,
)
import bridge.server as bridge

passed = failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1; print(f"  ✅ {name}")
    else:
        failed += 1; print(f"  ❌ {name}")


print("\n── 故宫专属身份 dh_gugong ──")
gg = next((a for a in _AVATAR_PRESETS if a["id"] == "dh_gugong"), None)
check("dh_gugong 已注册进 presets", gg is not None)
check("绑定 scenic=gugong", gg and gg.get("scenic") == "gugong")
check("preview 指向 dh_gugong.jpg", gg and gg.get("preview") == "/avatars/dh_gugong.jpg")
check("dh_gugong 在 _DITTO_BASE", "dh_gugong" in _DITTO_BASE)
check("dh_gugong 在桥接 AVATAR_MAP", "dh_gugong" in bridge.AVATAR_MAP)

print("\n── 景区智能默认（零 DB 播种）──")
check("灵山 → dh_lingshan", _scenic_default_config("lingshan") and _scenic_default_config("lingshan")["avatar_id"] == "dh_lingshan")
check("故宫 → dh_gugong", _scenic_default_config("gugong") and _scenic_default_config("gugong")["avatar_id"] == "dh_gugong")
check("未绑定景区 → None（回落全局默认）", _scenic_default_config("not_a_scenic") is None)
check("灵山/故宫均在 _SCENIC_BOUND_AVATAR", {"lingshan", "gugong"} <= set(_SCENIC_BOUND_AVATAR))

print("\n── 桥接底板候选解析（最具体优先）──")
cands = bridge._live_avatar_candidates("dh_gugong", "gugong", "main")
check("16:9 主候选 = dh_gugong__gugong__16x9", cands[0] == "dh_gugong__gugong__16x9")
pcands = bridge._live_avatar_candidates("dh_gugong", "gugong", "portrait")
check("9:16 竖版候选 = dh_gugong__gugong__9x16", pcands[0] == "dh_gugong__gugong__9x16")

print("\n── 底板文件就绪（本机真值；ready 来自文件系统）──")
eff = {a["id"]: a for a in _effective_avatars()}
# ready 可能为 None（无 ditto 目录的纯云端机），此处只在能查到目录时严格要求
r = eff["dh_gugong"].get("ready")
check("dh_gugong ready ∈ {True, None}（有目录则必 True）", r in (True, None))

print(f"\n{'='*40}\n通过 {passed} / {passed + failed}")
sys.exit(0 if failed == 0 else 1)
