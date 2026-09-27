"""通义万相「人景一体」身份库底板：人物 + 景区背景**一次性生成**（非抠图合成），16:9 与 9:16 双比例。

为什么不用抠图合成：rembg 把人贴到单独背景上 → 光照/景深/边缘不统一 → 永远"贴上去、格格不入"。
万相 t2i 一次性把人和场景协调生成 → 光影统一、零抠图边、人物完整自然在景中。
适用「身份库」（10 个不同的人，不需要锁脸）；**同脸换装**需锁身份，走 InstantID 人景一体
（`gen_avatar_inscene.py`），不在本脚本。

云 API（DashScope wanx2.1-t2i-plus），0 本地 GPU、不抢直播。
用法：unset 代理后 .venv/bin/python scripts/gen_avatar_inscene_wanx.py [scenic=lingshan] [id ...]
产物：assets/avatar_inscene_wanx/<id>__<scenic>__{16x9,9x16}.png（验观感后再部署进 ditto_avatars/）
"""
import os
import sys
import time
from pathlib import Path

import httpx
import dashscope
from dashscope import ImageSynthesis
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY")
MODEL = "wanx2.1-t2i-plus"
OUT = Path(__file__).resolve().parents[1] / "assets" / "avatar_inscene_wanx"

# 10 身份的气质/服装描述（不含背景——背景由 SCENES_CN 提供，一同生成）
LIBRARY = {
    "F1_modern":  "一位知性干练的现代女性景区讲解员，得体的海军蓝职业西装外套，佩戴讲解员工作证，利落的低马尾，面容清秀自然有气场",
    "F2_hanfu":   "一位温婉古典的中国古风女子导游，淡雅飘逸的汉服襦裙，低挽的发髻簪一支淡雅簪花，面容清丽柔美古典",
    "F3_youth":   "一位青春活泼甜美的年轻女性景区向导，清爽的景区马甲制服，高扎的清爽马尾，面容甜美灵动有朝气",
    "F4_qipao":   "一位东方典雅的女性向导，一袭改良丝绸旗袍尽显身段，优雅的盘发，面容精致温婉有韵味",
    "F5_ethnic":  "一位明艳的少数民族风情美女导游，鲜艳华美的民族服饰配精致银饰头冠，乌黑的长辫，面容立体明艳",
    "F6_mature":  "一位端庄大气知性的成熟女性文化讲解员，高级简约的职业套装，干净利落的低盘发，面容端庄优雅从容",
    "M1_modern":  "一位阳光亲和儒雅的现代男性景区讲解员，得体的浅色衬衫配西装，清爽的短发，面容俊朗温和有亲和力",
    "M2_scholar": "一位清俊温润的中国古风男性书生导游，宋代文士的青衫长袍，束发戴发冠，面容清隽儒雅",
    "M3_youth":   "一位青春朝气阳光的年轻男性景区向导，休闲的景区讲解员制服，利落短发，面容俊朗阳光有活力",
    "M4_business":"一位成熟稳重大气的男性向导，挺括的深色商务正装，沉稳的发型，面容硬朗成熟有气度",
}

# 8 景区背景（人站在其中，一同生成）——中文描述给万相
SCENES_CN = {
    "lingshan":    "身处灵山胜境的晨雾青山之间，远处雾霭中隐约可见高大的露天大佛与寺院宝塔剪影，温暖金色晨光，香雾缭绕的禅意氛围",
    "nihuawan":    "身处唐风禅意水乡小镇的暮色中，身后是白墙黛瓦的木构屋檐，暖黄灯笼柔光，淡淡樱花虚化光斑",
    "xihu":        "身处烟雨西湖畔，远处是雷峰塔与拱桥倒映在平静雾气朦胧的湖面上，柔和的青灰色空气透视薄雾",
    "huangshan":   "身处黄山云海之上的观景台，身后是翻涌的云海、远处的花岗岩奇峰与迎客松剪影，金色光辉",
    "gugong":      "身处北京故宫，身后是金色琉璃瓦宫殿飞檐与朱红宫墙，金黄银杏叶，柔和晨光",
    "zhangjiajie": "身处张家界，身后是云雾缭绕、高耸入云的石英砂岩峰林，苍翠葱郁，空灵缥缈",
    "bingmayong":  "身处暖琥珀色灯光的兵马俑博物馆展厅，身后是柔和虚化的兵马俑军阵坑",
    "mogaoku":     "身处敦煌金色鸣沙山与月牙泉前，温暖沙色调，清澈黎明天空",
}

SUFFIX = (
    "，近景胸像特写，肩部以上构图，面部清晰且占画面较大比例、居中略偏上，直视镜头，亲切微笑不露齿，"
    "高颜值精致五官赏心悦目，皮肤干净通透，眼神温和有亲和力，嘴部清晰无遮挡，"
    "柔和的环境光自然照亮人物、与背景光影统一，浅景深电影感虚化背景，"
    "超写实人像摄影，电影质感，自然色调，8k"
)
NEG = ("抠图，贴图，拼贴，悬浮，纯色背景，影棚背景，硬边缘，丑陋，畸形五官，斜视，歪嘴，"
       "露齿大笑，眼袋，黑眼圈，浓妆，模糊，低分辨率，多余的手，水印，文字")

SIZES = {"16x9": "1280*720", "9x16": "720*1280"}

_C = httpx.Client(trust_env=False, timeout=120, follow_redirects=True)


def main():
    scenic = sys.argv[1] if len(sys.argv) > 1 else "lingshan"
    if scenic not in SCENES_CN:
        sys.exit(f"未知景区 {scenic}（可选：{','.join(SCENES_CN)}）")
    ids = sys.argv[2:] or list(LIBRARY)
    OUT.mkdir(parents=True, exist_ok=True)
    scene = SCENES_CN[scenic]
    for aid in ids:
        if aid not in LIBRARY:
            print(f"  跳过未知 id {aid}", flush=True); continue
        prompt = LIBRARY[aid] + "，" + scene + SUFFIX
        for asp, size in SIZES.items():
            dst = OUT / f"{aid}__{scenic}__{asp}.png"
            if dst.exists():                       # 断点续传：已生成的跳过
                print(f"  ⏭ {dst.name} 已存在", flush=True); continue
            print(f"[{aid}__{scenic}__{asp}] 万相生成中（{size}）…", flush=True)
            for attempt in range(4):               # 单张失败重试，绝不让整批崩
                try:
                    r = ImageSynthesis.call(model=MODEL, prompt=prompt, negative_prompt=NEG, n=1, size=size)
                    if r.status_code != 200:
                        print(f"  ⚠️ {aid} {asp} {r.code} {r.message}（重试 {attempt+1}/4）", flush=True)
                        time.sleep(6); continue
                    dst.write_bytes(_C.get(r.output.results[0].url).content)
                    print(f"  ✅ {dst}", flush=True); break
                except Exception as e:
                    print(f"  ⚠️ {aid} {asp} 异常 {type(e).__name__}: {str(e)[:120]}（重试 {attempt+1}/4）", flush=True)
                    time.sleep(6)
            else:
                print(f"  ❌ {aid} {asp} 四次失败，跳过", flush=True)
    print("完成 →", OUT)


if __name__ == "__main__":
    main()
