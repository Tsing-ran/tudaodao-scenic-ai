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
    "voice_lively_f": "Cherry",   # 活泼甜美女声
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
}
DEFAULT_AVATAR = "sweet_bob_ditto"

# Ditto 源肖像目录：场景背景变体 <base>_bg_<bg_id>.png 也放这里
# （由 scripts/gen_avatar_background.py compose 产出；桥接与 LiveTalking 同机，可直接查文件）
DITTO_AVATARS_DIR = os.environ.get(
    "DITTO_AVATARS_DIR",
    os.path.expanduser("~/Desktop/LiveTalking/data/ditto_avatars"))


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


@app.post("/live/ask")
async def live_ask(body: AskIn):
    """游客问一句 → 订阅 RAG 句子级流式 → 每出一句立即驱动数字人开口。

    关键时序（压住 <5s 端到端延迟的核心）：
      RAG 第 1 句生成完(~0.8s) → 立刻送 LiveTalking 说出来 → 数字人即刻开口，
      与此同时 RAG 继续生成后面的句子并排队播放，而不是等整段答案。

    barge-in：进来即把本会话代号 +1。任何更早的 /live/ask 在其驱动循环里发现自己已非最新代
    → 立即停推后续句（新问首句 interrupt 会冲掉旧音频残留），实现"用户打断、立刻转答新问题"。
    """
    # state 按屏幕命名空间隔离（手机端 main 与大屏 portrait 即使 sessionid 都是 "0" 也不互相打断）
    sid = f"{body.screen}:{body.sessionid}"
    lt_base = LIVETALKING_BASE if body.screen == "main" else LIVETALKING_BASE_2
    my_gen = _ASK_GEN[sid] = _ASK_GEN.get(sid, 0) + 1

    # ── L1 命中：高频问答直接返回预渲染成品视频，0 GPU·0 LLM·<0.5s（不调 RAG、不占渲染槽）──
    hit = _faq_lookup(body.scenic_id, body.message)
    if hit:
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
            drive_enabled = True   # 大屏=独立 LiveTalking 实例(8011)，直接驱动，不占手机端共享渲染池

        async def _release_slot_if_owner(delay: float = 0.0):
            """释放本会话渲染槽——仅当本问仍是最新代（未被 barge-in 取代）。delay>0 = 说完延迟释放。"""
            if delay > 0:
                await asyncio.sleep(delay)
            if _ASK_GEN.get(sid) == my_gen and _SESSION_SLOT.get(sid):
                _SESSION_SLOT[sid] = False
                await POOL.release()

        intent = "qa"
        emotion = "neutral"
        sentences: list[str] = []
        drive_failures = 0
        first = True

        async def _drive(text: str, interrupt: bool):
            """把一句话送数字人说出来。单句失败不中断整条流，只计数。"""
            nonlocal drive_failures
            try:
                await client.post(
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
            except Exception:
                drive_failures += 1

        # 2) 订阅 RAG SSE 流，逐句驱动数字人
        superseded = False
        try:
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
                },
            ) as resp:
                resp.raise_for_status()
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
                        break
                    if etype == "intent":
                        intent = evt.get("value", intent)
                    elif etype == "emotion":
                        # emotion 事件在第一个 sentence 之前下发，第一句即可带上正确情绪
                        emotion = evt.get("value", emotion)
                    elif etype == "sentence":
                        text = (evt.get("text") or "").strip()
                        if not text:
                            continue
                        sentences.append(text)
                        # 第一句打断上一轮残留，后续句排队顺序播放（降级模式不驱动，只收集文字）
                        if drive_enabled:
                            await _drive(text, interrupt=(body.interrupt and first))
                        first = False
                    # end 事件无需特殊处理
        except Exception as e:
            await _release_slot_if_owner()
            raise HTTPException(
                status_code=502,
                detail=f"RAG 流式调用失败: {type(e).__name__}: {e}",
            )

        # barge-in：本问已被取代 → 槽已归新问（_release 因非最新代会自动跳过），安静返回；
        #   前端按提问序号丢弃本响应，不覆盖新问的 UI
        if superseded:
            return {
                "ok": True, "reply": "".join(sentences), "superseded": True,
                "mode": "text", "degraded": False, "intent": intent,
                "emotion": emotion, "voice": voice, "capacity": POOL.status(),
            }

        if not sentences:
            await _release_slot_if_owner()
            raise HTTPException(status_code=502, detail="RAG 未产出任何句子")

        reply = "".join(sentences)
        # 槽位释放：按估算说话时长延迟释放（说话期间占用，说完即可被下一个游客复用）；
        # 仅"最新一问"释放——被 barge-in 取代的旧问 _release 会因非最新代自动跳过，把槽留给新问
        asyncio.create_task(_release_slot_if_owner(len(reply) / SPEAK_CPS + 1.0))

        # 数字人是否真的开口了：启用驱动 且 至少一句送达成功
        spoke = drive_enabled and drive_failures < len(sentences)
        reason = None if spoke else (
            "livetalking_down" if not lt_ok else ("pool_full" if not drive_enabled else "drive_failed"))
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
        }


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


@app.post("/live/say")
async def live_say(body: SayIn):
    """让数字人直接说出一段给定文字（不走 RAG）。

    用于「拍照视觉定位」闭环：游客拍照 → /chat/image 出定位+讲解+指路文字 →
    本端点把这段文字按景区音色送 LiveTalking /human，让数字人开口说。
    """
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 不能为空")
    async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)) as client:
        if body.voice_id and body.voice_id in VOICE_MAP:
            voice = VOICE_MAP[body.voice_id]
        else:
            _, voice, _ = await _resolve_config(client, body.scenic_id)
        say_base = LIVETALKING_BASE if body.screen == "main" else LIVETALKING_BASE_2
        try:
            await client.post(
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
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"驱动数字人失败: {type(e).__name__}: {e}")
    return {"ok": True, "voice": voice, "chars": len(text)}


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


@app.get("/live/avatar")
async def live_avatar(scenic_id: str = "lingshan"):
    """前端建立 WebRTC 连接前调用：返回该景区当前应使用的真实 avatar_id 与音色。
    把返回的 avatar_id 作为 LiveTalking /offer 的 `avatar` 参数即可实现形象切换。"""
    async with httpx.AsyncClient(trust_env=False) as client:
        avatar, voice, background_id = await _resolve_config(client, scenic_id)
    return {"avatar_id": avatar, "voice": voice, "background_id": background_id,
            "scenic_id": scenic_id}


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
