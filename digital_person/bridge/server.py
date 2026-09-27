"""
RAG → 数字人 桥接层（本地运行，串联问答与口型驱动）

部署位置：本地 4080 机器，与 LiveTalking 同机（内部 localhost 调用，零公网暴露）。

职责（把两条孤立的服务接成一条链）：
  游客提问 → 本桥接 /live/ask
    1) 调 RAG_BASE/chat        拿 reply / emotion / intent
    2) 读 digital-human/config 把占位 avatar_id/voice_id 翻译成
       「真实的 LiveTalking avatar」与「真实的 edge-TTS 音色」
    3) 调 LIVETALKING_BASE/human(echo) 让数字人用该音色把 reply 说出来

  形象切换：avatar 是「连接级」参数（在 LiveTalking /offer 建连时指定），
  所以前端连接前先调 /live/avatar 拿到该景区当前 avatar_id，再传给 /offer。

启动：
  cd /home/jiale/Desktop/Digital_Person
  .venv/bin/uvicorn bridge.server:app --host 0.0.0.0 --port 9000

可用环境变量覆盖后端地址（演示时 RAG 可指向本地 GPU 实例以求最低延迟，
也可指向 ECS 公网 http://116.62.136.211:8000）：
  RAG_BASE=http://localhost:8000  LIVETALKING_BASE=http://localhost:8010
"""
import asyncio
import json
import os
import pathlib
import re
import time
import uuid

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

RAG_BASE = os.environ.get("RAG_BASE", "http://localhost:8000").rstrip("/")
LIVETALKING_BASE = os.environ.get("LIVETALKING_BASE", "http://localhost:8010").rstrip("/")
# 大屏竖版数字人第二实例（9:16，端口 8011，推流 livestream2）——供游客端大屏 web（队友）用
LIVETALKING_BASE_2 = os.environ.get("LIVETALKING_BASE_2", "http://localhost:8011").rstrip("/")
SRS_FLV2 = os.environ.get("SRS_FLV2", "http://localhost:8080/live/livestream2.flv").rstrip("/")
# SRS 的 HTTP-FLV 直播流地址（RTMP 模式下 LiveTalking 推到 SRS，浏览器从这里拉）
SRS_FLV = os.environ.get("SRS_FLV", "http://localhost:8080/live/livestream.flv").rstrip("/")
# SRS 的 HLS 目录（供 iOS H5 经桥接同源反代，绕开 mixed-content + 跨源）
SRS_HLS_BASE = os.environ.get("SRS_HLS_BASE", "http://localhost:8080/live").rstrip("/")
# React 商业级前端构建产物（webapp/dist），桥接当统一 https 入口在末尾 mount
WEBAPP_DIST = os.environ.get(
    "WEBAPP_DIST",
    str(pathlib.Path(__file__).resolve().parent.parent / "webapp" / "dist"),
)
# 旧版纯手写 H5（保留回退，挂在 /legacy）
H5_MOBILE_PATH = os.environ.get(
    "H5_MOBILE_PATH",
    str(pathlib.Path(__file__).resolve().parent.parent / "talk_mobile.html"),
)
# 安卓 FLV 播放器（mpegts.js）：随 LiveTalking 仓库自带，桥接同源转发给安卓浏览器/WebView
MPEGTS_JS_PATH = os.environ.get(
    "MPEGTS_JS_PATH",
    os.path.expanduser("~/Desktop/LiveTalking/web/mpegts-1.7.3.min.js"),
)

# ── 占位 ID → 真实资源的映射 ──────────────────────────────────────────
# digital-human/config 里存的是业务占位 ID（female_elegant / voice_gentle_f…），
# 这里把它们翻译成下游真正认识的资源名。生成新形象/接入新音色后只改这两张表。

# voice_id → 百炼 Qwen-TTS 音色名（LiveTalking --tts qwentts 读 tts.ref_file）
# Qwen3-TTS-Flash-Realtime：云端实时合成、0 本地 GPU、用现有 DASHSCOPE_API_KEY，
# 自然度远胜 edge-TTS。音色按消息可切（qwentts 检测到 ref_file 变化即重连换音色）。
VOICE_MAP = {
    "voice_gentle_f": "Serena",   # 知性温柔女声（默认——Cherry 偏嫩已弃用主位）
    "voice_lively_f": "Cherry",   # 活泼明快女声
    "voice_wu_f":     "Jada",     # 吴侬软语（吴语方言，江南景区特色）
    "voice_calm_m":   "Ethan",    # 沉稳男声
    "voice_bright_m": "Dylan",    # 京腔青年男声（北京话）
}
DEFAULT_VOICE = "Serena"

# avatar_id → 真实 LiveTalking avatar 名。
# Ditto 引擎（现直播主引擎）：data/ditto_avatars/<id>.png（源肖像即 avatar，无需烘录）。
# 新 id 对齐 /digital-human/presets；旧占位 id 保留兼容已有配置行。
AVATAR_MAP = {
    "female_sweet":   "sweet_bob_ditto",  # 主形象：甜美波波头(美图精修/Ditto 全脸驱动)
    "female_guofeng": "guofeng_female",   # 古风女导游（MuseTalk 烘录，未出 ditto 版）
    "male_casual":    "musetalk_avatar1", # 男形象（示例）
    # legacy 兼容
    "female_elegant": "sweet_bob_ditto",
    "female_young":   "sweet_bob_ditto",
    "male_mature":    "musetalk_avatar1",
    "male_young":     "musetalk_avatar1",
    # —— 万相高颜值身份库（10 人；已烘 <id>__<scenic>__<aspect> 159 张，id 即 base 前缀）——
    **{i: i for i in ("F1_modern", "F2_hanfu", "F3_youth", "F4_qipao", "F5_ethnic",
                      "F6_mature", "M1_modern", "M2_scholar", "M3_youth", "M4_business")},
    # —— 同脸换装（sweet_outfit_<x>，InstantID 锁脸换装，studio 无景底板）——
    "outfit_qipao":  "sweet_outfit_qipao",  "outfit_hanfu": "sweet_outfit_hanfu",
    "outfit_blazer": "sweet_outfit_blazer", "outfit_ethnic": "sweet_outfit_ethnic",
    "outfit_vest":   "sweet_outfit_vest",   "outfit_coat":  "sweet_outfit_coat",
    # —— 万相景区专属导览身份库（2026-06-19，每个绑一个景区；底板 dh_<scenic>__<scenic>__<aspect>）——
    # 故宫 2026-06-26 补齐：沿用甜美脸 + 故宫朱墙金瓦背景合成底板
    **{i: i for i in ("dh_lingshan", "dh_nihuawan", "dh_xihu", "dh_gugong",
                      "dh_mogaoku", "dh_zhangjiajie", "dh_bingmayong")},
}
DEFAULT_AVATAR = "sweet_bob_ditto"

# Ditto 源肖像目录：场景背景变体 <base>_bg_<bg_id>.png 也放这里
# （由 scripts/gen_avatar_background.py compose 产出；桥接与 LiveTalking 同机，可直接查文件）
def _default_ditto_dir() -> str:
    """本机(~/Desktop)与 AutoDL(/root/autodl-tmp) 同码不同路径 → 探测存在者。"""
    for p in (os.path.expanduser("~/Desktop/LiveTalking/data/ditto_avatars"),
              "/root/autodl-tmp/LiveTalking/data/ditto_avatars"):
        if os.path.isdir(p):
            return p
    return os.path.expanduser("~/Desktop/LiveTalking/data/ditto_avatars")

DITTO_AVATARS_DIR = os.environ.get("DITTO_AVATARS_DIR", _default_ditto_dir())


def _elapsed_ms(t0: float) -> int:
    return int((time.perf_counter() - t0) * 1000)


def _avlog(req_id: str, event: str, **fields):
    payload = {"req": req_id, "event": event, **fields}
    print("[avsync] " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")), flush=True)


def _resolve_avatar_variant(base: str, background_id: str | None) -> str:
    """按景区配置的场景背景解析 avatar 变体；变体未烘出时回落原图（容错）。
    命名与 scripts/gen_avatar_background.py 的 variant_name 一致：
    bg_id 自带 bg_ 前缀(预设)直接拼，否则(上传件)补 bg_。"""
    if background_id:
        suffix = background_id if background_id.startswith("bg_") else f"bg_{background_id}"
        cand = f"{base}_{suffix}"
        if os.path.isfile(os.path.join(DITTO_AVATARS_DIR, f"{cand}.png")):
            return cand
    return base


# 屏幕比例 → 底板宽高比后缀（身份库 159 张按此命名）
_ASPECT = {"main": "16x9", "portrait": "9x16"}


def _live_avatar_candidates(avatar_id: str, scenic_id: str, screen: str) -> list[str]:
    """把(形象 id, 景区, 屏幕)解析成 Ditto 底板候选名，最具体→最兜底；调用方取第一个存在的。
    兼容两套命名：身份库 <base>__<scenic>__<aspect>（F1-F6/M1-M4）与
    sweet_bob 传统 <base>_bg_<scenic> / <base>_portrait_<scenic>。"""
    # custom_* = AI 定制形象，底板名即 id 前缀（custom_<ts>__<scenic>__<aspect>），故直透不回落甜妹
    mapped = AVATAR_MAP.get(avatar_id)
    base = mapped or (avatar_id if avatar_id.startswith("custom_") else DEFAULT_AVATAR)
    asp = _ASPECT.get(screen, "16x9")
    cands = [
        f"{base}__{scenic_id}__{asp}",     # 身份库·本景区·本比例
        f"{base}__lingshan__{asp}",        # 缺该景区 → 回落灵山版（同比例）
        f"{base}_portrait_{scenic_id}" if screen == "portrait" else f"{base}_bg_{scenic_id}",
        base,                              # 换装/裸底板（studio 无景）
        DEFAULT_AVATAR,
    ]
    # 未知 id（不在 AVATAR_MAP、也非 custom_）不再静默直落甜妹底板——优先本景区专属身份
    # （教训 2026-07-13：sweet_bob 灵山竖版底图曾因背景人形剪影唇形坍缩，未知 id 全被它接住放大故障面）
    if mapped is None and not avatar_id.startswith("custom_"):
        cands = [f"dh_{scenic_id}__{scenic_id}__{asp}", f"dh_lingshan__lingshan__{asp}"] + cands
    # 去重保序
    seen, out = set(), []
    for c in cands:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def _pick_existing_avatar(cands: list[str]) -> str:
    """取第一个在 ditto_avatars/ 真存在的底板；都查不到(如目录未配)→ 给首选，交引擎兜底。"""
    for c in cands:
        if os.path.isfile(os.path.join(DITTO_AVATARS_DIR, f"{c}.png")):
            return c
    return cands[0]

# ── L1 高频问答视频缓存（规模化方案最大成本杀手）──
# 命中高频问答 → 直接返回预渲染成品视频片段(clip)，0 GPU·0 LLM·<0.5s，
# 既不调 RAG 也不占渲染槽。清单 webapp/{dist,public}/faq/manifest.json，片由 prerender_faq.py 产。
_WEBAPP_ROOT = pathlib.Path(__file__).resolve().parent.parent / "webapp"
_FAQ: dict[str, list[dict]] = {}


def _norm(s: str) -> str:
    """归一化：去空白与中英标点，便于"问句包含触发短语"的子串匹配。"""
    return re.sub(r"[\s，。？！?,.!、~～·:：；;\"'（）()]", "", (s or "").lower())


def _load_faq() -> int:
    """加载 FAQ 清单（优先 dist，回退 public）。返回条目总数。"""
    global _FAQ
    for base in (_WEBAPP_ROOT / "dist" / "faq", _WEBAPP_ROOT / "public" / "faq"):
        mf = base / "manifest.json"
        if mf.exists():
            try:
                data = json.loads(mf.read_text(encoding="utf-8"))
                scenics = data.get("scenics", {})
                # 预归一化每个触发短语，加速命中
                for items in scenics.values():
                    for it in items:
                        it["_norms"] = [_norm(m) for m in it.get("match", [])]
                _FAQ = scenics
                return sum(len(v) for v in scenics.values())
            except Exception:
                continue
    _FAQ = {}
    return 0


def _faq_lookup(scenic_id: str, message: str) -> dict | None:
    """高频问答命中查找：问句归一化后包含任一触发短语即命中。"""
    norm = _norm(message)
    if not norm:
        return None
    for it in _FAQ.get(scenic_id, []):
        if any(m and m in norm for m in it.get("_norms", [])):
            return it
    return None


# ── 数字人渲染容量池（规模化方案 L2/L3：按"发话"共享 GPU + 满载降级）──
# 一个 slot = 一路并发"正在说话"的数字人。发话时占用、说完(估算时长)自动释放，
# 下一个游客的发话即可复用。满载或 LiveTalking 不可用 → 降级为纯文字答复（保证人人及时）。
POOL_SIZE = int(os.environ.get("AVATAR_POOL_SIZE", "1"))   # 本地单卡=1；GPU池部署时按卡数设
SPEAK_CPS = float(os.environ.get("SPEAK_CHARS_PER_SEC", "4.5"))  # 估算说话时长(中文~4.5字/秒@0.9语速)
_LT_HEALTH_TTL = 5.0   # LiveTalking 健康检查缓存秒数
DRIVE_PACING = os.environ.get("DRIVE_PACING", "1").lower() not in {"0", "false", "no", "off"}
DRIVE_PACE_CPS = float(os.environ.get("DRIVE_PACE_CPS", str(SPEAK_CPS)))
DRIVE_PACE_LEAD_SEC = float(os.environ.get("DRIVE_PACE_LEAD_SEC", "0.8"))
DRIVE_PACE_MAX_WAIT_SEC = float(os.environ.get("DRIVE_PACE_MAX_WAIT_SEC", "14.0"))


def _drive_pace_wait_seconds(text: str) -> float:
    """估算本句至少应占用的播放时间，用于给下一句入队限速。"""
    if not DRIVE_PACING:
        return 0.0
    cps = max(1.0, DRIVE_PACE_CPS)
    speak_s = len(text or "") / cps
    return min(DRIVE_PACE_MAX_WAIT_SEC, max(0.0, speak_s - DRIVE_PACE_LEAD_SEC))


class AvatarPool:
    """数字人并发槽位管理：try_acquire 非阻塞抢槽，说完后异步释放。"""
    def __init__(self, size: int):
        self.size = max(1, size)
        self.in_use = 0
        self._lock = asyncio.Lock()

    async def try_acquire(self) -> bool:
        async with self._lock:
            if self.in_use < self.size:
                self.in_use += 1
                return True
            return False

    async def release(self):
        async with self._lock:
            self.in_use = max(0, self.in_use - 1)

    async def release_after(self, seconds: float):
        try:
            await asyncio.sleep(max(0.5, seconds))
        finally:
            await self.release()

    def status(self) -> dict:
        return {"pool_size": self.size, "in_use": self.in_use, "available": self.size - self.in_use}


POOL = AvatarPool(POOL_SIZE)
_lt_health = {"ok": False, "ts": 0.0}

# ── barge-in（提问打断）状态 ───────────────────────────────────────────────
# 同一数字人会话(sessionid)只保留"最新一问"。新问到来即把代号 +1；旧问的驱动循环
# 每句开头比对代号，发现自己已非最新 → 立即停推后续句（新问首句 interrupt 已冲掉旧音频）。
# 渲染槽按会话归属(本地单卡 POOL_SIZE=1)：首问 acquire 占槽，barge-in 复用同一槽不重复抢，
# 仅"最新一问"说完后才延迟释放 → 打断时不会被自己的旧槽卡成 pool_full 误降级为纯文字。
_ASK_GEN: dict[str, int] = {}            # sessionid → 最新提问代号
_SESSION_SLOT: dict[str, bool] = {}      # sessionid → 该会话当前是否占着渲染槽

# ── 播报有序化（2026-07-12 定稿）：per-sid 播报队列 ─────────────────────────
# 规则：queue=True 的 /live/say 入队串行播放（一条播完才播下一条，迎宾/客流/路线等
# 自动播报互不打断）；用户主动内容（/live/ask* 或 interrupt=True 的直发 /live/say）
# 到来时清空该 sid 的排队 + /interrupt_talk 硬清 LiveTalking 已排队残句，立即让位。
# 排队条目超时未轮到直接丢弃，防积压的旧播报在很久之后诡异冒出。
SPEECH_QUEUE_TTL = float(os.environ.get("SPEECH_QUEUE_TTL", "90"))
_SPEECH_Q: dict[str, asyncio.Queue] = {}        # sid → 待播队列
_SPEECH_WORKER: dict[str, asyncio.Task] = {}    # sid → 常驻消费协程
_SPEECH_DRAIN_SEQ: dict[str, int] = {}          # sid → 清队代号（在飞条目据此自弃）
_ASK_ACTIVE: dict[str, int] = {}                # sid → 正在进行的 ask 计数（防队列抢走慢生成答案的通道）


def _speech_queue(sid: str) -> asyncio.Queue:
    q = _SPEECH_Q.get(sid)
    if q is None:
        q = _SPEECH_Q[sid] = asyncio.Queue()
    return q


def _drain_speech_queue(sid: str, reason: str = "") -> int:
    """用户主动内容到来：清空 sid 的排队播报并 bump 清队代号（在飞条目播出前会自弃）。"""
    _SPEECH_DRAIN_SEQ[sid] = _SPEECH_DRAIN_SEQ.get(sid, 0) + 1
    _NOW_PLAYING.pop(sid, None)   # 被打断的内容不再是"正在播"，字幕即刻让位
    q = _SPEECH_Q.get(sid)
    n = 0
    if q is not None:
        while not q.empty():
            try:
                q.get_nowait()
                n += 1
            except asyncio.QueueEmpty:
                break
    if n:
        _avlog("squeue", "speech_queue_drained", sid=sid, dropped=n, reason=reason)
    return n


async def _lt_interrupt_oneshot(lt_base: str, sessionid: str):
    """硬清 LiveTalking 端已排队残句（best-effort，不阻塞主链路）。"""
    try:
        async with httpx.AsyncClient(trust_env=False) as c:
            await c.post(f"{lt_base}/interrupt_talk", json={"sessionid": sessionid}, timeout=3)
    except Exception:
        pass


async def _lt_is_speaking(client: httpx.AsyncClient, lt_base: str, sessionid: str) -> bool | None:
    """查询 LiveTalking 是否正在说话；探测失败返回 None（调用方走估算兜底）。"""
    try:
        r = await client.post(f"{lt_base}/is_speaking", json={"sessionid": sessionid}, timeout=3)
        d = r.json()
        if d.get("code") == 0:
            return bool(d.get("data"))
    except Exception:
        pass
    return None


# ── 「正在播放」登记（2026-07-13 逐句字幕/音波真信号）──────────────────────
# 每次把文本送 LiveTalking /human 时登记该 sid 正在播的内容；前端轮询
# GET /live/now-playing 驱动逐句字幕与音波兜底动画（覆盖问答逐句 + 队列播报 + 直发 say）。
# 无需显式清除：条目按字数估算时长自然过期（elapsed > est + margin 即视为不在播），
# 新内容（含打断后的新首句）到来时直接覆盖。
_NOW_PLAYING: dict[str, dict] = {}   # sid → {text, ts, est_s, source}

# 当前每路直播流上活跃的形象 id（screen → avatar_id）。热切成功即登记，
# 供 /live/now-playing 回带、前端过渡层收尾对账（旧前端忽略该字段）。
_LIVE_AVATAR: dict[str, str] = {}

# ── 应急广播上屏字幕（2026-07-14）──────────────────────────────────────
# 管理端发应急广播时可同时在现场大屏(kiosk)顶部推一条醒目字幕横幅。纯内存查表：
# screen → {text, style, expire_ts}；kiosk 轮询 GET /live/subtitle 取当前有效字幕，
# 到期(now>expire_ts)返回空。与 /live/now-playing 同款轻量写法，无守护协程。
_SUBTITLE: dict[str, dict] = {}


def _set_now_playing(sid: str, text: str, source: str):
    _NOW_PLAYING[sid] = {"text": text, "ts": time.monotonic(),
                         "est_s": len(text) / SPEAK_CPS + 1.5, "source": source}


async def _speech_worker_loop(sid: str, screen: str):
    """播报队列常驻消费协程：逐条出队 → 等通道空闲 → 送 LiveTalking → 等播完 → 下一条。"""
    q = _speech_queue(sid)
    lt_base = LIVETALKING_BASE if screen == "main" else LIVETALKING_BASE_2
    timeout = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
    while True:
        item = await q.get()
        body = item["body"]
        req_id = item["req_id"]
        drain_seq = _SPEECH_DRAIN_SEQ.get(sid, 0)
        if time.monotonic() - item["ts"] > SPEECH_QUEUE_TTL:
            _avlog(req_id, "queue_say_expired", sid=sid,
                   waited_s=round(time.monotonic() - item["ts"], 1))
            continue
        try:
            async with httpx.AsyncClient(trust_env=False, timeout=timeout) as client:
                # 通道让行：正在进行的 ask（含句间生成停顿）或仍在播的内容先说完
                idle_hits = 0
                while time.monotonic() - item["ts"] <= SPEECH_QUEUE_TTL:
                    if _SPEECH_DRAIN_SEQ.get(sid, 0) != drain_seq:
                        break
                    if not _ASK_ACTIVE.get(sid):
                        speaking = await _lt_is_speaking(client, lt_base, body.sessionid)
                        if not speaking:      # False 或探测失败都放行（估算兜底）
                            idle_hits += 1
                            if idle_hits >= 2:   # 双确认，防句间/合成间隙误判空闲
                                break
                        else:
                            idle_hits = 0
                    await asyncio.sleep(0.5)
                if _SPEECH_DRAIN_SEQ.get(sid, 0) != drain_seq:
                    _avlog(req_id, "queue_say_dropped", sid=sid, reason="drained_inflight")
                    continue
                if time.monotonic() - item["ts"] > SPEECH_QUEUE_TTL:
                    _avlog(req_id, "queue_say_expired", sid=sid, during="wait_idle")
                    continue
                # 接管代号：停掉可能仍在跑的旧 ask 残循环（与直发 /live/say 同语义）
                my_gen = _ASK_GEN[sid] = _ASK_GEN.get(sid, 0) + 1
                if body.voice_id and body.voice_id in VOICE_MAP:
                    voice = VOICE_MAP[body.voice_id]
                else:
                    _, voice, _ = await _resolve_config(client, body.scenic_id)
                _avlog(req_id, "queue_say_drive", sid=sid, chars=len(body.text), voice=voice,
                       waited_s=round(time.monotonic() - item["ts"], 1))
                await client.post(
                    f"{lt_base}/human",
                    json={
                        "sessionid": body.sessionid,
                        "text": body.text,
                        "type": "echo",
                        "interrupt": False,   # 排队内容永不打断别人，顺序衔接
                        "tts": {"ref_file": voice, "emotion": body.emotion,
                                "scenic_id": body.scenic_id},
                    },
                    timeout=15,
                )
                _set_now_playing(sid, body.text, "queue")
                # 等播完：先睡估算时长的大半，再轮询 is_speaking 双确认收尾
                est = len(body.text) / SPEAK_CPS + 1.5
                await asyncio.sleep(min(est * 0.8, 60.0))
                deadline = time.monotonic() + max(est, 10.0) + 15.0
                idle_hits = 0
                while time.monotonic() < deadline:
                    if _ASK_GEN.get(sid) != my_gen:   # 被用户内容顶替，不再守
                        break
                    speaking = await _lt_is_speaking(client, lt_base, body.sessionid)
                    if speaking is False:
                        idle_hits += 1
                        if idle_hits >= 2:
                            break
                    elif speaking is True:
                        idle_hits = 0
                    else:                              # 探测失败 → 纯估算兜底
                        await asyncio.sleep(max(0.0, est * 0.2))
                        break
                    await asyncio.sleep(0.7)
                _avlog(req_id, "queue_say_done", sid=sid,
                       superseded=_ASK_GEN.get(sid) != my_gen)
        except Exception as e:  # noqa: BLE001 - 单条失败不倒队列
            _avlog(req_id, "queue_say_error", sid=sid, error=f"{type(e).__name__}: {e}")


def _ensure_speech_worker(sid: str, screen: str):
    t = _SPEECH_WORKER.get(sid)
    if t is None or t.done():
        _SPEECH_WORKER[sid] = asyncio.create_task(_speech_worker_loop(sid, screen))


async def _livetalking_ok(client: httpx.AsyncClient) -> bool:
    """LiveTalking 可用性（5s 缓存，避免每次问答都探活）。"""
    now = time.monotonic()
    if now - _lt_health["ts"] < _LT_HEALTH_TTL:
        return _lt_health["ok"]
    ok = False
    try:
        r = await client.get(f"{LIVETALKING_BASE}/", timeout=2)
        ok = r.status_code < 500
    except Exception:
        ok = False
    _lt_health.update(ok=ok, ts=now)
    return ok


app = FastAPI(title="数字人桥接层", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskIn(BaseModel):
    sessionid: str                 # LiveTalking WebRTC 会话 ID（/offer 返回的那个）
    message: str
    session_id: str = "anonymous"  # RAG 业务会话 ID（用于历史/分析，与上面不是一回事）
    scenic_id: str = "lingshan"
    group_type: str = "adult"      # adult / family_kids / senior / couple
    lang: str = "auto"
    fast: bool = False
    interrupt: bool = True         # 新提问默认打断数字人上一句未播完的话
    voice_id: str | None = None    # 游客精调音色（覆盖景区默认配置；presets 的 voice_id）
    screen: str = "main"           # 'main'=手机端 16:9(8010)；'portrait'=大屏竖版 9:16(8011)
    situation: dict | None = None  # 自身情况标签（age/pace/mobility/purpose/first_time），透传 RAG
    interests: list[str] = []      # 静态兴趣（开场快选），透传 RAG 入游中画像


async def _resolve_config(client: httpx.AsyncClient, scenic_id: str) -> tuple[str, str, str]:
    """读 digital-human/config，翻译成 (真实 avatar[含背景变体], 真实 voice, background_id)。
    任何失败回落默认。"""
    try:
        r = await client.get(
            f"{RAG_BASE}/digital-human/config",
            params={"scenic_id": scenic_id},
            timeout=5,
        )
        cfg = r.json()
        background_id = cfg.get("background_id") or ""
        avatar = _resolve_avatar_variant(
            AVATAR_MAP.get(cfg.get("avatar_id"), DEFAULT_AVATAR), background_id)
        voice = VOICE_MAP.get(cfg.get("voice_id"), DEFAULT_VOICE)
        return avatar, voice, background_id
    except Exception:
        return DEFAULT_AVATAR, DEFAULT_VOICE, ""


async def _run_ask(body: AskIn, emit):
    """游客问一句 → 订阅 RAG 句子级流式 → 每出一句立即驱动数字人开口。

    关键时序（压住 <5s 端到端延迟的核心）：
      RAG 第 1 句生成完(~0.8s) → 立刻送 LiveTalking 说出来 → 数字人即刻开口，
      与此同时 RAG 继续生成后面的句子并排队播放，而不是等整段答案。

    barge-in：进来即把本会话代号 +1。任何更早的 /live/ask 在其驱动循环里发现自己已非最新代
    → 立即停推后续句（新问首句 interrupt 会冲掉旧音频残留），实现"用户打断、立刻转答新问题"。

    JSON 与 SSE 字幕流共用此核心。`emit(event:str, data:dict)` = 异步回调：
      - JSON 端点传 no-op（只取最终返回 dict）；
      - SSE 端点（/live/ask_stream）用它把"open/sentence"逐句下发，让前端字幕与数字人
        说话同步流式吐字（卡拉OK式）。错误抛 HTTPException，由 SSE 包装层捕获转 error 事件。
    返回最终结果 dict（与历史 /live/ask 响应结构一致，另加 first_sentence_ms）。
    """
    # state 按屏幕命名空间隔离（手机端 main 与大屏 portrait 即使 sessionid 都是 "0" 也不互相打断）
    sid = f"{body.screen}:{body.sessionid}"
    lt_base = LIVETALKING_BASE if body.screen == "main" else LIVETALKING_BASE_2
    my_gen = _ASK_GEN[sid] = _ASK_GEN.get(sid, 0) + 1
    # 有序播放规则：用户提问=立即打断——清空该 sid 排队播报 + 硬清 LiveTalking 残句
    _drain_speech_queue(sid, reason="user_ask")
    if body.interrupt:
        asyncio.create_task(_lt_interrupt_oneshot(lt_base, body.sessionid))
    t_start = time.perf_counter()
    req_id = uuid.uuid4().hex[:8]
    _avlog(req_id, "ask_start", screen=body.screen, sessionid=body.sessionid,
           sid=sid, gen=my_gen, scenic_id=body.scenic_id, msg_len=len(body.message or ""),
           voice_id=body.voice_id or "", interrupt=body.interrupt)

    # ── L1 命中：高频问答直接返回预渲染成品视频，0 GPU·0 LLM·<0.5s（不调 RAG、不占渲染槽）──
    hit = _faq_lookup(body.scenic_id, body.message)
    if hit:
        _avlog(req_id, "ask_clip_hit", elapsed_ms=_elapsed_ms(t_start),
               scenic_id=body.scenic_id, clip=hit.get("clip", ""), chars=len(hit.get("answer", "")))
        return {
            "ok": True,
            "reply": hit["answer"],
            "emotion": hit.get("emotion", "happy"),
            "intent": "qa",
            "voice": None,
            "sentence_count": 1,
            "drive_failures": 0,
            "mode": "clip",                 # 前端据此直接播 clip_url 成品视频
            "clip_url": hit["clip"],
            "cached": True,
            "degraded": False,
            "capacity": POOL.status(),
        }

    # trust_env=False：桥接只调 localhost/内网/ECS，绕开环境里的 SOCKS 代理
    # read 超时给到 60s，容纳 LLM 整段流式生成的时长
    timeout = httpx.Timeout(connect=5.0, read=60.0, write=10.0, pool=5.0)
    async with httpx.AsyncClient(trust_env=False, timeout=timeout) as client:
        # 1) 流式开始前先确定音色（第一句就要用）；游客精调 voice_id 优先于景区默认
        if body.voice_id and body.voice_id in VOICE_MAP:
            voice = VOICE_MAP[body.voice_id]
        else:
            _, voice, _ = await _resolve_config(client, body.scenic_id)
        _avlog(req_id, "voice_resolved", elapsed_ms=_elapsed_ms(t_start),
               screen=body.screen, voice=voice, voice_id=body.voice_id or "")

        # 1.5) 容量决策：LiveTalking 可用 且 本会话持有渲染槽 → 驱动数字人开口；
        #      否则降级为纯文字答复（答案照出，只是这一条没有会动的脸）——保证人人及时。
        #      barge-in：同会话上一问还占着槽 → 复用，不重复 acquire（否则会被自己的延迟
        #      释放卡成 pool_full 误降级），仅"最新一问"说完才释放。
        if body.screen == "main":
            lt_ok = await _livetalking_ok(client)
            if lt_ok and not _SESSION_SLOT.get(sid):
                if await POOL.try_acquire():
                    _SESSION_SLOT[sid] = True
            drive_enabled = lt_ok and _SESSION_SLOT.get(sid, False)
        else:
            lt_ok = True
            drive_enabled = True   # 大屏=独立 LiveTalking 实例(8011)，直接驱动，不占手机端共享渲染池
        _avlog(req_id, "open", elapsed_ms=_elapsed_ms(t_start), screen=body.screen,
               drive_enabled=drive_enabled, lt_ok=lt_ok, capacity=POOL.status())

        # 字幕流：先告诉前端本轮是否会真开口（drive_enabled）+ 音色。
        # 前端据此决定字幕节奏：会开口 → 按说话速率卡拉OK式逐字吐（跟随语音）；
        # 降级纯文字 → 无语音可同步，直接快速显示。
        await emit("open", {"drive_enabled": drive_enabled, "voice": voice})

        async def _release_slot_if_owner(delay: float = 0.0):
            """释放本会话渲染槽——仅当本问仍是最新代（未被 barge-in 取代）。delay>0 = 说完延迟释放。"""
            if delay > 0:
                await asyncio.sleep(delay)
            if _ASK_GEN.get(sid) == my_gen and _SESSION_SLOT.get(sid):
                _SESSION_SLOT[sid] = False
                await POOL.release()
                _avlog(req_id, "slot_released", elapsed_ms=_elapsed_ms(t_start),
                       delay_s=round(delay, 3), capacity=POOL.status())

        intent = "qa"
        emotion = "neutral"
        sentences: list[str] = []
        drive_failures = 0
        first = True
        first_sentence_ms: int | None = None    # 首句送达耗时（≈数字人开口时刻，诚实延迟口径）
        next_drive_at = 0.0                     # 下一句允许送入 LiveTalking 的时间点

        async def _drive(text: str, interrupt: bool, index: int):
            """把一句话送数字人说出来。单句失败不中断整条流，只计数。"""
            nonlocal drive_failures
            t_drive = time.perf_counter()
            _avlog(req_id, "drive_start", elapsed_ms=_elapsed_ms(t_start), index=index,
                   chars=len(text), interrupt=interrupt, emotion=emotion, voice=voice,
                   screen=body.screen)
            try:
                r = await client.post(
                    f"{lt_base}/human",
                    json={
                        "sessionid": body.sessionid,
                        "text": text,
                        "type": "echo",
                        "interrupt": interrupt,
                        # ref_file=Qwen音色名(qwentts用); scenic_id=景区(ttsbackend用→队友CosyVoice景区专属音色);
                        # emotion 透传→数字人切表情底座
                        "tts": {"ref_file": voice, "emotion": emotion, "scenic_id": body.scenic_id},
                    },
                    timeout=10,
                )
                _set_now_playing(sid, text, "ask")
                _avlog(req_id, "drive_done", elapsed_ms=_elapsed_ms(t_start), index=index,
                       http_ms=_elapsed_ms(t_drive), status_code=r.status_code)
            except Exception as e:
                drive_failures += 1
                _avlog(req_id, "drive_error", elapsed_ms=_elapsed_ms(t_start), index=index,
                       http_ms=_elapsed_ms(t_drive), error=f"{type(e).__name__}: {e}")

        # 2) 订阅 RAG SSE 流，逐句驱动数字人
        superseded = False
        try:
            _avlog(req_id, "rag_stream_start", elapsed_ms=_elapsed_ms(t_start))
            async with client.stream(
                "POST",
                f"{RAG_BASE}/chat",
                json={
                    "session_id": body.session_id,
                    "message": body.message,
                    "scenic_id": body.scenic_id,
                    "group_type": body.group_type,
                    "lang": body.lang,
                    "fast": body.fast,
                    "stream": True,
                    "situation": body.situation,
                    "interests": body.interests,
                },
            ) as resp:
                resp.raise_for_status()
                _avlog(req_id, "rag_stream_open", elapsed_ms=_elapsed_ms(t_start),
                       status_code=resp.status_code)
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    try:
                        evt = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    etype = evt.get("type")
                    # barge-in：被更新的提问取代 → 停止接收/驱动本轮（新问首句已 interrupt 冲掉旧音频）
                    if _ASK_GEN.get(sid) != my_gen:
                        superseded = True
                        _avlog(req_id, "superseded", elapsed_ms=_elapsed_ms(t_start),
                               latest_gen=_ASK_GEN.get(sid), my_gen=my_gen)
                        break
                    if etype == "intent":
                        intent = evt.get("value", intent)
                        _avlog(req_id, "rag_intent", elapsed_ms=_elapsed_ms(t_start), intent=intent)
                    elif etype == "emotion":
                        # emotion 事件在第一个 sentence 之前下发，第一句即可带上正确情绪
                        emotion = evt.get("value", emotion)
                        _avlog(req_id, "rag_emotion", elapsed_ms=_elapsed_ms(t_start), emotion=emotion)
                    elif etype == "sentence":
                        text = (evt.get("text") or "").strip()
                        if not text:
                            continue
                        idx = len(sentences)
                        if drive_enabled and DRIVE_PACING:
                            wait_s = max(0.0, next_drive_at - time.perf_counter())
                            if wait_s > 0:
                                _avlog(req_id, "drive_pace_wait", elapsed_ms=_elapsed_ms(t_start),
                                       index=idx, wait_ms=int(wait_s * 1000))
                                await asyncio.sleep(wait_s)
                                if _ASK_GEN.get(sid) != my_gen:
                                    superseded = True
                                    _avlog(req_id, "superseded", elapsed_ms=_elapsed_ms(t_start),
                                           latest_gen=_ASK_GEN.get(sid), my_gen=my_gen,
                                           during="drive_pace_wait")
                                    break
                        _avlog(req_id, "rag_sentence", elapsed_ms=_elapsed_ms(t_start),
                               index=idx, chars=len(text), drive_enabled=drive_enabled,
                               emotion=emotion)
                        sentences.append(text)
                        # 第一句打断上一轮残留，后续句排队顺序播放（降级模式不驱动，只收集文字）
                        if drive_enabled:
                            await _drive(text, interrupt=(body.interrupt and first), index=idx)
                            if _ASK_GEN.get(sid) != my_gen:
                                superseded = True
                                _avlog(req_id, "superseded", elapsed_ms=_elapsed_ms(t_start),
                                       latest_gen=_ASK_GEN.get(sid), my_gen=my_gen,
                                       during="drive_done")
                                break
                            pace_wait = _drive_pace_wait_seconds(text)
                            next_drive_at = time.perf_counter() + pace_wait
                            if pace_wait > 0:
                                _avlog(req_id, "drive_pace_next", elapsed_ms=_elapsed_ms(t_start),
                                       index=idx, next_wait_ms=int(pace_wait * 1000))
                        if first_sentence_ms is None:
                            first_sentence_ms = int((time.perf_counter() - t_start) * 1000)
                        # 字幕流：本句已送数字人开口 → 立刻下发字幕，前端按说话速率逐字吐（与语音同步）
                        await emit("sentence", {"text": text, "index": len(sentences) - 1, "emotion": emotion})
                        _avlog(req_id, "sse_sentence", elapsed_ms=_elapsed_ms(t_start),
                               index=idx, chars=len(text))
                        first = False
                    elif etype == "end":
                        _avlog(req_id, "rag_end", elapsed_ms=_elapsed_ms(t_start),
                               full_chars=len(evt.get("full_text") or ""))
        except Exception as e:
            await _release_slot_if_owner()
            _avlog(req_id, "ask_error", elapsed_ms=_elapsed_ms(t_start),
                   error=f"{type(e).__name__}: {e}")
            raise HTTPException(
                status_code=502,
                detail=f"RAG 流式调用失败: {type(e).__name__}: {e}",
            )

        # barge-in：本问已被取代 → 槽已归新问（_release 因非最新代会自动跳过），安静返回；
        #   前端按提问序号丢弃本响应，不覆盖新问的 UI
        if superseded:
            _avlog(req_id, "ask_done", elapsed_ms=_elapsed_ms(t_start), superseded=True,
                   sentence_count=len(sentences), drive_failures=drive_failures,
                   first_sentence_ms=first_sentence_ms, capacity=POOL.status())
            return {
                "ok": True, "reply": "".join(sentences), "superseded": True,
                "mode": "text", "degraded": False, "intent": intent,
                "emotion": emotion, "voice": voice, "capacity": POOL.status(),
                "first_sentence_ms": first_sentence_ms,
            }

        if not sentences:
            await _release_slot_if_owner()
            _avlog(req_id, "ask_error", elapsed_ms=_elapsed_ms(t_start),
                   error="RAG 未产出任何句子")
            raise HTTPException(status_code=502, detail="RAG 未产出任何句子")

        reply = "".join(sentences)
        # 槽位释放：按估算说话时长延迟释放（说话期间占用，说完即可被下一个游客复用）；
        # 仅"最新一问"释放——被 barge-in 取代的旧问 _release 会因非最新代自动跳过，把槽留给新问
        asyncio.create_task(_release_slot_if_owner(len(reply) / SPEAK_CPS + 1.0))

        # 数字人是否真的开口了：启用驱动 且 至少一句送达成功
        spoke = drive_enabled and drive_failures < len(sentences)
        reason = None if spoke else (
            "livetalking_down" if not lt_ok else ("pool_full" if not drive_enabled else "drive_failed"))
        _avlog(req_id, "ask_done", elapsed_ms=_elapsed_ms(t_start), superseded=False,
               sentence_count=len(sentences), reply_chars=len(reply),
               drive_failures=drive_failures, mode="avatar" if spoke else "text",
               degrade_reason=reason, first_sentence_ms=first_sentence_ms,
               capacity=POOL.status())
        return {
            "ok": True,                          # 答案永远拿得到（降级也算成功）
            "reply": reply,
            "emotion": emotion,
            "intent": intent,
            "voice": voice,
            "sentence_count": len(sentences),
            "drive_failures": drive_failures,
            "mode": "avatar" if spoke else "text",   # 前端据此决定看脸还是看字
            "degraded": not spoke,                    # true=本条降级为纯文字
            "degrade_reason": reason,                 # livetalking_down / pool_full / drive_failed
            "capacity": POOL.status(),
            "first_sentence_ms": first_sentence_ms,   # 首句送达耗时（≈开口时刻，前端可参考）
        }


async def _noop_emit(event: str, data: dict) -> None:
    """JSON 端点用：不需要逐句下发，只取 _run_ask 的最终返回。"""
    return None


async def _run_ask_tracked(body: AskIn, emit):
    """_run_ask 外套一层活跃计数：播报队列 worker 据此避让正在进行的 ask
    （含句间 LLM 生成停顿——那时 is_speaking 可能短暂为 False，不能被队列抢通道）。"""
    sid = f"{body.screen}:{body.sessionid}"
    _ASK_ACTIVE[sid] = _ASK_ACTIVE.get(sid, 0) + 1
    try:
        return await _run_ask(body, emit)
    finally:
        _ASK_ACTIVE[sid] = max(0, _ASK_ACTIVE.get(sid, 1) - 1)


@app.post("/live/ask")
async def live_ask(body: AskIn):
    """游客问一句 → 数字人开口（一次性 JSON 响应，含完整答案）。

    历史端点，保持响应结构不变（队友/降级回退用）。需要"字幕随语音逐字吐"用 /live/ask_stream。
    """
    return await _run_ask_tracked(body, _noop_emit)


@app.post("/live/ask_stream")
async def live_ask_stream(body: AskIn):
    """同 /live/ask，但以 SSE 把字幕逐句下发，让前端字幕与数字人说话同步流式吐字（卡拉OK式）。

    事件（`data:` 一行一个 JSON）：
      {"type":"open","drive_enabled":bool,"voice":str}   本轮是否真开口（决定字幕节奏）
      {"type":"sentence","text":str,"index":int,"emotion":str}  每句送数字人开口时下发
      {"type":"done", ...完整结果dict...}                收尾（reply/mode/degraded/intent/emotion/timing…）
      {"type":"error","detail":str,"status":int}         出错
    """
    q: asyncio.Queue = asyncio.Queue()

    async def emit(event: str, data: dict) -> None:
        await q.put((event, data))

    async def runner():
        try:
            result = await _run_ask_tracked(body, emit)
            await q.put(("done", result))
        except HTTPException as e:
            await q.put(("error", {"detail": str(e.detail), "status": e.status_code}))
        except Exception as e:  # noqa: BLE001 - 兜底，绝不让流悬挂
            await q.put(("error", {"detail": f"{type(e).__name__}: {e}", "status": 500}))
        finally:
            await q.put((None, None))   # 终止哨兵

    async def gen():
        task = asyncio.create_task(runner())
        try:
            while True:
                event, data = await q.get()
                if event is None:
                    break
                payload = {"type": event, **(data or {})}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )


@app.on_event("startup")
async def _startup_faq():
    n = _load_faq()
    print(f"[bridge] L1 FAQ 缓存载入 {n} 条高频问答")


@app.post("/live/faq/reload")
async def live_faq_reload():
    """重载 FAQ 缓存清单（prerender 脚本更新清单后调用，热生效，无需重启）。"""
    n = _load_faq()
    return {"ok": True, "count": n, "scenics": list(_FAQ.keys())}


@app.get("/live/capacity")
async def live_capacity():
    """数字人渲染容量观测（供运维/数据大屏）：当前占用/总槽位 + LiveTalking 是否在线。"""
    async with httpx.AsyncClient(trust_env=False) as client:
        lt_ok = await _livetalking_ok(client)
    return {**POOL.status(), "livetalking_ok": lt_ok, "speak_cps": SPEAK_CPS}


class SayIn(BaseModel):
    sessionid: str                 # LiveTalking WebRTC/RTMP 会话 ID
    text: str                      # 直接要数字人说出来的文字（如拍照定位讲解的结果）
    scenic_id: str = "lingshan"    # 决定音色
    interrupt: bool = True
    emotion: str = "neutral"       # 面部情绪：驱动数字人切换表情底座（neutral/happy/concerned…）
    voice_id: str | None = None    # 游客精调音色（覆盖景区默认配置）
    screen: str = "main"           # 'main'=手机端 16:9(8010)；'portrait'=大屏竖版 9:16(8011)
    queue: bool = False            # True=入播报队列串行播放（迎宾/客流等自动播报用，一条播完再播下一条）；
                                   # False=直发（默认，行为不变；interrupt=True 时同时清空排队播报）


@app.post("/live/say")
async def live_say(body: SayIn):
    """让数字人直接说出一段给定文字（不走 RAG）。

    用于「拍照视觉定位」闭环：游客拍照 → /chat/image 出定位+讲解+指路文字 →
    本端点把这段文字按景区音色送 LiveTalking /human，让数字人开口说。
    """
    t_start = time.perf_counter()
    req_id = uuid.uuid4().hex[:8]
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空")
    _avlog(req_id, "say_start", screen=body.screen, sessionid=body.sessionid,
           scenic_id=body.scenic_id, chars=len(text), interrupt=body.interrupt,
           emotion=body.emotion, voice_id=body.voice_id or "", queue=body.queue)
    sid = f"{body.screen}:{body.sessionid}"
    # 播报队列模式：入队即返回，由该 sid 的常驻 worker 串行播放（一条播完再播下一条）
    if body.queue:
        body.text = text
        _ensure_speech_worker(sid, body.screen)
        q = _speech_queue(sid)
        q.put_nowait({"body": body, "ts": time.monotonic(), "req_id": req_id})
        _avlog(req_id, "say_queued", sid=sid, position=q.qsize(), chars=len(text))
        return {"ok": True, "queued": True, "position": q.qsize(), "chars": len(text)}
    # 接管会话代号：停掉任何仍在跑的旧 /live/ask 驱动循环（治「换页/重连后数字人接着说上一页旧答案」——
    # 关网页不会通知服务端，旧 ask 循环仍在逐句驱动；新页迎宾走本端点，bump 代号即让旧循环在下一句自停）。
    my_gen = _ASK_GEN[sid] = _ASK_GEN.get(sid, 0) + 1
    # 有序播放规则：interrupt 直发 say 视为用户主动内容 → 清空该 sid 排队播报
    if body.interrupt:
        _drain_speech_queue(sid, reason="user_say")

    async def _release_slot_if_owner(delay: float):
        if delay > 0:
            await asyncio.sleep(delay)
        if _ASK_GEN.get(sid) == my_gen and _SESSION_SLOT.get(sid):
            _SESSION_SLOT[sid] = False
            await POOL.release()
            _avlog(req_id, "say_slot_released", elapsed_ms=_elapsed_ms(t_start),
                   delay_s=round(delay, 3), capacity=POOL.status())

    async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)) as client:
        if body.voice_id and body.voice_id in VOICE_MAP:
            voice = VOICE_MAP[body.voice_id]
        else:
            _, voice, _ = await _resolve_config(client, body.scenic_id)
        say_base = LIVETALKING_BASE if body.screen == "main" else LIVETALKING_BASE_2
        _avlog(req_id, "say_drive_start", elapsed_ms=_elapsed_ms(t_start),
               screen=body.screen, voice=voice)
        t_drive = time.perf_counter()
        try:
            r = await client.post(
                f"{say_base}/human",
                json={
                    "sessionid": body.sessionid,
                    "text": text,
                    "type": "echo",
                    "interrupt": body.interrupt,
                    "tts": {"ref_file": voice, "emotion": body.emotion, "scenic_id": body.scenic_id},
                },
                timeout=15,
            )
            _set_now_playing(sid, text, "say")
            _avlog(req_id, "say_drive_done", elapsed_ms=_elapsed_ms(t_start),
                   http_ms=_elapsed_ms(t_drive), status_code=r.status_code)
        except Exception as e:
            _avlog(req_id, "say_drive_error", elapsed_ms=_elapsed_ms(t_start),
                   http_ms=_elapsed_ms(t_drive), error=f"{type(e).__name__}: {e}")
            if body.screen == "main":
                asyncio.create_task(_release_slot_if_owner(0.0))
            raise HTTPException(status_code=502, detail=f"驱动数字人失败: {type(e).__name__}: {e}")
    if body.screen == "main":
        asyncio.create_task(_release_slot_if_owner(len(text) / SPEAK_CPS + 1.0))
    _avlog(req_id, "say_done", elapsed_ms=_elapsed_ms(t_start), voice=voice, chars=len(text))
    return {"ok": True, "voice": voice, "chars": len(text)}


class InterruptIn(BaseModel):
    sessionid: str                 # LiveTalking 会话 ID
    screen: str = "main"           # 'main'=手机端 16:9 / 'portrait'=大屏竖版 9:16


@app.post("/live/interrupt")
async def live_interrupt(body: InterruptIn):
    """用户主动打断：立即停止数字人当前播报。

    清空该 sid 的排队播报 + bump 会话代号（在跑的 /live/ask、/live/say 驱动循环
    下一句自停）+ 硬清 LiveTalking 端已排队残句 + 撤下「正在播」登记（字幕即刻让位）+
    释放可能占用的渲染槽（防打断后卡 pool_full）。纯 CPU，不碰 GPU/不重启流。
    前端配合把 <video> 音量淡出，即「打断后语音逐渐减弱、且不影响下一条提问输入」。
    """
    sid = f"{body.screen}:{body.sessionid}"
    _ASK_GEN[sid] = _ASK_GEN.get(sid, 0) + 1            # 旧驱动循环下一句自停
    dropped = _drain_speech_queue(sid, reason="user_interrupt")  # 清队 + 清 now-playing
    lt_base = LIVETALKING_BASE if body.screen == "main" else LIVETALKING_BASE_2
    asyncio.create_task(_lt_interrupt_oneshot(lt_base, body.sessionid))  # 硬清引擎残句
    if _SESSION_SLOT.get(sid):                          # 释放本会话占用的渲染槽
        _SESSION_SLOT[sid] = False
        try:
            await POOL.release()
        except Exception:
            pass
    _avlog("interrupt", "user_interrupt", sid=sid, dropped=dropped)
    return {"ok": True, "dropped": dropped}


@app.get("/live/now-playing")
async def live_now_playing(screen: str = "main", sessionid: str = "0"):
    """当前数字人正在播的内容（逐句字幕/音波的真信号）。

    纯内存查表、零下游调用，轮询友好（前端 ~800ms 一次）。数据来源 = 每次送
    LiveTalking /human 时的登记（问答逐句 / 队列播报 / 直发 say 三路全覆盖），
    按字数估算时长自然过期，无守护协程。
    """
    sid = f"{screen}:{sessionid}"
    avatar_id = _LIVE_AVATAR.get(screen, "")
    np_ = _NOW_PLAYING.get(sid)
    if np_:
        elapsed = time.monotonic() - np_["ts"]
        if elapsed <= np_["est_s"] + 2.5:
            return {"speaking": True, "text": np_["text"], "source": np_["source"],
                    "elapsed_ms": int(elapsed * 1000), "est_ms": int(np_["est_s"] * 1000),
                    "avatar_id": avatar_id}
    return {"speaking": False, "text": "", "source": "", "elapsed_ms": 0, "est_ms": 0,
            "avatar_id": avatar_id}


# ── 应急广播字幕 + 全屏播报 ──────────────────────────────────────────────
def _screens(screen: str) -> list[str]:
    return ["portrait", "main"] if screen == "both" else [screen]


class SubtitleIn(BaseModel):
    text: str                          # 上屏字幕文案（空字符串=立即撤下字幕）
    screen: str = "portrait"           # 'portrait'(大屏) / 'main'(手机端) / 'both'
    duration_s: float = 20.0           # 字幕停留秒数
    style: str = "alert"               # 'alert'=警示红 / 'info'=通知蓝


@app.post("/live/subtitle")
async def live_subtitle(body: SubtitleIn):
    """写当前上屏字幕（kiosk 轮询取用）。text 为空=撤下。"""
    text = (body.text or "").strip()
    style = body.style if body.style in ("alert", "info") else "alert"
    for sc in _screens(body.screen):
        if text:
            _SUBTITLE[sc] = {"text": text, "style": style,
                             "expire_ts": time.monotonic() + max(1.0, body.duration_s)}
        else:
            _SUBTITLE.pop(sc, None)
    return {"ok": True, "screens": _screens(body.screen), "cleared": not text}


@app.get("/live/subtitle")
async def live_get_subtitle(screen: str = "portrait"):
    """kiosk 轮询取当前有效上屏字幕；无/过期返回 active=False。"""
    sub = _SUBTITLE.get(screen)
    if sub and time.monotonic() < sub["expire_ts"]:
        return {"active": True, "text": sub["text"], "style": sub["style"],
                "remain_ms": int((sub["expire_ts"] - time.monotonic()) * 1000)}
    return {"active": False, "text": "", "style": "alert", "remain_ms": 0}


class BroadcastIn(BaseModel):
    text: str
    screens: list[str] = ["portrait"]  # 目标屏列表：portrait / main
    scenic_id: str = "lingshan"
    emotion: str = "concerned"
    subtitle: bool = True              # 是否同时推上屏字幕横幅
    duration_s: float = 20.0
    style: str = "alert"
    voice_id: str | None = None


@app.post("/live/broadcast")
async def live_broadcast(body: BroadcastIn):
    """应急广播：一次调用让所选屏的数字人立即开口播报（打断当前讲解）+ 可选推上屏字幕。"""
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空")
    targets = [s for s in body.screens if s in ("portrait", "main")] or ["portrait"]
    results = {}
    for sc in targets:
        try:
            await live_say(SayIn(sessionid="0", text=text, scenic_id=body.scenic_id,
                                 interrupt=True, emotion=body.emotion,
                                 voice_id=body.voice_id, screen=sc, queue=False))
            results[sc] = True
        except Exception:
            results[sc] = False
    if body.subtitle:
        style = body.style if body.style in ("alert", "info") else "alert"
        for sc in targets:
            _SUBTITLE[sc] = {"text": text, "style": style,
                             "expire_ts": time.monotonic() + max(1.0, body.duration_s)}
    ok = sum(1 for v in results.values() if v)
    return {"ok": ok > 0, "spoken": results, "subtitle": body.subtitle,
            "screens": targets}


@app.get("/stream.flv")
async def stream_flv():
    """反代 SRS 的 HTTP-FLV 直播流。

    为什么要反代：SRS 的 FLV 响应不带 Access-Control-Allow-Origin，
    而交互页是从 :8000 (或别的源) 打开的，浏览器跨源拉 :8080 的流会被拦 → 画框转圈/黑屏。
    桥接层(:9000)有 CORS allow *，前端改拉 :9000/stream.flv 即同源放行，绕开 SRS 无 CORS。
    用 StreamingResponse 边收边吐，不缓冲整段（直播流是无限长的）。
    """
    client = httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(connect=5.0, read=None, write=10.0, pool=5.0))
    req = client.build_request("GET", SRS_FLV)
    upstream = await client.send(req, stream=True)
    if upstream.status_code != 200:
        await upstream.aclose()
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"SRS 流不可用: HTTP {upstream.status_code}（确认 LiveTalking 正在推流、SRS 在跑）")

    async def gen():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose()
            await client.aclose()

    return StreamingResponse(gen(), media_type="video/x-flv")


@app.get("/stream_portrait.flv")
async def stream_portrait_flv():
    """反代大屏竖版(9:16) FLV 直播流（livestream2）。供游客端大屏 web。
    HLS 用现成 /hls/livestream2.m3u8（/hls 通配反代已覆盖），无需单独路由。"""
    client = httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(connect=5.0, read=None, write=10.0, pool=5.0))
    upstream = await client.send(client.build_request("GET", SRS_FLV2), stream=True)
    if upstream.status_code != 200:
        await upstream.aclose(); await client.aclose()
        raise HTTPException(status_code=502, detail=f"竖版 SRS 流不可用: HTTP {upstream.status_code}（确认竖版 LiveTalking(8011) 在推 livestream2）")

    async def gen():
        try:
            async for chunk in upstream.aiter_bytes():
                yield chunk
        finally:
            await upstream.aclose(); await client.aclose()

    return StreamingResponse(gen(), media_type="video/x-flv")


# ── iOS H5 统一入口：桥接(:9000) 当唯一 https 源，反代 RAG + SRS-HLS ──────
# 背景：个人号小程序 <video> 播不了直播 HLS、又禁 live-player；改走 iPhone Safari
# （原生支持 HLS）。但 Safari 上 https 页面不能混入 http 子资源（mixed-content），
# 且多端口会跨源。故让桥接做唯一入口：H5 全部相对路径，桥接反代到各后端，
# 再用 cloudflared 把 :9000 暴露成可信 https 域名。

@app.get("/legacy")
async def serve_h5_legacy():
    """旧版纯手写 H5（回退）。商业级 React 版由文件末尾 StaticFiles 挂在 /。"""
    return FileResponse(H5_MOBILE_PATH, media_type="text/html")


@app.get("/vendor/mpegts.js")
async def serve_mpegts():
    """安卓浏览器/WebView 的 FLV 播放器，同源转发避免跨源/混合内容。"""
    return FileResponse(MPEGTS_JS_PATH, media_type="application/javascript")


@app.get("/api-doc")
async def api_doc():
    """渲染 API_DOC.md 为网页，供前端队友浏览器直接看最新接口契约（no-cache 永远最新）。
    每次更新后端把 API_DOC.md 同步到桥接所在目录即可，队友刷新 https://<autodl>:8443/api-doc 就是最新。"""
    md_path = pathlib.Path(__file__).resolve().parent.parent / "API_DOC.md"
    if not md_path.exists():
        raise HTTPException(status_code=404, detail="API_DOC.md 不存在（确认已同步到桥接所在目录）")
    text = md_path.read_text(encoding="utf-8")
    try:
        import markdown as _md
        body = _md.markdown(text, extensions=["tables", "fenced_code", "toc", "sane_lists"])
    except Exception:
        import html as _html
        body = f"<pre>{_html.escape(text)}</pre>"
    page = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>API 文档 · 智游导览</title>
<style>body{{max-width:920px;margin:0 auto;padding:24px;font:15px/1.7 -apple-system,system-ui,'Segoe UI',sans-serif;color:#1a1a1a}}
table{{border-collapse:collapse;width:100%;margin:12px 0;font-size:14px}}th,td{{border:1px solid #dde;padding:6px 10px;text-align:left;vertical-align:top}}
th{{background:#f6f8fa}}code{{background:#f1f3f5;padding:1px 5px;border-radius:4px;font-size:13px}}
pre{{background:#f6f8fa;padding:12px;border-radius:8px;overflow:auto}}pre code{{background:none;padding:0}}
h1,h2{{border-bottom:1px solid #eee;padding-bottom:5px;margin-top:32px}}h3{{margin-top:24px}}a{{color:#2563eb}}
blockquote{{border-left:3px solid #cbd5e1;margin:8px 0;padding:2px 14px;color:#475569;background:#f8fafc}}</style>
</head><body>{body}</body></html>"""
    return Response(content=page, media_type="text/html; charset=utf-8",
                    headers={"Cache-Control": "no-cache, must-revalidate"})


@app.get("/hls/{path:path}")
async def proxy_hls(path: str):
    """反代 SRS 的 HLS（m3u8 + ts）。m3u8 里 ts 是相对路径，仍命中本路由。"""
    url = f"{SRS_HLS_BASE}/{path}"
    async with httpx.AsyncClient(trust_env=False,
                                 timeout=httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)) as client:
        r = await client.get(url)
    # m3u8 用标准 MIME；ts 用 video/mp2t。直播分片禁缓存。
    ct = r.headers.get("content-type") or (
        "application/vnd.apple.mpegurl" if path.endswith(".m3u8") else "video/mp2t"
    )
    return Response(content=r.content, status_code=r.status_code, media_type=ct,
                    headers={"Cache-Control": "no-cache"})


@app.api_route("/rag/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_rag(path: str, request: Request):
    """反代 RAG 后端（/trip/greeting、/asr、/chat/image 等），转发方法/查询/体/头。"""
    url = f"{RAG_BASE}/{path}"
    body = await request.body()
    # 去掉 hop-by-hop 与会让上游错算长度的头
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ("host", "content-length", "connection", "accept-encoding")}
    async with httpx.AsyncClient(trust_env=False,
                                 timeout=httpx.Timeout(connect=5.0, read=60.0, write=30.0, pool=5.0)) as client:
        r = await client.request(request.method, url, params=dict(request.query_params),
                                 content=body, headers=headers)
    resp_headers = {k: v for k, v in r.headers.items()
                    if k.lower() not in ("content-length", "transfer-encoding", "connection", "content-encoding")}
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"), headers=resp_headers)


@app.api_route("/cloud/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_cloud(path: str, request: Request):
    """管理端历史用 /cloud/* 前缀访问 RAG（= /rag 别名）。单网关 :8443/admin 下同源转发到 RAG。"""
    url = f"{RAG_BASE}/{path}"
    body = await request.body()
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ("host", "content-length", "connection", "accept-encoding")}
    async with httpx.AsyncClient(trust_env=False,
                                 timeout=httpx.Timeout(connect=5.0, read=60.0, write=30.0, pool=5.0)) as client:
        r = await client.request(request.method, url, params=dict(request.query_params),
                                 content=body, headers=headers)
    resp_headers = {k: v for k, v in r.headers.items()
                    if k.lower() not in ("content-length", "transfer-encoding", "connection", "content-encoding")}
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"), headers=resp_headers)


# 反代管理端自有后端（:6008 的 /api/*：登录鉴权、AI 生成、会话、TTS）——
# 管理端经本网关 :8443/admin 提供时，其 /api 调用同源走这里转发到 :6008。
ADMIN_API_BASE = os.environ.get("ADMIN_API_BASE", "http://localhost:6008").rstrip("/")


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_admin_api(path: str, request: Request):
    url = f"{ADMIN_API_BASE}/api/{path}"
    body = await request.body()
    headers = {k: v for k, v in request.headers.items()
               if k.lower() not in ("host", "content-length", "connection", "accept-encoding")}
    async with httpx.AsyncClient(trust_env=False,
                                 timeout=httpx.Timeout(connect=5.0, read=120.0, write=30.0, pool=5.0)) as client:
        r = await client.request(request.method, url, params=dict(request.query_params),
                                 content=body, headers=headers)
    resp_headers = {k: v for k, v in r.headers.items()
                    if k.lower() not in ("content-length", "transfer-encoding", "connection", "content-encoding")}
    return Response(content=r.content, status_code=r.status_code,
                    media_type=r.headers.get("content-type"), headers=resp_headers)


@app.get("/live/avatar")
async def live_avatar(scenic_id: str = "lingshan"):
    """前端建立 WebRTC 连接前调用：返回该景区当前应使用的真实 avatar_id 与音色。
    把返回的 avatar_id 作为 LiveTalking /offer 的 `avatar` 参数即可实现形象切换。"""
    async with httpx.AsyncClient(trust_env=False) as client:
        avatar, voice, background_id = await _resolve_config(client, scenic_id)
    return {"avatar_id": avatar, "voice": voice, "background_id": background_id,
            "scenic_id": scenic_id}


class SetAvatarIn(BaseModel):
    avatar_id:  str                 # 形象 id（/digital-human/presets 里的 id）
    scenic_id:  str = "lingshan"
    sessionid:  str = "0"           # 直播会话 id（webapp 常量 "0"）
    screen:     str = "main"        # main=手机 16:9(8010)；portrait=大屏 9:16(8011)


@app.post("/live/avatar")
async def live_set_avatar(body: SetAvatarIn):
    """热拔插换形象：把 avatar_id 按景区/屏幕解析成已烘底板，调 LiveTalking /set_avatar
    在**不断流**前提下当场换人/换装（~1s）。与连接级 GET /live/avatar 互补。
    持久化为景区默认请另调 PUT /digital-human/config（本端点只管即时切换）。"""
    target = _pick_existing_avatar(
        _live_avatar_candidates(body.avatar_id, body.scenic_id, body.screen))
    lt_base = LIVETALKING_BASE if body.screen == "main" else LIVETALKING_BASE_2
    async with httpx.AsyncClient(trust_env=False, timeout=25) as client:
        try:
            r = await client.post(f"{lt_base}/set_avatar",
                                  json={"sessionid": body.sessionid, "avatar_id": target})
            data = r.json()
        except Exception as e:
            raise HTTPException(status_code=502,
                                detail=f"切换数字人失败: {type(e).__name__}: {e}")
    switched = isinstance(data, dict) and data.get("code") == 0
    if switched:
        _LIVE_AVATAR[body.screen] = body.avatar_id
    return {"ok": switched, "avatar_id": body.avatar_id, "resolved": target,
            "screen": body.screen, "detail": data}


class SetLipIn(BaseModel):
    scale:  float = 1.0               # DITTO_LIP_SCALE：说话嘴幅缩放，1.0=原始，越小张口越含蓄
    screen: str = "both"              # both / main / portrait


@app.post("/live/lip")
async def live_set_lip(body: SetLipIn):
    """热调数字人说话嘴幅（转发 LiveTalking /set_lip 写本进程 env DITTO_LIP_SCALE，
    motion_stitch 每帧读、把 lip 维度朝闭口拉；scale<1 收小张口，"刚刚不露齿" ~0.8）。"""
    scale = max(0.3, min(float(body.scale), 1.0))
    bases = []
    if body.screen in ("both", "main"):
        bases.append(("main", LIVETALKING_BASE))
    if body.screen in ("both", "portrait"):
        bases.append(("portrait", LIVETALKING_BASE_2))
    results = {}
    async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
        for name, base in bases:
            try:
                r = await client.post(f"{base}/set_lip", json={"scale": scale})
                results[name] = r.json()
            except Exception as e:  # noqa: BLE001
                results[name] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    ok = all(isinstance(v, dict) and v.get("code") == 0 for v in results.values()) if results else False
    return {"ok": ok, "scale": scale, "detail": results}


class SetEmotionIn(BaseModel):
    emotion:   str                    # happy/neutral/concerned/…（EMO_TO_DITTO 键）
    screen:    str = "portrait"
    sessionid: str = "0"


@app.post("/live/emotion")
async def live_set_emotion(body: SetEmotionIn):
    """热切数字人默认情绪基调（转发 LiveTalking /set_emotion；引擎方法已存在，仅需暴露路由）。"""
    lt_base = LIVETALKING_BASE if body.screen == "main" else LIVETALKING_BASE_2
    async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
        try:
            r = await client.post(f"{lt_base}/set_emotion",
                                  json={"sessionid": body.sessionid, "emotion": body.emotion})
            data = r.json()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status_code=502,
                                detail=f"切换情绪失败: {type(e).__name__}: {e}")
    ok = isinstance(data, dict) and data.get("code") == 0
    return {"ok": ok, "emotion": body.emotion, "screen": body.screen, "detail": data}


@app.get("/live/scenic-bg")
async def live_scenic_bg(scenic_id: str = "lingshan", screen: str = "portrait"):
    """大屏场景氛围底图：取该景区当前形象底板，缩小+高斯模糊成 JPEG 返回，
    供 kiosk 页面铺同源环境背景——页面与数字人视频天然同一个场景（换库不换码）。"""
    aid = f"dh_{scenic_id}"
    async with httpx.AsyncClient(trust_env=False, timeout=10) as client:
        try:
            r = await client.get(f"{RAG_BASE}/digital-human/config",
                                 params={"scenic_id": scenic_id})
            aid = (r.json() or {}).get("avatar_id") or aid
        except Exception:  # noqa: BLE001 — 配置读不到用智能默认底板
            pass
    target = _pick_existing_avatar(_live_avatar_candidates(aid, scenic_id, screen))
    src = os.path.join(DITTO_AVATARS_DIR, f"{target}.png")
    if not os.path.isfile(src):
        raise HTTPException(status_code=404, detail="该景区暂无形象底板")
    import tempfile
    cache = os.path.join(tempfile.gettempdir(),
                         f"scenicbg_{target}_{int(os.path.getmtime(src))}.jpg")
    if not os.path.isfile(cache):
        from PIL import Image, ImageFilter
        im = Image.open(src).convert("RGB")
        im.thumbnail((128, 128), Image.LANCZOS)
        im = im.filter(ImageFilter.GaussianBlur(3))
        im.save(cache, "JPEG", quality=82)
    return FileResponse(cache, media_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=600"})


@app.get("/live/avatar-plate")
async def live_avatar_plate(avatar_id: str, scenic_id: str = "lingshan",
                            screen: str = "portrait", background_id: str = ""):
    """管理端「离线预览」真值源：把(形象 id, 景区, 屏幕, 背景)按与 /live/avatar **完全相同**的
    候选解析逻辑落到实际底板，返回该底板缩略 JPEG（不模糊、不动直播流）。
    预览所见 = 热切后空闲画面，天然一致；调参即换图，零串扰。
    响应头 X-Resolved-Plate 便于前端提示"变体缺失已回落原图"。"""
    base = _pick_existing_avatar(_live_avatar_candidates(avatar_id, scenic_id, screen))
    target = _resolve_avatar_variant(base, background_id) if background_id else base
    src = os.path.join(DITTO_AVATARS_DIR, f"{target}.png")
    if not os.path.isfile(src):
        # 变体不存在 → 回落到 base 底板
        target = base
        src = os.path.join(DITTO_AVATARS_DIR, f"{target}.png")
    if not os.path.isfile(src):
        raise HTTPException(status_code=404, detail=f"无底板: {avatar_id}")
    import tempfile
    cache = os.path.join(tempfile.gettempdir(),
                         f"plate_{target}_{int(os.path.getmtime(src))}.jpg")
    if not os.path.isfile(cache):
        from PIL import Image
        im = Image.open(src).convert("RGB")
        if im.width > 540:
            im = im.resize((540, round(im.height * 540 / im.width)), Image.LANCZOS)
        im.save(cache, "JPEG", quality=88)
    return FileResponse(cache, media_type="image/jpeg",
                        headers={"Cache-Control": "no-cache", "X-Resolved-Plate": target})


@app.get("/live/health")
async def live_health():
    """探测 RAG 与 LiveTalking 是否都在线（联调时先打这个）。"""
    out = {
        "rag": False,
        "livetalking": False,
        "rag_base": RAG_BASE,
        "livetalking_base": LIVETALKING_BASE,
    }
    async with httpx.AsyncClient(trust_env=False) as client:
        try:
            r = await client.get(f"{RAG_BASE}/health", timeout=3)
            out["rag"] = r.status_code == 200
        except Exception:
            pass
        try:
            # LiveTalking 无 /health，用首页探活
            r = await client.get(f"{LIVETALKING_BASE}/index.html", timeout=3)
            out["livetalking"] = r.status_code == 200
        except Exception:
            pass
    return out


# ── 管理端 Vue web（队友工程的 dist）经桥接单网关在 /admin 提供 ──
# AutoDL 只对外映射 6006→:8443，:6008 无独立公网 → 把管理端挂到本网关 /admin。
# 管理端以 base='/admin/' 构建（资源 /admin/assets/*），CLOUD_BASE 直连本网关 /rag（同源）。
_ADMIN_DIST = next((p for p in (
    "/root/digital-human/frontend/dist",
    os.path.expanduser("~/digital-human/frontend/dist"),
) if os.path.isdir(p)), None)

if _ADMIN_DIST:
    _ADMIN_ENTRY = os.path.join(_ADMIN_DIST, "admin", "index.html")

    @app.get("/admin")
    async def _admin_root():
        return FileResponse(_ADMIN_ENTRY, media_type="text/html",
                            headers={"Cache-Control": "no-cache"})

    @app.get("/admin/{path:path}")
    async def _admin_spa(path: str):
        f = os.path.join(_ADMIN_DIST, path)
        if path and os.path.isfile(f):
            return FileResponse(f)
        return FileResponse(_ADMIN_ENTRY, media_type="text/html",  # SPA 回退=管理端入口
                            headers={"Cache-Control": "no-cache"})


# ── React 商业级前端：StaticFiles 挂在 /（必须置于所有 API 路由之后，API 优先匹配）──
# html=True 让 / 发 index.html、/assets/* 发静态资源；SPA 单页直接命中 index。
# dist 不存在（未构建）则回退发旧版手写 H5，保证始终有可用页面。
if os.path.isdir(WEBAPP_DIST):
    # index.html 必须 no-cache：内容哈希资源(/assets/*)可永久缓存，但 index 一旦被浏览器
    # 缓存，重新构建后手机/演示机会一直加载旧 bundle（实测踩坑：旧 mpegts 无重连逻辑）。
    # 显式路由 "/" 优先于 StaticFiles mount 命中，强制每次 revalidate。
    _INDEX_HTML = os.path.join(WEBAPP_DIST, "index.html")

    @app.get("/")
    async def _serve_index():
        return FileResponse(_INDEX_HTML, media_type="text/html",
                            headers={"Cache-Control": "no-cache, must-revalidate"})

    app.mount("/", StaticFiles(directory=WEBAPP_DIST, html=True), name="webapp")
else:
    @app.get("/")
    async def _serve_legacy_root():
        return FileResponse(H5_MOBILE_PATH, media_type="text/html")
