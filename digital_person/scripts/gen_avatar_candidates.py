"""批量生成数字人形象候选图（通义万相 t2i），供挑选。

通用形象：一次出多种风格（现代/古风、男/女、不同气质），都满足 MuseTalk 选材标准
（正脸、嘴部清晰无遮挡、写实真人风、纯背景、竖版 720x1280）。
产物存 assets/avatar_candidates/（仓库目录，持久），挑中后再图生视频→烘 avatar。
"""
import os
from pathlib import Path

import dashscope
import httpx
from dashscope import ImageSynthesis
from dotenv import load_dotenv

MODEL = "wanx2.1-t2i-plus"   # plus 质量更好，挑选用
OUT = Path(__file__).resolve().parents[1] / "assets" / "avatar_candidates"

# MuseTalk 选材 + 审美通用后缀：正脸、嘴部清晰、柔光、纯背景、写实、竖版；
# 高颜值赏心悦目、端庄亲和、只微笑不大笑、发型不夸张
_SUFFIX = (
    "，正面半身肖像，直视镜头，端庄优雅的浅浅微笑，亲切温和有亲和力，"
    "不露齿大笑不夸张，高颜值精致五官赏心悦目，发型简洁自然不夸张，"
    "嘴部清晰无遮挡，柔和影棚光，纯色浅灰背景，超写实人像摄影，电影质感，8k，竖版构图"
)

CANDIDATES = {
    # —— 第一批：基础风格 ——
    "01_modern_female":  "一位亲切专业的现代女性景区讲解员，简约职业装，佩戴讲解员工作证，发型干练，面容清秀自然知性",
    "02_guofeng_female": "一位温婉的中国古典美女导游，淡雅汉服襦裙，简洁低挽的发髻配淡雅簪花，面容清秀古典端庄",
    "03_modern_male":    "一位儒雅的现代男性景区讲解员，得体浅色衬衫西装，面容亲和阳光，短发清爽",
    "04_guofeng_male":   "一位儒雅的中国古风男性书生导游，宋代文士青衫，束发，面容清俊温润",
    "05_young_female":   "一位青春活泼的年轻女性导游，休闲马甲制服，清爽马尾，面容甜美亲和",
    "06_mature_female":  "一位知性优雅的成熟女性文化讲解员，简约高级职业装，简洁低盘发，面容端庄大气",
    # —— 第二批（高颜值版）：服装/发型/脸型/性别拉开跨度，但统一高颜值 ——
    "07_ethnic_female":      "一位高颜值的少数民族风情美女导游，精致立体的五官，鲜艳华美的民族服饰与银饰头冠，乌黑长辫",
    "08_shorthair_female":   "一位高颜值气质美女讲解员，利落的齐耳短发，精致的瓜子脸，简约白衬衫，清冷高级的明星颜",
    "09_glasses_male":       "一位英俊儒雅的男性文化学者讲解员，斯文金丝眼镜，深邃立体的五官，剪裁合体的西装，成熟魅力",
    "10_curly_female":       "一位优雅高颜值的女性导游，蓬松的棕色长卷发，精致的鹅蛋脸，米色风衣，温柔大气的女神气质",
    "11_uniform_young_male": "一位阳光帅气的年轻男性景区制服导游，藏蓝色制服与帽子，清爽利落短发，英气的轮廓",
    "12_sweet_female":       "一位甜美可爱的年轻女性导游，清爽马尾，精致的圆脸，浅色polo衫，元气满满的邻家女神",
    "13_qipao_female":       "一位高颜值的旗袍女导游，简洁优雅的低盘发，精致古典的东方五官，改良真丝旗袍，东方美人气质",
    "14_handsome_male":      "一位成熟帅气的男性资深向导，硬朗深邃的五官，利落短发与淡淡胡茬，户外冲锋衣，沉稳有魅力",
    # —— 第三批：沿用"甜美女"成功方向的变体（年轻/甜美/清纯/亲和/高颜值）——
    "15_sweet_longhair":   "一位甜美清纯的年轻女性导游，柔顺的黑色长直发，精致甜美的鹅蛋脸，浅蓝色衬衫，温柔亲和的气质",
    "16_sweet_bob":        "一位甜美可爱的年轻女性讲解员，齐肩内扣短发波波头，精致圆润的脸，米白色针织衫，邻家女神感",
    "17_gentle_pretty":    "一位温柔知性的年轻美女导游，低马尾微卷，精致五官皮肤白皙，浅杏色西装外套，清纯气质",
    "18_lively_cute":      "一位元气满满的活泼甜美女导游，清爽高马尾，灵动的大眼睛，浅粉色景区马甲制服，青春洋溢",
    "19_pure_girl":        "一位清纯甜美的年轻女导游，自然空气刘海长发，干净白皙的脸庞，淡雅连衣裙，邻家少女般亲切",
    "20_warm_pretty":      "一位温暖亲和的甜美女性讲解员，柔和的中长发，弯弯的笑眼，浅色职业衬衫，治愈系气质",
}


def main():
    load_dotenv()
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, desc in CANDIDATES.items():
        dst = OUT / f"{name}.png"
        if dst.exists():
            print(f"[skip] {name} 已存在")
            continue
        print(f"[gen ] {name} …")
        rsp = ImageSynthesis.call(model=MODEL, prompt=desc + _SUFFIX, n=1, size="720*1280")
        if rsp.status_code != 200:
            print(f"  ❌ {name} 失败 {rsp.code} {rsp.message}")
            continue
        url = rsp.output.results[0].url
        with httpx.Client(trust_env=False, timeout=120, follow_redirects=True) as c:
            dst.write_bytes(c.get(url).content)
        print(f"  ✅ {dst}")
    print("全部完成 ->", OUT)


if __name__ == "__main__":
    main()
