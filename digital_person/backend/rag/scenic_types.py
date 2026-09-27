"""景区类型画像（scenic_type × TYPE_PROFILES）——"换库不换码"的差异化底座。

立意：泛化 ≠ 千人一面。同一套代码，按景区**类型**呈现恰当的不同口吻与提醒。
`scenic_type` 管"景区是什么"，与 `group_type`（同行人）、`situation`（游客自身）正交。

**铁律：类型差异只进数据，不进 if-else 代码分支**（守住"换库不换码"）。
新景区接入 = 在 SCENIC_TYPE 里多选一个类型，零新代码路径。

注入口径（与客流/天气同一个口子 `_directive_with_context`）：
  - `persona`：讲解口吻（事实中性，仅调语气/侧重）→ 注入**全部意图**，让 qa 也带景区气质；
    因不改事实，准确率测试（关键词命中）不受影响。
  - `reminders`：主动提醒（礼仪/预约/安全/接驳）→ 仅注入 navigation/recommend，避免 qa prompt 膨胀。
  - `reco`：推荐准则 → 供 recommend 端点拼进"挑卡"系统提示，让不同类型景区的推荐侧重不同。
"""

# scenic_id → 类型。现有 8 景区天然覆盖 5 类（religious / museum / mountain / urban_open / resort_town）。
SCENIC_TYPE: dict[str, str] = {
    "lingshan":    "religious",    # 宗教人文：礼仪禁忌、祈福、演出场次
    "nihuawan":    "resort_town",  # 度假小镇：住宿餐饮、夜游夜演、慢节奏
    "xihu":        "urban_open",   # 开放城市：交通接驳、夜景、免票无边界
    "huangshan":   "mountain",     # 自然山岳：安全体力、天气、索道、日出
    "gugong":      "museum",       # 博物遗址：预约限流、文物保护、单向动线
    "zhangjiajie": "mountain",
    "bingmayong":  "museum",
    "mogaoku":     "museum",
}

# 类型画像（纯数据表）。每条 persona ≤2 句、事实中性；reminders/reco 各 1 句，避免 prompt 膨胀。
TYPE_PROFILES: dict[str, dict[str, str]] = {
    "religious": {
        "label": "禅意宗教",
        "persona": (
            "【讲解风格】这里是禅意宗教场所，语气温润平和、庄重而不刻板，"
            "可适度点出禅意与文化意涵，但始终以事实为先。"
        ),
        "reminders": (
            "请主动留意提示：殿内礼仪与拍照规定、祈福参拜的流程与寓意；"
            "遇有定时演出（如九龙灌浴）可主动告知场次与赶场所需时间。"
        ),
        "reco": "侧重文化体验与祈福节奏，把握心静慢行的氛围，别堆砌赶场。",
    },
    "museum": {
        "label": "博物展陈",
        "persona": (
            "【讲解风格】这里是博物/遗址类场所，语气沉稳考据、像一位文博讲解员，"
            "重史实细节与年代脉络，娓娓道来而不浮夸。"
        ),
        "reminders": (
            "请主动留意提示：预约与限流规定、文物保护要求（部分区域禁止拍照或禁用闪光灯）、"
            "单向参观动线，合理安排时间避免临近闭馆错过重点。"
        ),
        "reco": "侧重深度讲解与中轴/主线动线，提醒预约配额，宁可少而精。",
    },
    "mountain": {
        "label": "自然山岳",
        "persona": (
            "【讲解风格】这里是自然山岳景区，语气像稳重可靠的向导，"
            "把安全与体力放在前面，讲景之余不忘提醒量力而行。"
        ),
        "reminders": (
            "请主动结合天气与时段提示：山顶温差与防晒防雨、索道缆车的运营、"
            "日出日落最佳时刻，并按体力推荐分级路线。"
        ),
        "reco": "侧重体力分配与索道接驳，按时段避开陡升路段，安全第一。",
    },
    "urban_open": {
        "label": "开放城市",
        "persona": (
            "【讲解风格】这里是开放式城市山水，语气轻松生活化，"
            "像本地朋友带逛，兼顾人文典故与闲适意趣。"
        ),
        "reminders": (
            "可主动提示：交通接驳（地铁、公交、游船）、夜景与亮灯时段；"
            "景区开放无边界，按兴趣自由串联即可。"
        ),
        "reco": "侧重交通串联与步移景异，按兴趣松散组合，不必拘泥固定路线。",
    },
    "resort_town": {
        "label": "度假小镇",
        "persona": (
            "【讲解风格】这里是度假小镇，语气从容慢生活、像生活方式主理人，"
            "鼓励放慢脚步、重体验而非赶景点。"
        ),
        "reminders": (
            "可主动提示：住宿与餐饮、夜游与夜间演出的时段；"
            "建议傍晚留下来感受灯火与禅意夜色，不必赶行程。"
        ),
        "reco": "侧重慢节奏与夜游体验，留白胜过塞满，傍晚是重头戏。",
    },
}

# 未知景区/类型的中性兜底：空串 → 不注入任何文字 → prompt 与原状逐字节一致（零准确率影响）。
_NEUTRAL = {"label": "", "persona": "", "reminders": "", "reco": ""}


def scenic_type_of(scenic_id: str) -> str:
    """景区 → 类型（未登记返回空串）。"""
    return SCENIC_TYPE.get(scenic_id, "")


def _profile(scenic_id: str) -> dict[str, str]:
    return TYPE_PROFILES.get(SCENIC_TYPE.get(scenic_id, ""), _NEUTRAL)


def type_label(scenic_id: str) -> str:
    """类型中文标签（前端差异化展示用，如"博物展陈"）。未登记景区返回空串。"""
    return _profile(scenic_id)["label"]


def type_persona_directive(scenic_id: str) -> str:
    """讲解口吻指令（事实中性，注入全部意图）。未登记景区返回空串。"""
    return _profile(scenic_id)["persona"]


def type_reminder_directive(scenic_id: str) -> str:
    """主动提醒指令（礼仪/预约/安全/接驳，仅注入路线/推荐意图）。未登记景区返回空串。"""
    return _profile(scenic_id)["reminders"]


def type_reco_guideline(scenic_id: str) -> str:
    """推荐准则（供 recommend 端点拼进系统提示）。未登记景区返回空串。"""
    return _profile(scenic_id)["reco"]
