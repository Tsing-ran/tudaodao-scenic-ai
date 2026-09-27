"""拍照打卡核验·决策与融合 roundtrip（不打 DashScope，桩掉 VL，只验融合/决策/理由/位置软门）。

跑法：.venv/bin/python tests/test_checkin.py
真·VL 闭集识别准确率已用真实灵山照片单独实测（dafo 0.98 / wuyin 0.95 / 人像 none）。
"""

import asyncio
import sys

import backend.api.checkin as C
from backend.api.checkin import Cand, CheckinRequest, checkin_endpoint

CANDS = [
    Cand(id="menlou", name="灵山胜境门楼", lng=120.101730, lat=31.422257),
    Cand(id="dafo", name="灵山大佛", lng=120.096477, lat=31.430194),
]


def _stub(matched, conf, ev=None, alt=None):
    def f(image_b64, candidates, scenic_name="灵山胜境", image_format="jpeg"):
        return {"matched_id": matched, "confidence": conf, "evidence": ev or ["施无畏印手势"], "alt_id": alt}
    return f


def run(matched, conf, *, target="dafo", gps=None):
    C.verify_checkin = _stub(matched, conf)
    req = CheckinRequest(scenic_id="lingshan", image_b64="x", target_id=target, candidates=CANDS, gps=gps)
    return asyncio.run(checkin_endpoint(req))


def main():
    fails = 0

    def check(name, cond):
        nonlocal fails
        print(f"  {'✅' if cond else '❌'} {name}")
        if not cond:
            fails += 1

    # 1) 命中目标站 → confirmed
    r = run("dafo", 0.9)
    check("命中目标→confirmed", r.decision == "confirmed" and r.matched_name == "灵山大佛")

    # 2) 认出的是别的站 → wrong_stop
    r = run("dafo", 0.9, target="menlou")
    check("认出别站→wrong_stop", r.decision == "wrong_stop" and "调一下" in r.reason)

    # 3) 没认出 → uncertain
    r = run(None, 0.0)
    check("none→uncertain", r.decision == "uncertain")

    # 4) 置信低（无 GPS，阈值 0.7）→ uncertain
    r = run("dafo", 0.5)
    check("低置信→uncertain", r.decision == "uncertain")

    # 5) 位置软门·近：conf0.5 + GPS 就在大佛 → +0.15=0.65 ≥ 放宽阈值0.6 → confirmed
    r = run("dafo", 0.5, gps=[120.096477, 31.430194])
    check("GPS近加信→confirmed", r.decision == "confirmed" and r.distance_m is not None and r.distance_m <= 80
          and abs(r.confidence - 0.65) < 0.01 and "米" in r.reason)

    # 6) 位置软门·远：conf0.9 + GPS 在门楼(距大佛~1km) → -0.35=0.55 < 0.7 → uncertain（视觉与位置矛盾）
    r = run("dafo", 0.9, gps=[120.101730, 31.422257])
    check("GPS远减信→uncertain", r.decision == "uncertain" and r.distance_m > 300
          and abs(r.confidence - 0.55) < 0.01)

    print(f"\n{'通过' if fails == 0 else f'{fails} 项失败'}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
