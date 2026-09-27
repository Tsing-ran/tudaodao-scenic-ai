"""本地肖像图 → 自然微动 idle 待机视频（通义万相 图生视频）。

为什么用图生视频而不是 LivePortrait：万相 i2v 是真·视频扩散生成，整帧连贯，
头一动头发自然跟随 → 不会出现 LivePortrait（2D 扭曲）那种"头动发不动"的穿模。
动作 prompt 控制成"小幅自然微动"，既破死脸又稳。

用法：
  .venv/bin/python scripts/make_idle_from_image.py <输入图.png> <输出.mp4>
"""
import os
import sys
from pathlib import Path

import dashscope
import httpx
from dashscope import VideoSynthesis
from dotenv import load_dotenv

I2V_MODEL = "wanx2.1-i2v-turbo"

# ── 播音员"动作分离"原则 ──────────────────────────────────────────────────────
# 根因：i2v 物理模拟会让眨眼帧与发丝摆动帧在同一时刻叠加（"复合运动帧"），
# MuseTalk 推理时直接用 idle 帧做底座，复合运动帧出现在说话流里就变成"抽搐感"。
# 播音员对策：①发型用造型剂固定（发丝绝不动）②眨眼在句间孤立发生（与头动时间隔离）
#             ③头部完全静止（只有呼吸微起伏）→ 三类运动彻底解耦，消除复合运动帧。
# ─────────────────────────────────────────────────────────────────────────────

# neutral 底座（默认）：沉稳端庄浅笑
MOTION = (
    "一位专业的女主播端坐在镜头前，目光始终平视前方、专注真诚地看着镜头，富有对象感；"
    "【头发关键】头发完全静止固定，如同用造型剂定型，一丝一毫都不飘动、不摆动、不随任何动作晃动；"
    "头部和肩膀完全静止端正，绝不左右摇头或前后晃动，只有几乎察觉不到的极微呼吸起伏；"
    "保持端庄温和的浅笑，神情沉稳亲和；"
    "眼睛几乎全程完全睁开，仅在第3到4秒之间发生唯一一次、短促干脆的单次眨眼，"
    "该次眨眼与头部、头发的任何动作在时间上完全隔离，眨眼后眼睛立即重新睁开；"
    "切忌出现眨眼与头发摆动同时发生的情况；"
    "背景纯净静止，镜头固定，画面稳定清晰"
)

# happy 底座：温暖微笑、眼含笑意（眨眼与发型规则同上）
MOTION_HAPPY = (
    "一位专业的女主播端坐在镜头前，目光平视镜头，嘴角自然上扬、展现温暖真诚的微笑，眼含笑意，神情亲切愉悦；"
    "【头发关键】头发完全静止固定，如同用造型剂定型，一丝一毫都不飘动、不摆动；"
    "头部和肩膀完全静止端正，只有几乎察觉不到的极微呼吸起伏；"
    "眼睛几乎全程完全睁开，仅在第3到4秒之间发生唯一一次、短促干脆的单次眨眼，"
    "眨眼与头发任何动作时间完全隔离，眨完立即睁开；"
    "切忌眨眼与头发摆动同时发生；"
    "背景纯净静止，镜头固定，画面稳定清晰"
)

# concerned 底座：温柔关切、眉间微凝（眨眼与发型规则同上）
MOTION_CONCERNED = (
    "一位专业的女主播端坐在镜头前，目光平视镜头，神情温柔专注，眉头微微带有轻柔的关切之意，"
    "流露出真诚的关心与理解，表情沉稳而富有同情心；"
    "【头发关键】头发完全静止固定，如同用造型剂定型，一丝一毫都不飘动、不摆动；"
    "头部和肩膀完全静止端正，只有几乎察觉不到的极微呼吸起伏；"
    "眼睛几乎全程完全睁开，仅在第3到4秒之间发生唯一一次、短促干脆的单次眨眼，"
    "眨眼与头发任何动作时间完全隔离，眨完立即睁开；"
    "切忌眨眼与头发摆动同时发生；"
    "背景纯净静止，镜头固定，画面稳定清晰"
)


def main():
    if len(sys.argv) < 3:
        sys.exit("用法: make_idle_from_image.py <输入图> <输出mp4> [表情motion覆盖]")
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    motion = sys.argv[3] if len(sys.argv) > 3 else MOTION   # 可选：覆盖动作/表情 prompt
    if not src.exists():
        sys.exit(f"输入图不存在: {src}")

    load_dotenv()
    key = os.getenv("DASHSCOPE_API_KEY")
    dashscope.api_key = key

    # 传 file:// 本地路径，SDK 自动上传到 DashScope OSS 并解析
    img = f"file://{src.resolve()}"
    print(f"[i2v] {I2V_MODEL} 自动上传本地图并生成 …（约 3-5 分钟）")
    rsp = VideoSynthesis.call(model=I2V_MODEL, prompt=motion, img_url=img)
    if rsp.status_code != 200:
        sys.exit(f"❌ 图生视频失败 code={rsp.code} msg={rsp.message}")
    url = rsp.output.video_url
    dst.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(trust_env=False, timeout=180, follow_redirects=True) as c:
        dst.write_bytes(c.get(url).content)
    print(f"✅ idle 视频已存: {dst}")


if __name__ == "__main__":
    main()
