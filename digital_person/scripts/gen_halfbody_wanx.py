"""通义万相生成「半身露手」女导游（16:9，自然头身比，给 EchoMimicV2 当手势参考）。

SDXL+InstantID 出半身露手老变大头娃娃 / 糊脸；改用万相 t2i——头身比自然、原生 1280x720=16:9。
注意：万相是重新生成的脸（非 InstantID 锁的 face16），风格与原 sweet_bob 同源但非同一张脸。
后续若要精确身份，可在万相好身材上再叠 InstantID 换脸（万相出比例 + InstantID 出身份）。
用法：unset 代理后 .venv/bin/python scripts/gen_halfbody_wanx.py [张数=4]
"""
import sys
from pathlib import Path
import os
import httpx
import dashscope
from dashscope import ImageSynthesis
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY")
MODEL = "wanx2.1-t2i-plus"
OUT = Path(__file__).resolve().parents[1] / "assets" / "avatar_facelock"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4

PROMPT = (
    "一位年轻甜美亲切的女性景区导游，波波头短发，海军蓝职业西装外套配工作证，"
    "半身构图从头到腰部完整可见，自然真实的头身比例，站姿端庄，"
    "双臂自然张开离开身体，双手抬到腰部高度手掌张开五指清晰可见，做欢迎的开放手势，"
    "正面面向镜头，直视前方，浅浅亲切的微笑不露齿，"
    "干净通透无眼袋的肌肤，精致小巧的鼻子，高颜值清纯赏心悦目，"
    "头发完整头顶上方留有空白，人物居中四周留白，"
    "柔和均匀的影棚光，纯色浅灰背景，超写实人像摄影，电影质感，8k，16:9横版构图"
)
NEG = (
    "大头娃娃，头身比例失调，头过大，手部畸形，多手指，少手指，手指残缺，手出画面，"
    "手臂被裁切，头顶被裁，刘海盖住眼睛，特写大头照，眼袋，黑眼圈，大鼻孔，"
    "露齿大笑，模糊，低分辨率，畸形，水印，文字"
)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(N):
        print(f"[{i+1}/{N}] 万相生成中...", flush=True)
        rsp = ImageSynthesis.call(model=MODEL, prompt=PROMPT, negative_prompt=NEG,
                                  n=1, size="1280*720")
        if rsp.status_code != 200:
            print(f"  ❌ 失败 {rsp.code} {rsp.message}", flush=True)
            continue
        url = rsp.output.results[0].url
        dst = OUT / f"wanx_halfbody_{i+1}.png"
        with httpx.Client(trust_env=False, timeout=120, follow_redirects=True) as c:
            dst.write_bytes(c.get(url).content)
        print(f"  ✅ {dst}", flush=True)


if __name__ == "__main__":
    main()
