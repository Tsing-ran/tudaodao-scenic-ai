"""阶段0：为 EchoMimicV2 生成「半身带手」参考图（万相云 API，0 GPU）。

EchoMimicV2 的手势驱动要求参考图把双手露在画面里、半身正面、背景干净，
否则姿态模板对不上 → 形变。本脚本出几版 F1 知性女导览员风格半身带手图，
供后续与姿态模板对齐后做"我们自己的"样片（演示英雄镜头）。
产物 assets/echomimic_ref/<id>.png（1024x1024 方构图，贴合 infer.py 的 768 resize）。
用法：unset 代理后 .venv/bin/python scripts/gen_echomimic_ref.py
"""
import os
from pathlib import Path
import httpx
import dashscope
from dashscope import ImageSynthesis
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY")
OUT = Path(__file__).resolve().parents[1] / "assets" / "echomimic_ref"
MODEL = "wanx2.1-t2i-plus"

# 共同尾缀：半身、双手可见、正面、纯背景、写实 —— EchoMimic 参考图硬要求
SUFFIX = (
    "，半身构图从头到髋部，双手自然舒展置于身前清晰可见无遮挡，"
    "正面直视镜头，端正自然站姿，双臂微微张开，"
    "纯净浅灰色影棚背景，柔和均匀的影棚光，高颜值精致五官，"
    "皮肤干净通透，超写实人像摄影，电影质感，8k，方形构图"
)
NEG = ("侧身，背影，转身，手部残缺，多余的手指，手被遮挡，抱胸，插兜，"
       "大头特写，过近，杂乱背景，文字，水印，低分辨率，畸形")

REFS = {
    "F1_guide_a": "一位知性干练的现代女性景区讲解员，得体的海军蓝职业西装外套，佩戴讲解员工作证，利落的低马尾，面容清秀自然亲和，双手在身前轻轻摊开做讲解手势",
    "F1_guide_b": "一位知性干练的现代女性景区讲解员，海军蓝职业西装，低马尾，面容清秀亲和，一只手自然抬起像在指引介绍，另一只手垂在身侧",
    "F1_guide_c": "一位青春甜美的年轻女性景区向导，清爽的浅蓝色景区马甲制服，高扎马尾，面容甜美灵动，双手在胸前自然交叠又微微展开，亲切微笑",
    "F1_guide_d": "一位温婉的中国风女性导游，淡雅改良旗袍，优雅盘发，面容清丽，双手在身前自然舒展做欢迎手势",
}

_C = httpx.Client(trust_env=False, timeout=180, follow_redirects=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for rid, desc in REFS.items():
        print(f"[{rid}] 万相生成中…", flush=True)
        try:
            r = ImageSynthesis.call(model=MODEL, prompt=desc + SUFFIX,
                                    negative_prompt=NEG, n=1, size="1024*1024")
        except Exception as e:
            print(f"  ❌ {rid} 异常 {e}", flush=True); continue
        if r.status_code != 200:
            print(f"  ❌ {rid} 失败 {r.code} {r.message}", flush=True); continue
        dst = OUT / f"{rid}.png"
        dst.write_bytes(_C.get(r.output.results[0].url).content)
        print(f"  ✅ {dst}", flush=True)
    print("完成 →", OUT)


if __name__ == "__main__":
    main()
