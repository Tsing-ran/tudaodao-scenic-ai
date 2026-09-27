"""OKLCH ↔ Hex 颜色转换（无第三方依赖，Björn Ottosson 的 OKLab 公式）。

主题接口内部存 OKLCH（游客端 webapp 直接喂 CSS 变量），但管理端色板用 Hex，
故 GET 两种都给、PUT 两种都收。本模块负责双向转换 + OKLCH 字符串解析/格式化。
"""
from __future__ import annotations

import math
import re


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    c = max(0.0, min(1.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def hex_to_oklch(hex_str: str) -> tuple[float, float, float]:
    """#rrggbb → (L, C, H度)。"""
    h = hex_str.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    r, g, b = _srgb_to_linear(r), _srgb_to_linear(g), _srgb_to_linear(b)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (v ** (1 / 3) if v >= 0 else -((-v) ** (1 / 3)) for v in (l, m, s))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.hypot(a, bb)
    H = math.degrees(math.atan2(bb, a)) % 360
    return L, C, H


def oklch_to_hex(L: float, C: float, H: float) -> str:
    """(L, C, H度) → #rrggbb（超出 sRGB 色域时夹取最近可表示色）。"""
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    rgb = (round(_linear_to_srgb(r) * 255), round(_linear_to_srgb(g) * 255), round(_linear_to_srgb(bl) * 255))
    return "#" + "".join(f"{max(0, min(255, v)):02x}" for v in rgb)


_OKLCH_RE = re.compile(r"oklch\(\s*([\d.]+%?)\s+([\d.]+)\s+([\d.]+)", re.I)


def parse_oklch(s: str) -> tuple[float, float, float] | None:
    """'oklch(0.575 0.2 268)' → (L, C, H)；L 支持百分号。解析失败返回 None。"""
    m = _OKLCH_RE.search(s or "")
    if not m:
        return None
    l_raw = m.group(1)
    L = float(l_raw[:-1]) / 100 if l_raw.endswith("%") else float(l_raw)
    return L, float(m.group(2)), float(m.group(3))


def format_oklch(L: float, C: float, H: float) -> str:
    return f"oklch({L:.4g} {C:.4g} {H:.4g})"


def to_oklch_str(value: str) -> str:
    """把任意颜色串（hex 或 oklch）规范成 oklch 字符串（用于落库，游客端要 OKLCH）。"""
    v = (value or "").strip()
    if v.startswith("#") or re.fullmatch(r"[0-9a-fA-F]{3}|[0-9a-fA-F]{6}", v):
        return format_oklch(*hex_to_oklch(v))
    return v  # 已是 oklch（或其它 CSS 颜色），原样存


def to_hex_str(value: str) -> str | None:
    """把任意颜色串（oklch 或 hex）转成 hex；无法解析返回 None。"""
    v = (value or "").strip()
    if v.startswith("#"):
        return v.lower()
    parsed = parse_oklch(v)
    return oklch_to_hex(*parsed) if parsed else None
