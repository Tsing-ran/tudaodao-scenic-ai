"""为通用 F/M + 换装形象批量上景，准备 Flux Kontext 输入：
抠出人物 → 放进 16:9(1280×720) 与 9:16(720×1280) 灰底画布（上半/中景留白给 Flux 长景）。
复用 dh_ 上景配方：人物占比留余、四周灰底 → Flux 整体重绘出真上景。
用法: prep_flux_inputs.py <src.png> <out_prefix>
  产出 <out_prefix>_16x9.png 和 <out_prefix>_9x16.png
"""
import sys
from PIL import Image
import numpy as np
import rembg

SRC, PREFIX = sys.argv[1], sys.argv[2]
GREY = (231, 234, 239)

src = Image.open(SRC).convert("RGB")
cut = rembg.remove(src, session=rembg.new_session("birefnet-portrait"))   # RGBA
a = np.asarray(cut)[..., 3] > 128
ys, xs = np.where(a)
person = cut.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
pw, ph = person.size


def compose(W, H, h_frac, top_frac):
    canvas = Image.new("RGB", (W, H), GREY)
    target_h = int(h_frac * H)
    sc = target_h / ph
    nw, nh = int(pw * sc), int(ph * sc)
    pr = person.resize((nw, nh), Image.LANCZOS)
    px = (W - nw) // 2
    py = int(top_frac * H)
    canvas.paste(pr, (px, py), pr)
    return canvas


# 16:9：人物放小、头在上部、下方留空 → 逼 Flux 往下补躯干，治"头大身小"（半身中景、头身比正常）
compose(1280, 720, 0.55, 0.10).save(f"{PREFIX}_16x9.png")
# 9:16：人物上半居中、下半留白长身体+景（同 dh_ 竖版输入）
compose(720, 1280, 0.52, 0.07).save(f"{PREFIX}_9x16.png")
print(f"{PREFIX}: person {pw}x{ph} -> 16x9 + 9x16 done")
