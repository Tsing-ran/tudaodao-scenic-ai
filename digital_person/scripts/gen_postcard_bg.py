"""为「电子明信片」生成景区写意背景（通义万相 t2i）。

输出竖版 720x1280 到 webapp/public/postcard/{scenic}.jpg，作为 Canvas 明信片底图。
要求：写意/水彩国风、氛围柔和、顶部与底部留白便于叠加文字、画面无文字、无明显人物。
"""
import os
import sys
from pathlib import Path

import dashscope
import httpx
from dashscope import ImageSynthesis

MODEL = "wanx2.1-t2i-plus"
OUT = Path(__file__).resolve().parent.parent / "webapp" / "public" / "postcard"

# 每个景区一句写意 prompt（无文字、留白、柔和、适合做明信片底图）
SCENES = {
    "lingshan": "无锡灵山胜境，巍峨青铜大佛与金顶梵宫远景，太湖晨曦霞光，禅意祥和，中国风水彩写意插画",
    "nihuawan": "拈花湾禅意小镇，五重塔与香月花街灯笼，黄昏暖光，唯美禅境，中国风水彩写意插画",
    "xihu": "杭州西湖，断桥苏堤远山，烟雨朦胧荷影，江南水墨意境，柔和水彩写意插画",
    "huangshan": "黄山云海奇松，光明顶日出霞光，群峰耸立云雾缭绕，国风水墨写意插画",
    "gugong": "北京故宫角楼红墙金瓦，暮色霞光琉璃飞檐，庄重典雅，国风水彩写意插画",
}
SUFFIX = "，构图上下留白，柔和氛围，无任何文字水印，无明显人物，明信片背景图，竖版"


def main():
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
    if not dashscope.api_key:
        print("❌ 缺 DASHSCOPE_API_KEY"); sys.exit(1)
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for name, desc in SCENES.items():
        if only and name != only:
            continue
        dst = OUT / f"{name}.jpg"
        if dst.exists():
            print(f"[skip] {name} 已存在"); continue
        print(f"[gen ] {name} …", flush=True)
        rsp = ImageSynthesis.call(model=MODEL, prompt=desc + SUFFIX, n=1, size="720*1280")
        if rsp.status_code != 200:
            print(f"  ❌ {name} 失败 {rsp.code} {rsp.message}"); continue
        url = rsp.output.results[0].url
        with httpx.Client(trust_env=False, timeout=120, follow_redirects=True) as c:
            dst.write_bytes(c.get(url).content)
        print(f"  ✅ {dst}", flush=True)
    print("完成 ->", OUT)


if __name__ == "__main__":
    main()
