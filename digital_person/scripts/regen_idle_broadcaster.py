"""
重新生成三套 idle 底座（播音员静态版）——消除复合运动帧（眨眼+甩发同时出现的抽搐感）。

改进原理（播音员"动作分离"原则）：
  旧版：i2v 物理模拟让眨眼帧和发丝摆动帧时间叠加（复合运动帧）
       → MuseTalk 说话时这些帧出现 → 视觉"抽搐"
  新版：头发固定（造型剂原则）+ 眨眼孤立（句间发生，不与头/发运动叠加）
       → 彻底消除复合运动帧

用法：
  .venv/bin/python scripts/regen_idle_broadcaster.py
"""
import os, sys, json, dashscope, httpx
from pathlib import Path
from dashscope import VideoSynthesis
from dotenv import load_dotenv

load_dotenv()
dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

BASE = Path(__file__).parent.parent
IMG  = BASE / "assets/avatar_candidates/16_sweet_bob_retouched.png"
MODEL = "wanx2.1-i2v-turbo"

# 三套底座 → (输出路径, MOTION prompt)
VARIANTS = {
    "neutral": {
        "out": BASE / "assets/avatar_src/sweet_bob/idle.mp4",
        "motion": (
            "一位专业的女主播端坐在镜头前，目光始终平视前方、专注真诚地看着镜头，富有对象感；"
            "头发完全静止固定，如同用造型剂定型，一丝一毫都不飘动、不摆动、不随任何动作晃动；"
            "头部和肩膀完全静止端正，绝不左右摇头或前后晃动，只有几乎察觉不到的极微呼吸起伏；"
            "保持端庄温和的浅笑，神情沉稳亲和；"
            "眼睛几乎全程完全睁开，仅在第3到4秒之间发生唯一一次短促干脆的单次眨眼，"
            "该次眨眼与头部头发的任何动作在时间上完全隔离，眨眼后眼睛立即重新睁开；"
            "切忌出现眨眼与头发摆动同时发生的情况；背景纯净静止，镜头固定，画面稳定清晰"
        ),
    },
    "happy": {
        "out": BASE / "assets/avatar_src/sweet_bob_happy/idle.mp4",
        "motion": (
            "一位专业的女主播端坐在镜头前，目光平视镜头，嘴角自然上扬展现温暖真诚的微笑，"
            "眼含笑意，神情亲切愉悦；"
            "头发完全静止固定，如同用造型剂定型，一丝一毫都不飘动、不摆动；"
            "头部和肩膀完全静止端正，只有几乎察觉不到的极微呼吸起伏；"
            "眼睛几乎全程完全睁开，仅在第3到4秒之间发生唯一一次短促干脆的单次眨眼，"
            "眨眼与头发任何动作时间完全隔离，眨完立即睁开；"
            "切忌眨眼与头发摆动同时发生；背景纯净静止，镜头固定，画面稳定清晰"
        ),
    },
    "concerned": {
        "out": BASE / "assets/avatar_src/sweet_bob_concerned/idle.mp4",
        "motion": (
            "一位专业的女主播端坐在镜头前，目光平视镜头，神情温柔专注，"
            "眉头微微带有轻柔的关切之意，流露出真诚的关心与理解，表情沉稳而富有同情心；"
            "头发完全静止固定，如同用造型剂定型，一丝一毫都不飘动、不摆动；"
            "头部和肩膀完全静止端正，只有几乎察觉不到的极微呼吸起伏；"
            "眼睛几乎全程完全睁开，仅在第3到4秒之间发生唯一一次短促干脆的单次眨眼，"
            "眨眼与头发任何动作时间完全隔离，眨完立即睁开；"
            "切忌眨眼与头发摆动同时发生；背景纯净静止，镜头固定，画面稳定清晰"
        ),
    },
}


def gen_one(name, cfg):
    out = Path(cfg["out"])
    motion = cfg["motion"]
    img_url = f"file://{IMG.resolve()}"
    print(f"\n[{name}] 提交 i2v …")
    rsp = VideoSynthesis.call(model=MODEL, prompt=motion, img_url=img_url)
    if rsp.status_code != 200:
        print(f"[{name}] ❌ 失败: code={rsp.code} msg={rsp.message}")
        return False
    url = rsp.output.video_url
    out.parent.mkdir(parents=True, exist_ok=True)
    # 备份旧版
    if out.exists():
        out.rename(out.with_suffix(".mp4.bak"))
    print(f"[{name}] 下载视频…")
    with httpx.Client(trust_env=False, timeout=180, follow_redirects=True) as c:
        out.write_bytes(c.get(url).content)
    print(f"[{name}] ✅ 已存: {out}  ({out.stat().st_size//1024}KB)")
    return True


if __name__ == "__main__":
    if not IMG.exists():
        sys.exit(f"主图不存在: {IMG}")
    print(f"使用图: {IMG}")
    ok = 0
    for name, cfg in VARIANTS.items():
        if gen_one(name, cfg):
            ok += 1
    print(f"\n=== 完成 {ok}/{len(VARIANTS)} ===")
    if ok == len(VARIANTS):
        print("全部生成成功，请运行 genavatar 重烘三套 avatar。")
    else:
        sys.exit("部分失败，请检查上方错误。")
