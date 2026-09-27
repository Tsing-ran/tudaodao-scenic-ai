"""时间 + 天气感知：给导游"随机应变"的环境上下文（午后日晒→室内、下雨→带伞、傍晚→日落）。

- 时间：本地当前时刻 → 时段（清晨/上午/中午/下午/傍晚/夜晚），永远可用、零依赖。
- 天气：wttr.in 免费无 key 查询当地实时天气，带 30 分钟缓存 + 超时 + 优雅降级
        （取不到天气时只用时间，不影响主流程）。
导游据此自然给"避暑/带伞/防晒/看日落"等建议，体现真实导游对天气的适应职责。
"""
from __future__ import annotations

import datetime as dt
import time

import httpx

# scenic_id → 天气查询城市
SCENIC_CITY = {
    "lingshan": "无锡",
    "nihuawan": "无锡",
    "xihu": "杭州",
    "huangshan": "黄山",
    "gugong": "北京",
    "zhangjiajie": "张家界",
    "bingmayong": "西安",
    "mogaoku": "敦煌",
}

# wttr.in 英文天气描述 → 中文（覆盖常见项；未命中则保留原文）
_COND_CN = {
    "Sunny": "晴", "Clear": "晴", "Partly cloudy": "多云", "Cloudy": "阴",
    "Overcast": "阴", "Mist": "薄雾", "Fog": "雾", "Patchy rain nearby": "局部有雨",
    "Patchy rain possible": "可能有雨", "Light rain": "小雨", "Moderate rain": "中雨",
    "Heavy rain": "大雨", "Light drizzle": "毛毛雨", "Thundery outbreaks possible": "可能有雷阵雨",
    "Light snow": "小雪", "Moderate snow": "中雪", "Heavy snow": "大雪", "Patchy snow nearby": "局部有雪",
    "Haze": "雾霾", "Smoky haze": "雾霾", "Smoke": "烟霾", "Patchy light rain": "局部小雨",
    "Light rain shower": "阵雨", "Moderate or heavy rain shower": "大阵雨", "Blowing dust": "浮尘",
}

_CACHE: dict[str, tuple[float, str | None]] = {}   # city -> (ts, "中文天气 温度℃" 或 None)
_TTL = 1800  # 天气缓存 30 分钟


def _period(hour: int) -> str:
    if hour < 6:  return "凌晨"
    if hour < 9:  return "清晨"
    if hour < 11: return "上午"
    if hour < 13: return "中午"
    if hour < 17: return "下午"
    if hour < 19: return "傍晚"
    return "夜晚"


def _fetch_weather(city: str) -> str | None:
    """查 wttr.in，返回"多云 25℃"样式；失败返回 None。带 30 分钟缓存。"""
    now = time.time()
    hit = _CACHE.get(city)
    if hit and now - hit[0] < _TTL:
        return hit[1]
    result = None
    try:
        # trust_env=False：绕开环境里的 socks 代理（httpx 不支持 socks scheme），wttr.in 公网直连
        with httpx.Client(trust_env=False, timeout=5, follow_redirects=True) as c:
            r = c.get(f"https://wttr.in/{city}", params={"format": "%C|%t"})
        if r.status_code == 200 and "|" in r.text:
            cond_en, temp = (r.text.strip().split("|", 1) + [""])[:2]
            cond = _COND_CN.get(cond_en.strip(), cond_en.strip())
            temp = temp.strip().replace("+", "").replace("°C", "℃")
            result = f"{cond} {temp}".strip()
    except Exception:
        result = None
    _CACHE[city] = (now, result)
    return result


def env_brief(scenic_id: str, when: dt.datetime | None = None) -> str:
    """给导游 prompt 注入的一句话环境上下文（时间永远有，天气尽力而为）。"""
    when = when or dt.datetime.now()
    period = _period(when.hour)
    parts = [f"【实时环境】现在是 {when.month} 月 {when.day} 日{period}"]
    city = SCENIC_CITY.get(scenic_id)
    weather = _fetch_weather(city) if city else None
    if weather:
        parts.append(f"，{city}天气{weather}")
    parts.append("。请据此自然给出贴心建议（如午后日晒强先逛室内、下雨提醒带伞或走廊道、")
    parts.append("傍晚推荐日落机位、天热提醒补水），不要生硬罗列，也不要提及'系统/数据'。")
    return "".join(parts)
