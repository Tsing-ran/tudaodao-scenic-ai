"""跟我游 · 逐站导览 + 设施速查。

- 路线/站点：灵山取自官方资料《灵山胜境游览指南》真实推荐路线（历史/自然/亲子三线）；
  其余景区用公认经典游线。站点只给「名称 + 一句指路」，深度讲解由数字人实时走 RAG（/live/ask 该站点名）。
- 设施：按景区真实地标方位给出参考点位（卫生间/餐饮/休息/医务/母婴/无障碍）。
"""
import math

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/tour", tags=["tour"])


# ── 路线数据（station: name + 指路 hint）──────────────────────────
def _st(name: str, hint: str = "") -> dict:
    return {"name": name, "hint": hint}


TOURS: dict[str, list[dict]] = {
    "lingshan": [
        {
            "id": "history", "title": "历史文化深度游", "duration": "约 6 小时",
            "tag": "历史人文", "group": "adult",
            "stations": [
                _st("灵山大照壁", "南门入园即见，华夏第一壁，先在此合影"),
                _st("胜境广场", "照壁正前方开阔广场，步行约 3 分钟"),
                _st("佛手广场", "广场尽头，可摸天下第一掌祈福"),
                _st("祥符禅寺", "佛手广场东侧，千年古刹"),
                _st("杏坛广场", "出禅寺沿主道北行约 5 分钟"),
                _st("佛前广场", "杏坛广场尽头，灵山大佛脚下"),
                _st("灵山大佛", "登台阶仰瞻 88 米露天青铜大佛"),
                _st("灵山梵宫", "大佛西侧，佛教艺术殿堂，需安检"),
                _st("五印坛城", "梵宫旁，藏传佛教坛城"),
                _st("三圣殿", "返程经三圣殿，佛教历史展示后出口"),
            ],
        },
        {
            "id": "nature", "title": "自然风光全景游", "duration": "约 5 小时",
            "tag": "自然风光", "group": "couple",
            "stations": [
                _st("佛足坛", "南门入园右行，先观佛足"),
                _st("九龙灌浴", "佛足坛旁，整点有动态音乐喷泉表演"),
                _st("菩提大道", "沿道北行，一侧可眺太湖风光"),
                _st("灵山大佛", "大道尽头登顶俯瞰全景"),
                _st("曼飞龙塔", "大佛西南，傣式金塔园林"),
                _st("灵山精舍", "塔旁禅意园林，适合小憩"),
                _st("梵宫广场", "精舍外广场，傍晚灯光最美后出口"),
            ],
        },
        {
            "id": "family", "title": "亲子家庭轻松游", "duration": "约 4 小时",
            "tag": "亲子互动", "group": "family_kids",
            "stations": [
                _st("九龙灌浴", "南门入园直行，先看动态表演孩子最爱"),
                _st("佛手广场", "表演场北侧，带孩子摸天下第一掌"),
                _st("百子戏弥勒", "广场旁，百子嬉戏铜雕，亲子互动点"),
                _st("灵山梵宫", "欣赏穹顶艺术，注意安检与秩序"),
                _st("五印坛城", "梵宫旁体验藏式文化后出口"),
            ],
        },
    ],
    "xihu": [
        {
            "id": "classic", "title": "西湖经典一日", "duration": "约 5 小时",
            "tag": "自然风光", "group": "couple",
            "stations": [
                _st("断桥残雪", "北山街起点，白娘子传说之地"),
                _st("白堤", "沿堤西行，两侧桃柳夹道"),
                _st("平湖秋月", "白堤尽头临湖赏景平台"),
                _st("孤山", "西泠桥畔，西湖唯一天然岛屿"),
                _st("苏堤春晓", "跨湖长堤，六桥烟柳"),
                _st("花港观鱼", "苏堤南段西侧红鱼池"),
                _st("雷峰塔", "南屏山下，登塔俯瞰全湖后结束"),
            ],
        },
    ],
    "huangshan": [
        {
            "id": "classic", "title": "黄山精华登顶", "duration": "约 7 小时",
            "tag": "自然风光", "group": "adult",
            "stations": [
                _st("云谷寺", "后山登山口，可乘索道上行"),
                _st("白鹅岭", "索道上站，雲海观景起点"),
                _st("始信峰", "奇松云海第一处，沿步道约 20 分钟"),
                _st("光明顶", "黄山第二高峰，日出云海最佳"),
                _st("飞来石", "光明顶西侧巨石，《红楼梦》取景"),
                _st("迎客松", "玉屏楼前，黄山名片"),
                _st("玉屏楼", "前山下行，乘索道返回"),
            ],
        },
    ],
    "gugong": [
        {
            "id": "central", "title": "故宫中轴线精华", "duration": "约 4 小时",
            "tag": "历史人文", "group": "adult",
            "stations": [
                _st("午门", "故宫正门，验票入内"),
                _st("太和门", "过金水桥即达，太和殿前导"),
                _st("太和殿", "三大殿之首，皇帝登基大典处"),
                _st("中和殿", "太和殿后，方形攒尖顶"),
                _st("保和殿", "三大殿之末，殿试之所"),
                _st("乾清宫", "内廷正殿，帝王寝居理政"),
                _st("御花园", "中轴最北，古木奇石"),
                _st("神武门", "御花园后出宫，对望景山"),
            ],
        },
    ],
    "nihuawan": [
        {
            "id": "zen", "title": "拈花湾禅意慢行", "duration": "约 3 小时",
            "tag": "禅意文化", "group": "couple",
            "stations": [
                _st("香月花街", "小镇主街，禅意店铺林立"),
                _st("拈花塔", "街尽头地标五重塔，登塔观景"),
                _st("半山禅道", "沿山道缓行的禅意小径"),
                _st("鹿鸣谷", "林间静谧处，适合冥想小憩"),
                _st("禅行剧场", "夜场《禅行》灯光秀，压轴体验"),
            ],
        },
    ],
}

# ── 设施数据（type → 参考点位）────────────────────────────────────
FAC_TYPES = [
    {"id": "toilet", "label": "卫生间", "emoji": "🚻"},
    {"id": "food", "label": "餐饮", "emoji": "🍜"},
    {"id": "rest", "label": "休息区", "emoji": "🪑"},
    {"id": "medical", "label": "医务点", "emoji": "⛑️"},
    {"id": "baby", "label": "母婴室", "emoji": "🍼"},
    {"id": "access", "label": "无障碍", "emoji": "♿"},
]

FACILITIES: dict[str, dict[str, list[str]]] = {
    "lingshan": {
        "toilet": ["胜境广场东侧", "九龙灌浴表演场旁", "梵宫一层", "祥符禅寺出口"],
        "food": ["梵宫文化餐厅（正餐）", "胜境广场小吃区", "九龙灌浴旁茶歇亭"],
        "rest": ["菩提大道沿途座椅", "灵山精舍禅意休息区", "佛前广场遮阳棚"],
        "medical": ["游客中心医务室", "梵宫安检口旁急救点"],
        "baby": ["游客中心母婴室", "梵宫一层母婴室"],
        "access": ["全程无障碍坡道", "游客中心可租轮椅", "梵宫设无障碍电梯"],
    },
    "xihu": {
        "toilet": ["断桥北侧", "苏堤花港入口", "雷峰塔景区内"],
        "food": ["楼外楼（孤山店）", "湖滨步行街餐饮区", "花港观鱼茶室"],
        "rest": ["白堤沿途长椅", "孤山林荫座椅", "苏堤六桥休憩点"],
        "medical": ["湖滨游客中心医务点"],
        "baby": ["湖滨游客中心母婴室"],
        "access": ["环湖步道平缓无障碍", "游客中心租轮椅"],
    },
    "huangshan": {
        "toilet": ["云谷寺站", "白鹅岭索道站", "光明顶气象站旁", "玉屏楼"],
        "food": ["光明顶山顶餐厅", "白云宾馆餐饮", "玉屏楼小卖部"],
        "rest": ["始信峰观景台座椅", "光明顶休息平台"],
        "medical": ["光明顶医疗救助点", "玉屏楼救助站"],
        "baby": ["温泉景区游客中心母婴室"],
        "access": ["索道代步（不建议轮椅登山）", "温泉区无障碍设施"],
    },
    "gugong": {
        "toilet": ["午门内东西两侧", "太和殿广场两庑", "御花园东侧"],
        "food": ["冰窖餐厅", "故宫角楼咖啡", "神武门外快餐区"],
        "rest": ["太和门廊下座椅", "御花园树荫长椅"],
        "medical": ["午门内医务室", "东华门急救点"],
        "baby": ["午门检票口母婴室"],
        "access": ["主中轴备无障碍坡道", "可借轮椅（午门）"],
    },
    "nihuawan": {
        "toilet": ["香月花街中段", "拈花塔旁", "禅行剧场入口"],
        "food": ["香月花街小吃", "波罗蜜餐厅", "禅意茶馆"],
        "rest": ["花街廊亭", "鹿鸣谷林间座椅"],
        "medical": ["小镇游客中心医务点"],
        "baby": ["游客中心母婴室"],
        "access": ["小镇步道平缓", "游客中心租轮椅/婴儿车"],
    },
}


class Station(BaseModel):
    name: str
    hint: str = ""


class Route(BaseModel):
    id: str
    title: str
    duration: str
    tag: str
    group: str
    stations: list[Station]


class RoutesResponse(BaseModel):
    scenic_id: str
    routes: list[Route]


@router.get("/routes", response_model=RoutesResponse)
def tour_routes(scenic_id: str = "lingshan"):
    return RoutesResponse(scenic_id=scenic_id, routes=TOURS.get(scenic_id, []))


class FacilityGroup(BaseModel):
    id: str
    label: str
    emoji: str
    points: list[str]


class FacilitiesResponse(BaseModel):
    scenic_id: str
    groups: list[FacilityGroup]


@router.get("/facilities", response_model=FacilitiesResponse)
def tour_facilities(scenic_id: str = "lingshan"):
    data = FACILITIES.get(scenic_id, {})
    groups = [
        FacilityGroup(id=t["id"], label=t["label"], emoji=t["emoji"], points=data.get(t["id"], []))
        for t in FAC_TYPES if data.get(t["id"])
    ]
    return FacilitiesResponse(scenic_id=scenic_id, groups=groups)


# ── GPS 定位讲解：景点坐标（GCJ-02，高德底图同基准）+ 最近景点计算 ──────────────────
# 注：游客端已改为前端用 routeData 的 GCJ-02 坐标直接算最近点（见 lib/geo.ts），此处供后端消费方备用。
# lingshan 坐标与 routeData 对齐（高德 POI 检索真值）；⚠️其余景区仍为粗略近似，接入前需补真实 GCJ-02。
COORDS: dict[str, dict[str, tuple[float, float]]] = {
    "lingshan": {
        "灵山胜境门楼": (31.422257, 120.101730), "五印坛城": (31.424676, 120.103054),
        "九龙灌浴": (31.424601, 120.099984), "阿育王柱": (31.426188, 120.099261),
        "祥符禅寺": (31.427949, 120.098012), "灵山大佛": (31.430194, 120.096477),
        "灵山梵宫": (31.428218, 120.102420),
    },
    "nihuawan": {
        "香月花街": (31.4382, 120.0852), "拈花塔": (31.4375, 120.0858),
        "鹿鸣谷": (31.4360, 120.0840), "禅行剧场": (31.4388, 120.0848),
    },
    "xihu": {
        "断桥残雪": (30.2595, 120.1490), "白堤": (30.2580, 120.1450),
        "平湖秋月": (30.2570, 120.1420), "孤山": (30.2565, 120.1400),
        "苏堤春晓": (30.2480, 120.1380), "花港观鱼": (30.2400, 120.1390),
        "雷峰塔": (30.2320, 120.1485),
    },
    "huangshan": {
        "云谷寺": (30.1450, 118.1700), "白鹅岭": (30.1380, 118.1660),
        "始信峰": (30.1420, 118.1640), "光明顶": (30.1300, 118.1560),
        "迎客松": (30.1280, 118.1530), "玉屏楼": (30.1275, 118.1525),
    },
    "gugong": {
        "午门": (39.9163, 116.3972), "太和殿": (39.9176, 116.3972),
        "中和殿": (39.9182, 116.3972), "保和殿": (39.9187, 116.3972),
        "乾清宫": (39.9197, 116.3972), "御花园": (39.9210, 116.3972),
        "神武门": (39.9220, 116.3972),
    },
}

# 演示用「模拟位置」预设：景区入口/中心点等，便于室内/异地演示 GPS 逻辑
SIM_SPOTS: dict[str, list[dict]] = {
    "lingshan": [
        {"label": "景区入口（门楼）", "lat": 31.422257, "lng": 120.101730},
        {"label": "灵山大佛", "lat": 31.430194, "lng": 120.096477},
        {"label": "灵山梵宫", "lat": 31.428218, "lng": 120.102420},
    ],
    "xihu": [
        {"label": "断桥附近", "lat": 30.2596, "lng": 120.1491},
        {"label": "苏堤入口", "lat": 30.2485, "lng": 120.1381},
    ],
}


def _haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    """两经纬度间距离（米）。"""
    r = 6371000
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = math.radians(b[0] - a[0]); dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


class NearbyItem(BaseModel):
    name: str
    distance: int   # 米


class NearbyResponse(BaseModel):
    scenic_id: str
    nearest: NearbyItem | None = None
    items: list[NearbyItem] = []
    sim_spots: list[dict] = []


@router.get("/nearby", response_model=NearbyResponse)
def tour_nearby(scenic_id: str = "lingshan", lat: float | None = None, lng: float | None = None):
    """给定经纬度，返回该景区内最近的景点（按距离排序）。无坐标时只回 sim_spots 供演示。"""
    spots = COORDS.get(scenic_id, {})
    sims = SIM_SPOTS.get(scenic_id, [])
    if lat is None or lng is None or not spots:
        return NearbyResponse(scenic_id=scenic_id, sim_spots=sims)
    here = (lat, lng)
    ranked = sorted(((n, int(_haversine(here, c))) for n, c in spots.items()), key=lambda x: x[1])
    items = [NearbyItem(name=n, distance=d) for n, d in ranked[:4]]
    return NearbyResponse(scenic_id=scenic_id, nearest=items[0] if items else None, items=items, sim_spots=sims)
