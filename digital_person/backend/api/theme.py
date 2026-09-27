"""景区主题色：每个景区一套品牌色（primary 主色 + sweet 暖点缀，OKLCH）。

- 客户端切景区时 GET /scenic/theme，把 primary/sweet 套到 CSS 变量 → 整 App 随景区换肤。
- 管理端可 PUT /scenic/theme 覆盖默认色（落 scenic_theme 表），GET /scenic/themes 取全部。
颜色按景区文化意象定：灵山禅金、拈花湾禅紫、西湖湖青、黄山墨松、故宫朱红。
"""
from fastapi import APIRouter
from pydantic import BaseModel

from backend.db.database import load_theme_override, save_theme
from backend.rag.pipeline import get_scenic_config
from backend.rag.scenic_types import scenic_type_of, type_label
from backend.core.color import to_hex_str, to_oklch_str

router = APIRouter(prefix="/scenic", tags=["theme"])

# 默认主题（OKLCH 字符串，前端直接 setProperty）
DEFAULT_THEMES: dict[str, dict] = {
    "lingshan":  {"name": "灵山·禅金", "primary": "oklch(0.575 0.2 268)",  "sweet": "oklch(0.77 0.13 70)"},
    "nihuawan":  {"name": "拈花湾·禅紫", "primary": "oklch(0.6 0.15 312)",   "sweet": "oklch(0.8 0.1 12)"},
    "xihu":      {"name": "西湖·湖青", "primary": "oklch(0.62 0.12 192)",  "sweet": "oklch(0.8 0.11 8)"},
    "huangshan": {"name": "黄山·墨松", "primary": "oklch(0.52 0.1 245)",   "sweet": "oklch(0.68 0.13 152)"},
    "gugong":    {"name": "故宫·朱红", "primary": "oklch(0.55 0.19 28)",   "sweet": "oklch(0.78 0.14 82)"},
}
# 未知景区落中立品牌主题（通用方案，不绑定任何景区）
_FALLBACK = {"name": "智游·导览", "primary": "oklch(0.575 0.2 268)", "sweet": "oklch(0.74 0.15 28)"}


class Theme(BaseModel):
    scenic_id: str
    name: str
    primary: str                     # OKLCH 字符串（游客端 webapp 直接喂 CSS 变量）
    sweet: str
    primary_hex: str = ""            # 同色的 Hex（管理端色板用，省去 OKLCH↔Hex 转换）
    sweet_hex: str = ""
    guide_name: str = "小游"
    scenic_type: str = ""            # 景区类型（religious/museum/mountain/urban_open/resort_town），驱动前端差异化
    type_label: str = ""             # 类型中文标签（如"博物展陈"），供 UI 直接展示


def _resolve(scenic_id: str) -> Theme:
    base = DEFAULT_THEMES.get(scenic_id, _FALLBACK)
    merged = {**base, **(load_theme_override(scenic_id) or {})}
    guide = get_scenic_config(scenic_id).get("guide_name") or "小游"
    return Theme(scenic_id=scenic_id, name=merged["name"],
                 primary=merged["primary"], sweet=merged["sweet"],
                 primary_hex=to_hex_str(merged["primary"]) or "",
                 sweet_hex=to_hex_str(merged["sweet"]) or "",
                 guide_name=guide,
                 scenic_type=scenic_type_of(scenic_id),
                 type_label=type_label(scenic_id))


@router.get("/theme", response_model=Theme)
def get_theme(scenic_id: str = "lingshan"):
    """取某景区主题（默认 + 管理端覆盖合并后）。"""
    return _resolve(scenic_id)


@router.get("/themes")
def list_themes():
    """全部景区主题（管理端列表用）。"""
    return {"themes": [_resolve(k) for k in DEFAULT_THEMES]}


class ThemeUpdate(BaseModel):
    scenic_id: str
    name: str | None = None
    # primary/sweet 收 OKLCH 或 Hex（自动识别）；也可用 primary_hex/sweet_hex 直接传 Hex。
    primary: str | None = None       # "oklch(0.6 0.18 30)" 或 "#7c5cff"
    sweet: str | None = None
    primary_hex: str | None = None   # "#7c5cff"（管理端色板直传）
    sweet_hex: str | None = None


@router.put("/theme", response_model=Theme)
def update_theme(u: ThemeUpdate):
    """管理端覆盖某景区主题（部分字段更新），返回合并后结果（含 OKLCH + Hex）。
    入参 primary/sweet 收 Hex 或 OKLCH 均可；内部统一规范成 OKLCH 落库（游客端要 OKLCH）。"""
    primary = u.primary or u.primary_hex
    sweet = u.sweet or u.sweet_hex
    save_theme(
        u.scenic_id, u.name,
        to_oklch_str(primary) if primary else None,
        to_oklch_str(sweet) if sweet else None,
    )
    return _resolve(u.scenic_id)
