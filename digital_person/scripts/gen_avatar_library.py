"""通义万相批量生成「数字人形象素材库」：高颜值 · 男女 · 服装气质各异（10 个不同的人）。

云 API（DashScope wanx2.1-t2i-plus），不占本地/AutoDL GPU、不打扰实时数字人。竖版 720x1280。
（旧 ComfyUI SDXL 版已弃用——万相对中文美人质感更好、零 GPU 占用、不与实时数字人争显存。）
用法：unset 代理后 .venv/bin/python scripts/gen_avatar_library.py [仅生成某些id，空=全部]
产物：assets/avatar_library/<id>.png
"""
import sys, os
from pathlib import Path
import httpx
import dashscope
from dashscope import ImageSynthesis
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY")
MODEL = "wanx2.1-t2i-plus"
OUT = Path(__file__).resolve().parents[1] / "assets" / "avatar_library"

# 高颜值 + 选材统一后缀（正脸、嘴清晰、柔光、纯背景、写实、竖版）
SUFFIX = (
    "，正面半身肖像，直视镜头，浅浅亲切的微笑不露齿，高颜值精致五官赏心悦目，"
    "皮肤干净通透无瑕，眼神温和有亲和力，发型自然不夸张，嘴部清晰无遮挡，"
    "柔和均匀的影棚光，纯色浅灰背景，超写实人像摄影，电影质感，8k，竖版构图"
)
NEG = "丑陋，畸形五官，斜视，大小眼，歪嘴，露齿大笑，眼袋，黑眼圈，浓妆，模糊，低分辨率，多余的手，水印，文字"

LIBRARY = {
    # —— 女 ——
    "F1_modern":  "一位知性干练的现代女性景区讲解员，得体的海军蓝职业西装外套，佩戴讲解员工作证，利落的低马尾，面容清秀自然有气场",
    "F2_hanfu":   "一位温婉古典的中国古风女子导游，淡雅飘逸的汉服襦裙，低挽的发髻簪一支淡雅簪花，面容清丽柔美古典",
    "F3_youth":   "一位青春活泼甜美的年轻女性景区向导，清爽的景区马甲制服，高扎的清爽马尾，面容甜美灵动有朝气",
    "F4_qipao":   "一位东方典雅的女性，一袭改良丝绸旗袍尽显身段，优雅的盘发，面容精致温婉有韵味",
    "F5_ethnic":  "一位明艳的少数民族风情美女导游，鲜艳华美的民族服饰配精致银饰头冠，乌黑的长辫，面容立体明艳",
    "F6_mature":  "一位端庄大气知性的成熟女性文化讲解员，高级简约的职业套装，干净利落的低盘发，面容端庄优雅从容",
    # —— 男 ——
    "M1_modern":  "一位阳光亲和儒雅的现代男性景区讲解员，得体的浅色衬衫配西装，清爽的短发，面容俊朗温和有亲和力",
    "M2_scholar": "一位清俊温润的中国古风男性书生导游，宋代文士的青衫长袍，束发戴发冠，面容清隽儒雅",
    "M3_youth":   "一位青春朝气阳光的年轻男性景区向导，休闲的景区讲解员制服，利落短发，面容俊朗阳光有活力",
    "M4_business":"一位成熟稳重大气的男性向导，挺括的深色商务正装，沉稳的发型，面容硬朗成熟有气度",
}

_C = httpx.Client(trust_env=False, timeout=120, follow_redirects=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    for aid, desc in LIBRARY.items():
        if only and aid not in only:
            continue
        print(f"[{aid}] 万相生成中…", flush=True)
        r = ImageSynthesis.call(model=MODEL, prompt=desc + SUFFIX, negative_prompt=NEG, n=1, size="720*1280")
        if r.status_code != 200:
            print(f"  ❌ {aid} 失败 {r.code} {r.message}", flush=True)
            continue
        dst = OUT / f"{aid}.png"
        dst.write_bytes(_C.get(r.output.results[0].url).content)
        print(f"  ✅ {dst}", flush=True)
    print("完成 →", OUT)


if __name__ == "__main__":
    main()
