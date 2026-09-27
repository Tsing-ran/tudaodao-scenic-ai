#!/usr/bin/env python
"""通义万相文生图出 sweet_bob 风格 16:9 中景半身像（脸质感最好；露完整上半身+头发、镜头拉远）。
复刻主形象 16_sweet_bob 审美，横版 1280x720，供数字人/InfiniteTalk 源图候选。
用法: DASHSCOPE_API_KEY=... python gen_sweet_bob_16x9.py [n]
"""
import os, sys, httpx
import dashscope
from dashscope import ImageSynthesis
from pathlib import Path

dashscope.api_key = os.environ["DASHSCOPE_API_KEY"]
OUT = Path("/tmp/sb16x9"); OUT.mkdir(parents=True, exist_ok=True)
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4

PROMPT = (
    "一位甜美清纯的年轻女性景区讲解员，正好20岁的成年女大学生，气质甜美年轻但是成年人不是小孩，"
    "精致漂亮的瓜子脸，小巧的尖下巴，流畅匀称的脸部线条，饱满的苹果肌带来甜美减龄感，"
    "明亮灵动的大眼睛，小巧精致的鼻子，水润的唇，皮肤白皙嫩滑，"
    "超高颜值，甜美清纯惹人喜爱，邻家姐姐般温柔亲和，"
    "齐肩内扣短发波波头，完整露出全部头发不被裁切，"
    "穿米白色浅色高领针织毛衣，毛衣完整覆盖双肩和手臂，端庄保守不露肩不露肤，"
    "完全正面面对镜头，脸正对镜头端端正正，不侧脸不歪头不低头，双眼平视镜头，"
    "甜甜的浅浅微笑，弯弯的笑眼，亲切温和，不露齿不夸张，"
    "发型简洁自然，完整露出全部头发，头顶留有充足空间不被裁切，"
    "整个头部和全部头发都完整在画面内，头顶上方留有明显空白，绝不裁切到头发或头顶，"
    "中景半身像，完整露出上半身到腰部，镜头适当拉远，自然真实的头身比例不显头大，"
    "柔和影棚光，纯色浅灰影棚背景，超写实人像摄影，电影质感，8k，16:9 横版构图"
)

NEG = "露肩, 挖肩装, 一字肩, 露肩装, 漏肩, 镂空装, 吊带, 露肤, 深色衣服, 头发被裁切, 头顶被切, 侧脸, 歪头, 大头, 头大, 丑, 模糊, 低龄儿童, 小孩"

rsp = ImageSynthesis.call(model="wanx2.1-t2i-plus", prompt=PROMPT, negative_prompt=NEG, n=N, size="1280*720")
if rsp.status_code != 200:
    sys.exit(f"FAIL {rsp.code} {rsp.message}")
with httpx.Client(trust_env=False, timeout=120, follow_redirects=True) as c:
    for i, r in enumerate(rsp.output.results):
        p = OUT / f"sb16x9_{i+1}.png"
        p.write_bytes(c.get(r.url).content)
        print("saved", p)
