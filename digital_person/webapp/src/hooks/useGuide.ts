import { useCallback, useEffect, useRef, useState } from 'react'
import type { RefObject } from 'react'
import * as api from '@/lib/api'
import type { Lang } from '@/lib/i18n'
import { GROUPS, INTERESTS, LANGS, AGES, PACES, MOBILITIES, PURPOSES, FIRSTTIMES, SIT_DEFAULTS, makeT } from '@/lib/i18n'
import * as trace from '@/lib/trace'
import type { Trace, Badge } from '@/lib/trace'
import { badges } from '@/lib/trace'
import { track as trackEvent } from '@/lib/track'
import { applyScenicTheme } from '@/lib/theme'
import { watchPositionGCJ02, makeGeofence } from '@/lib/geo'

// iOS Safari 原生播 HLS、不支持 MSE/FLV；安卓 Chromium 反之。
const isIOS =
  /iP(hone|ad|od)/.test(navigator.userAgent) ||
  (navigator.platform === 'MacIntel' && (navigator as unknown as { maxTouchPoints: number }).maxTouchPoints > 1)
// iOS 要求 <5s 响应时必须走低延迟 WebRTC；HLS 只作为兜底。
const isSafari =
  /^((?!chrome|android|crios|fxios|edg).)*safari/i.test(navigator.userAgent)
const forceHls = new URLSearchParams(location.search).get('player') === 'hls'
const rtcInitialPlayoutDelay = isIOS || isSafari ? 0.65 : 0.4
const rtcSmoothPlayoutDelay = isIOS || isSafari ? 1.2 : 0.8
const rtcMaxPlayoutDelay = isIOS || isSafari ? 1.8 : 1.2
const rtcStatsIntervalMs = 3000
const rtcStatsReportMs = 10000
const liveHlsUrl = () => `/hls/livestream.m3u8?_=${Date.now()}`

interface RtcSample {
  videoPacketsLost?: number
  videoPacketsReceived?: number
  videoFramesDecoded?: number
  videoFramesDropped?: number
  videoFreezeCount?: number
  videoJitter?: number
  audioPacketsLost?: number
  audioPacketsReceived?: number
  audioJitter?: number
  rtt?: number
  incomingBitrate?: number
}

function statNumber(s: Record<string, unknown>, key: string): number | undefined {
  const v = s[key]
  return typeof v === 'number' && Number.isFinite(v) ? v : undefined
}

function metricDelta(now?: number, prev?: number): number {
  if (now == null || prev == null) return 0
  return Math.max(0, now - prev)
}

function roundMetric(v: number | undefined, digits = 3): number | undefined {
  if (v == null || !Number.isFinite(v)) return undefined
  const m = 10 ** digits
  return Math.round(v * m) / m
}

function applyRtcReceiverDelay(pc: RTCPeerConnection, delay: number) {
  try {
    pc.getReceivers().forEach((r) => {
      try { (r as unknown as { jitterBufferTarget: number }).jitterBufferTarget = delay } catch { /* ignore */ }
      try { (r as unknown as { playoutDelayHint: number }).playoutDelayHint = delay } catch { /* ignore */ }
    })
  } catch { /* ignore */ }
}

function readRtcStats(report: RTCStatsReport): RtcSample {
  const out: RtcSample = {}
  report.forEach((raw) => {
    const s = raw as unknown as Record<string, unknown>
    const type = String(s.type ?? '')
    const kind = String(s.kind ?? s.mediaType ?? '')
    if (type === 'inbound-rtp' && kind === 'video') {
      out.videoPacketsLost = statNumber(s, 'packetsLost')
      out.videoPacketsReceived = statNumber(s, 'packetsReceived')
      out.videoFramesDecoded = statNumber(s, 'framesDecoded')
      out.videoFramesDropped = statNumber(s, 'framesDropped')
      out.videoFreezeCount = statNumber(s, 'freezeCount')
      out.videoJitter = statNumber(s, 'jitter')
    } else if (type === 'inbound-rtp' && kind === 'audio') {
      out.audioPacketsLost = statNumber(s, 'packetsLost')
      out.audioPacketsReceived = statNumber(s, 'packetsReceived')
      out.audioJitter = statNumber(s, 'jitter')
    } else if (type === 'candidate-pair') {
      const state = String(s.state ?? '')
      const selected = s.nominated === true || s.selected === true
      if (state === 'succeeded' && (selected || out.rtt == null)) {
        out.rtt = statNumber(s, 'currentRoundTripTime')
        out.incomingBitrate = statNumber(s, 'availableIncomingBitrate')
      }
    }
  })
  return out
}

export type MicState = 'idle' | 'listening' | 'recording' | 'recognizing'
export type Status = 'idle' | 'connecting' | 'connected' | 'buffering' | 'error'
export interface Meta { intent?: string; emotion?: string; location?: string; timing?: string; greet?: boolean; degraded?: boolean; cached?: boolean }
// 对话流消息：用户气泡 / 助手气泡。assistant 在等待时 thinking=true（显思考态），
// 拿到回答后填 text + meta，置 animate=true 触发打字机逐字显示（reduced-motion 直接全文）。
// image = 用户拍的那张照片的 object URL（仅 role:'user'）：让「我发了什么」在屏幕上看得见，
// 而不是只留一句「拍了一张照片」。voice = 该条由语音转写而来 → UI 标「语音」并允许纠错重问。
export interface Msg {
  id: string; role: 'user' | 'assistant'; text: string; meta?: Meta
  thinking?: boolean; animate?: boolean; streaming?: boolean
  image?: string; voice?: boolean
}
let _msgSeq = 0
const newId = () => `m${++_msgSeq}_${Date.now()}`

export const SCENICS = [
  { id: 'lingshan', name: '灵山胜境' },
  { id: 'gugong', name: '故宫' },
  { id: 'nihuawan', name: '拈花湾' },
  { id: 'xihu', name: '西湖' },
  { id: 'huangshan', name: '黄山' },
]

// localStorage 读取（带合法性校验，坏值回落默认）
function loadPref(key: string, valid: string[], fallback: string) {
  try {
    const v = localStorage.getItem(key)
    return v && valid.includes(v) ? v : fallback
  } catch { return fallback }
}
function loadInterests() {
  try {
    const raw = JSON.parse(localStorage.getItem('lingjing.interests') || '[]')
    const ids = INTERESTS.map((i) => i.id)
    return Array.isArray(raw) ? raw.filter((x): x is string => typeof x === 'string' && ids.includes(x)) : []
  } catch { return [] }
}
const savePref = (key: string, val: string) => { try { localStorage.setItem(key, val) } catch { /* ignore */ } }

export function useGuide(videoRef: RefObject<HTMLVideoElement | null>) {
  // 开场偏好持久化：记住景区/同行人/兴趣/语言，回访免开场
  const [scenic, setScenic] = useState(() => loadPref('lingjing.scenic', SCENICS.map((s) => s.id), 'lingshan'))
  const [groupType, setGroupType] = useState(() => loadPref('lingjing.group', GROUPS.map((g) => g.id), 'adult'))
  const [interests, setInterests] = useState<string[]>(loadInterests)
  const [lang, setLang] = useState<Lang>(() => loadPref('lingjing.lang', LANGS.map((l) => l.id), 'zh') as Lang)
  // 自身情况标签（多步 onboarding 新增 5 维）：默认值=中性，老画像缺键回落默认 → 行为零变化
  const [age, setAge] = useState(() => loadPref('lingjing.age', AGES.map((a) => a.id), SIT_DEFAULTS.age))
  const [pace, setPace] = useState(() => loadPref('lingjing.pace', PACES.map((p) => p.id), SIT_DEFAULTS.pace))
  const [mobility, setMobility] = useState(() => loadPref('lingjing.mobility', MOBILITIES.map((m) => m.id), SIT_DEFAULTS.mobility))
  const [purpose, setPurpose] = useState(() => loadPref('lingjing.purpose', PURPOSES.map((p) => p.id), SIT_DEFAULTS.purpose))
  const [firstTime, setFirstTime] = useState(() => loadPref('lingjing.firsttime', FIRSTTIMES.map((f) => f.id), SIT_DEFAULTS.first_time))
  useEffect(() => { savePref('lingjing.scenic', scenic) }, [scenic])
  useEffect(() => { savePref('lingjing.group', groupType) }, [groupType])
  useEffect(() => { savePref('lingjing.interests', JSON.stringify(interests)) }, [interests])
  useEffect(() => { savePref('lingjing.lang', lang) }, [lang])
  useEffect(() => { savePref('lingjing.age', age) }, [age])
  useEffect(() => { savePref('lingjing.pace', pace) }, [pace])
  useEffect(() => { savePref('lingjing.mobility', mobility) }, [mobility])
  useEffect(() => { savePref('lingjing.purpose', purpose) }, [purpose])
  useEffect(() => { savePref('lingjing.firsttime', firstTime) }, [firstTime])
  const [status, setStatus] = useState<Status>('idle')
  const [thinking, setThinking] = useState(false)
  const [busy, setBusy] = useState(false)
  const [reply, setReply] = useState('')          // 兼容：最后一条助手文本（Postcard/trace 等如有依赖）
  const [meta, setMeta] = useState<Meta>({})       // 兼容：最后一条助手 meta（舞台 pills 仍读它）
  const [messages, setMessages] = useState<Msg[]>([])  // 对话流（一问一答气泡）
  // 推一条消息，返回其 id
  const pushMsg = useCallback((m: Omit<Msg, 'id'>) => {
    const id = newId()
    setMessages((prev) => [...prev, { ...m, id }])
    return id
  }, [])
  // 按 id 局部更新某条消息
  const patchMsg = useCallback((id: string, patch: Partial<Msg>) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)))
  }, [])
  const [mic, setMicState] = useState<MicState>('idle')
  // 录音可视化：micLevel = 归一化音量(0~1) 驱动电平柱；micMs = 已录毫秒数驱动计时器。
  // 两者只在录音期间有意义，停录即归零。没有它们，用户看不出麦克风到底在不在工作。
  const [micLevel, setMicLevel] = useState(0)
  const [micMs, setMicMs] = useState(0)
  const micStartRef = useRef(0)
  // heard = 最近一次语音识别出的文字。单独存一份（而不是只靠 messages）是为了让「你说：…」
  // 在舞台上持续可见——用户必须能核对自己被听成了什么，这正是本次要解决的问题。
  const [heard, setHeard] = useState('')
  // 拍照产生的 object URL：卸载时统一 revoke，避免整场会话累积泄漏
  const photoUrlsRef = useRef<string[]>([])
  useEffect(() => () => { photoUrlsRef.current.forEach((u) => { try { URL.revokeObjectURL(u) } catch { /* 已回收 */ } }) }, [])
  const [traceState, setTraceState] = useState<Trace>(() => trace.load())
  // 徽章解锁队列（居中高光卡逐个展示）+ 提交 trace 时 diff 出新解锁的徽章 → 入队 → App 弹庆祝
  const [celebrations, setCelebrations] = useState<Badge[]>([])
  const traceRef = useRef(traceState)
  const commitTrace = useCallback((next: Trace) => {
    const before = new Set(badges(traceRef.current).filter((b) => b.earned).map((b) => b.id))
    const newly = badges(next).filter((b) => b.earned && !before.has(b.id))
    traceRef.current = next
    setTraceState(next)
    if (newly.length) setCelebrations((q) => [...q, ...newly])
  }, [])
  const dismissCelebration = useCallback(() => setCelebrations((q) => q.slice(1)), [])
  // 足迹/徽章复位：trace 持久化在 localStorage 且跨会话累计 → 彩排走过一遍后徽章全解锁，
  // 正式录制时「我已到达」不会再弹庆祝卡。给设置里一个复位入口，保证每次录制都是干净状态。
  const resetTrace = useCallback(() => {
    trace.reset()
    const t = trace.load()
    traceRef.current = t
    setTraceState(t)
    setCelebrations([])
  }, [])

  // 音量渐变（rAF）：打断时"逐渐减弱"、抽屉打开时压低直播音（不影响下一条输入）。单飞行 ramp，新调用取消旧的。
  const volRampRef = useRef<number | null>(null)
  const rampVolume = useCallback((target: number, ms = 400) => {
    const v = videoRef.current
    if (!v) return
    if (volRampRef.current != null) { cancelAnimationFrame(volRampRef.current); volRampRef.current = null }
    const to = Math.max(0, Math.min(1, target))
    let from = 1
    try { from = v.volume } catch { /* srcObject 未就绪 */ }
    if (ms <= 0) { try { v.volume = to } catch { /* ignore */ } return }
    const t0 = performance.now()
    const step = () => {
      const p = Math.min(1, (performance.now() - t0) / ms)
      try { v.volume = from + (to - from) * p } catch { /* ignore */ }
      if (p < 1) volRampRef.current = requestAnimationFrame(step)
      else volRampRef.current = null
    }
    volRampRef.current = requestAnimationFrame(step)
  }, [videoRef])
  const [clipUrl, setClipUrl] = useState('')   // L1 命中：高频问答成品视频，在舞台直接播
  // 舞台字幕（数字人「正在说的话」）：卡拉OK逐字贴在画面底部，与吐字同步。
  // 聊天流只保留完整成句的历史；实时演出在这条字幕上，故聊天流不再每字重渲染（根治滚动抢夺）。
  const [caption, setCaption] = useState('')
  const [captionStreaming, setCaptionStreaming] = useState(false)
  // 数字人「此刻真的还在说」的真信号（桥接 /live/now-playing）。
  // 为什么不能用 busy/captionStreaming 代替：字幕按 CPS_SPEAK=5.0 推进且提前 1.5s 起步，
  // 而桥接按 SPEAK_CPS=4.5 喂句 → 字幕总比嘴早收尾 ~3-5s（长答案更久）；拍照路径更极端，
  // busy 在 liveSay 发出的同刻就被 finally 置 false，而嘴还要说 20-30s。
  // 这段窗口正是用户要的「终止数字人继续说话」，只能问后端。
  const [speaking, setSpeaking] = useState(false)
  const speakingMuteUntil = useRef(0)   // 打断后的抑制窗：忽略在途的旧轮询响应

  const [guideName, setGuideName] = useState('智能导览')
  const guideNameRef = useRef(guideName)
  useEffect(() => { guideNameRef.current = guideName }, [guideName])
  // 游客形象精调偏好（空 = 跟随管理端景区默认）；音色消息级即时生效，形象下次唤醒生效
  const [voiceId, setVoiceIdState] = useState<string>(() => { try { return localStorage.getItem('lingjing.voice') || '' } catch { return '' } })
  const [avatarPref, setAvatarPrefState] = useState<string>(() => { try { return localStorage.getItem('lingjing.avatar') || '' } catch { return '' } })
  const setVoiceId = useCallback((v: string) => { setVoiceIdState(v); try { localStorage.setItem('lingjing.voice', v) } catch { /* ignore */ } }, [])
  const setAvatarPref = useCallback((a: string) => { setAvatarPrefState(a); try { localStorage.setItem('lingjing.avatar', a) } catch { /* ignore */ } }, [])
  // 主动开讲（地理围栏）：默认关；开启且已连接时持续定位，走到景点 50m 内自动让数字人开讲
  const [autoNarrate, setAutoNarrateState] = useState<boolean>(() => { try { return localStorage.getItem('lingjing.autonarrate') === '1' } catch { return false } })
  const setAutoNarrate = useCallback((v: boolean) => { setAutoNarrateState(v); try { localStorage.setItem('lingjing.autonarrate', v ? '1' : '0') } catch { /* ignore */ } }, [])
  const [geoArrival, setGeoArrival] = useState('')   // 刚到达的景点名（顶部提示条）
  const voiceRef = useRef(voiceId)
  useEffect(() => { voiceRef.current = voiceId }, [voiceId])
  const scenicRef = useRef(scenic)
  useEffect(() => { scenicRef.current = scenic }, [scenic])
  // 切景区 → 套用该景区主题色（整站换肤）+ 拿到该景区导游名（文案动态化）
  useEffect(() => {
    let alive = true
    applyScenicTheme(scenic).then((n) => { if (alive) setGuideName(n) })
    return () => { alive = false }
  }, [scenic])
  const groupRef = useRef(groupType)
  useEffect(() => { groupRef.current = groupType }, [groupType])
  const langRef = useRef(lang)
  useEffect(() => { langRef.current = lang }, [lang])
  const interestsRef = useRef(interests)
  useEffect(() => { interestsRef.current = interests }, [interests])
  // 自身情况标签 refs（供 ask/recommend 等稳定回调读最新值，Phase B 透传给后端）
  const ageRef = useRef(age); useEffect(() => { ageRef.current = age }, [age])
  const paceRef = useRef(pace); useEffect(() => { paceRef.current = pace }, [pace])
  const mobilityRef = useRef(mobility); useEffect(() => { mobilityRef.current = mobility }, [mobility])
  const purposeRef = useRef(purpose); useEffect(() => { purposeRef.current = purpose }, [purpose])
  const firstTimeRef = useRef(firstTime); useEffect(() => { firstTimeRef.current = firstTime }, [firstTime])
  const backendLang = () => (LANGS.find((l) => l.id === langRef.current)?.backend || 'auto')
  // 组装自身情况快照（读 ref 取最新）：发给后端调讲解侧重 + 推荐。全默认时后端按"空"处理，
  // 缓存键/prompt 与现状逐字节一致（零准确率影响），故可无条件发送。
  const sitPayload = () => ({
    age: ageRef.current, pace: paceRef.current, mobility: mobilityRef.current,
    purpose: purposeRef.current, first_time: firstTimeRef.current,
  })

  // ── 个性化推荐「为你定制」：画像×兴趣×此刻 → 推荐卡（loadRecos 稳定，读 ref 取最新画像）──
  const [recos, setRecos] = useState<api.RecoCard[]>([])
  const [recoBasis, setRecoBasis] = useState<string[]>([])
  const [recosLoading, setRecosLoading] = useState(false)
  const recoSeqRef = useRef(0)
  const loadRecos = useCallback(async () => {
    const seq = ++recoSeqRef.current
    setRecosLoading(true)
    try {
      const r = await api.recommend({ scenic: scenicRef.current, groupType: groupRef.current, interests: interestsRef.current, lang: backendLang(), situation: sitPayload() })
      if (seq !== recoSeqRef.current) return       // 被更新的画像取代 → 丢弃旧结果
      setRecos(r.cards); setRecoBasis(r.basis)
    } catch { if (seq === recoSeqRef.current) setRecos([]) }
    finally { if (seq === recoSeqRef.current) setRecosLoading(false) }
  }, [])
  // 绑定当前景区/画像的埋点上报（供 App 调用）
  const track = useCallback((type: string, payload?: Record<string, unknown>) =>
    trackEvent(type, { scenic: scenicRef.current, groupType: groupRef.current, lang: langRef.current }, payload), [])
  const startedRef = useRef(false)
  const playerRef = useRef<{ destroy: () => void } | null>(null)
  const greetedRef = useRef(false)
  // ── FLV 客户端自愈：发布端每 5-10min 掉线(python_rtmpstream 无自动重连)，服务端
  //    RTMP 看门狗(streamout/rtmp.py)会把流救活，但 mpegts.js 收到 Early-EOF 后会冻死。
  //    这里监听 ERROR → 延迟重连，与服务端看门狗闭环，消除掉线黑屏。──
  const wantStreamRef = useRef(false)        // 是否应保持直播(连上置真)
  const reconnectingRef = useRef(false)      // 重连进行中(防重入)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectFlvRef = useRef<(() => void) | null>(null)
  const startWebRTCRef = useRef<((v: HTMLVideoElement) => Promise<void>) | null>(null)  // WebRTC 自愈用
  const askSeqRef = useRef(0)               // barge-in：提问序号，旧问异步结果按此丢弃
  const rtcStatsTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const rtcStatsSeqRef = useRef(0)
  const rtcQualityRef = useRef<{
    delay: number
    poorWindows: number
    lastReportAt: number
    prev?: RtcSample
  }>({ delay: rtcInitialPlayoutDelay, poorWindows: 0, lastReportAt: 0 })

  const stopRtcStats = useCallback(() => {
    rtcStatsSeqRef.current += 1
    if (rtcStatsTimerRef.current) {
      clearInterval(rtcStatsTimerRef.current)
      rtcStatsTimerRef.current = null
    }
  }, [])

  // ── 主动迎宾 ──────────────────────────────────────────────
  const greet = useCallback(async () => {
    if (greetedRef.current) return
    greetedRef.current = true
    // ① 优先：连接时先播「含手势」预渲染欢迎片（自带语音+挥手），播完 onEnded 回归实时。
    //    实时 Ditto 驱动静态肖像、出不了手 → 手势只能走离线预渲染片；命中即不再 liveSay（避免双声）。
    try {
      const gc = await api.greetingClip(scenicRef.current, groupRef.current)
      if (gc?.clip) {
        const m: Meta = { greet: true }
        if (gc.text) {
          setReply(gc.text); setMeta(m)
          pushMsg({ role: 'assistant', text: gc.text, meta: m })
          setCaption(gc.text); setCaptionStreaming(false)
        }
        setClipUrl(gc.clip)                              // 舞台播含手势欢迎片（自带音频）
        return
      }
    } catch { /* 取片失败 → 回退实时迎宾 */ }
    // ② 回退：实时数字人开口迎宾（无手势，原逻辑）
    setThinking(true)
    const aid = pushMsg({ role: 'assistant', text: '', thinking: true })
    try {
      const g = await api.greeting(scenicRef.current, groupRef.current, sitPayload())
      if (g.text) {
        const m: Meta = { greet: true }
        setReply(g.text); setThinking(false); setMeta(m)
        patchMsg(aid, { text: g.text, thinking: false, meta: m })
        setCaption(g.text); setCaptionStreaming(false)   // 迎宾词上字幕（贴脸）
        api.liveSay(g.text, scenicRef.current, g.emotion || 'happy', voiceRef.current || undefined)
      } else { setThinking(false); setMessages((prev) => prev.filter((m) => m.id !== aid)) }
    } catch { setThinking(false); setMessages((prev) => prev.filter((m) => m.id !== aid)) }
  }, [pushMsg, patchMsg])

  // 建（或重建）安卓/桌面 FLV 播放器，并挂 ERROR→重连。每次重建都销毁旧播放器。
  const startFlv = useCallback(async (v: HTMLVideoElement) => {
    stopRtcStats()
    const mpegts = (await import('mpegts.js')).default
    if (!mpegts.isSupported()) throw new Error('浏览器不支持 FLV(MSE)')
    if (playerRef.current) { try { playerRef.current.destroy() } catch { /* ignore */ } playerRef.current = null }
    // 低延迟直播播放：小 IO 缓冲吸收公网代理 jitter（防空缓冲卡顿/转圈），
    // 同时开 liveBufferLatencyChasing 追直播边缘——落后超 3s 即追回 ~0.8s，延迟不无限漂移。
    // URL 必须绝对：enableWorker 让 IO loader 跑在 blob: worker 里，而 blob: URL 没有可解析的
    // base，worker 内 fetch('/stream.flv') 会直接抛 "Failed to parse URL"。用 location 兜成绝对
    // 地址即可（仍是同源，反代/网关行为不变）。
    const flvUrl = new URL('/stream.flv', location.href).href
    const p = mpegts.createPlayer(
      { type: 'flv', url: flvUrl, isLive: true },
      {
        enableWorker: true,
        enableStashBuffer: true,
        stashInitialSize: 384,
        liveBufferLatencyChasing: true,
        liveBufferLatencyChasingOnPaused: true,
        liveBufferLatencyMaxLatency: 3.0,
        liveBufferLatencyMinRemain: 0.8,
        autoCleanupSourceBuffer: true,
      },
    )
    // 流中断(发布端掉线/Early-EOF/网络/cloudflare 524)→ 触发重连循环
    p.on(mpegts.Events.ERROR, () => { reconnectFlvRef.current?.() })
    p.attachMediaElement(v)
    p.load()
    await p.play()
    playerRef.current = p as unknown as { destroy: () => void }
  }, [stopRtcStats])

  // WebRTC 播放（杭州网关：亚秒延迟 + 自带抖动缓冲，根治远端长途卡顿）。SRS 原生 /rtc/v1/play，
  // 把 RTMP(H264+AAC) 转 WebRTC(H264+Opus) 推给浏览器。iOS Safari/安卓/桌面全支持。
  // AutoDL 部署无 /rtc 端点 → fetch 非 2xx 抛错，connect 回退 HLS/FLV。
  const startWebRTC = useCallback(async (v: HTMLVideoElement) => {
    stopRtcStats()
    if (playerRef.current) { try { playerRef.current.destroy() } catch { /* ignore */ } playerRef.current = null }
    const pc = new RTCPeerConnection()
    pc.addTransceiver('video', { direction: 'recvonly' })
    pc.addTransceiver('audio', { direction: 'recvonly' })
    pc.ontrack = (e) => { if (e.streams[0]) v.srcObject = e.streams[0] }
    pc.oniceconnectionstatechange = () => {
      const st = pc.iceConnectionState
      if ((st === 'failed' || st === 'disconnected') && wantStreamRef.current && !reconnectingRef.current) {
        reconnectingRef.current = true; setStatus('buffering')
        reconnectTimerRef.current = setTimeout(async () => {
          reconnectingRef.current = false
          if (!wantStreamRef.current) return
          try { await startWebRTCRef.current?.(v); setStatus('connected') } catch { /* 下次 ice 事件再试 */ }
        }, 1500)
      }
    }
    const offer = await pc.createOffer()
    await pc.setLocalDescription(offer)
    const resp = await fetch('/rtc/v1/play/', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api: location.origin + '/rtc/v1/play/',
        streamurl: 'webrtc://' + location.hostname + '/live/livestream',
        clientip: null, sdp: offer.sdp,
      }),
    })
    if (!resp.ok) { pc.close(); throw new Error('no-rtc ' + resp.status) }
    const data = await resp.json()
    if (data.code !== 0) { pc.close(); throw new Error('rtc-code ' + data.code) }
    await pc.setRemoteDescription({ type: 'answer', sdp: data.sdp })
    // 初始仍保持低延迟；如果 iOS 现场统计连续变差，再提升接收端抖动缓冲。
    applyRtcReceiverDelay(pc, rtcInitialPlayoutDelay)
    rtcQualityRef.current = { delay: rtcInitialPlayoutDelay, poorWindows: 0, lastReportAt: 0 }
    const statsSeq = ++rtcStatsSeqRef.current
    const sampleStats = async () => {
      if (statsSeq !== rtcStatsSeqRef.current || pc.connectionState === 'closed') return
      try {
        const sample = readRtcStats(await pc.getStats())
        if (statsSeq !== rtcStatsSeqRef.current) return
        const q = rtcQualityRef.current
        const prev = q.prev
        const videoLostDelta = metricDelta(sample.videoPacketsLost, prev?.videoPacketsLost)
        const videoRecvDelta = metricDelta(sample.videoPacketsReceived, prev?.videoPacketsReceived)
        const audioLostDelta = metricDelta(sample.audioPacketsLost, prev?.audioPacketsLost)
        const audioRecvDelta = metricDelta(sample.audioPacketsReceived, prev?.audioPacketsReceived)
        const framesDroppedDelta = metricDelta(sample.videoFramesDropped, prev?.videoFramesDropped)
        const framesDecodedDelta = metricDelta(sample.videoFramesDecoded, prev?.videoFramesDecoded)
        const freezeDelta = metricDelta(sample.videoFreezeCount, prev?.videoFreezeCount)
        const videoLossRate = videoLostDelta + videoRecvDelta > 0
          ? videoLostDelta / (videoLostDelta + videoRecvDelta)
          : 0
        const audioLossRate = audioLostDelta + audioRecvDelta > 0
          ? audioLostDelta / (audioLostDelta + audioRecvDelta)
          : 0
        const jitterMs = Math.max(sample.videoJitter ?? 0, sample.audioJitter ?? 0) * 1000
        const hasPrev = prev != null
        const severe = hasPrev && (
          (videoLostDelta >= 8 && videoLossRate >= 0.02) ||
          (audioLostDelta >= 8 && audioLossRate >= 0.02) ||
          framesDroppedDelta >= 4 ||
          freezeDelta >= 1 ||
          jitterMs >= 80 ||
          (sample.rtt ?? 0) >= 0.8
        )
        q.poorWindows = severe ? q.poorWindows + 1 : Math.max(0, q.poorWindows - 1)
        let adapted = false
        if (q.poorWindows >= 2 && q.delay < rtcSmoothPlayoutDelay) {
          q.delay = rtcSmoothPlayoutDelay
          applyRtcReceiverDelay(pc, q.delay)
          adapted = true
        } else if (q.poorWindows >= 4 && q.delay < rtcMaxPlayoutDelay) {
          q.delay = rtcMaxPlayoutDelay
          applyRtcReceiverDelay(pc, q.delay)
          adapted = true
        }
        const now = Date.now()
        if (severe || adapted || now - q.lastReportAt >= rtcStatsReportMs) {
          q.lastReportAt = now
          track('webrtc_quality', {
            player: 'webrtc',
            platform: isIOS ? 'ios' : (isSafari ? 'safari' : 'other'),
            severe,
            adapted,
            delay_s: q.delay,
            poor_windows: q.poorWindows,
            video_loss_delta: videoLostDelta,
            video_loss_rate: roundMetric(videoLossRate),
            audio_loss_delta: audioLostDelta,
            audio_loss_rate: roundMetric(audioLossRate),
            frames_decoded_delta: framesDecodedDelta,
            frames_dropped_delta: framesDroppedDelta,
            freeze_delta: freezeDelta,
            jitter_ms: roundMetric(jitterMs, 1),
            rtt_ms: roundMetric((sample.rtt ?? 0) * 1000, 1),
            incoming_kbps: roundMetric((sample.incomingBitrate ?? 0) / 1000, 1),
          })
        }
        q.prev = sample
      } catch { /* 质量采样失败不影响播放 */ }
    }
    rtcStatsTimerRef.current = setInterval(sampleStats, rtcStatsIntervalMs)
    void sampleStats()
    await v.play().catch(() => {})
    playerRef.current = {
      destroy: () => {
        stopRtcStats()
        try { pc.close() } catch { /* ignore */ }
        try { v.srcObject = null } catch { /* ignore */ }
      },
    }
  }, [stopRtcStats, track])

  useEffect(() => { startWebRTCRef.current = startWebRTC }, [startWebRTC])

  // 重连闭包（用 ref 持有以便 ERROR 回调稳定调用最新版）：1.5s 退避后重试，失败则继续，
  // 直到服务端看门狗把流救活、play() 成功。wantStream=false(未连/卸载)则停止。
  useEffect(() => {
    reconnectFlvRef.current = () => {
      if (!wantStreamRef.current || reconnectingRef.current) return
      reconnectingRef.current = true
      setStatus('buffering')
      const attempt = async () => {
        if (!wantStreamRef.current) { reconnectingRef.current = false; return }
        const v = videoRef.current
        if (!v) { reconnectingRef.current = false; return }
        try { await startFlv(v); reconnectingRef.current = false; setStatus('connected') }
        catch { reconnectTimerRef.current = setTimeout(attempt, 1500) }   // 流还没回来，继续重试
      }
      reconnectTimerRef.current = setTimeout(attempt, 1500)
    }
  }, [startFlv, videoRef])

  // 卸载清理：停重连 + 销毁播放器
  useEffect(() => () => {
    wantStreamRef.current = false
    stopRtcStats()
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
    if (playerRef.current) { try { playerRef.current.destroy() } catch { /* ignore */ } playerRef.current = null }
  }, [stopRtcStats])

  // ── 断开：把直播态整体复位到「未连接」──────────────────────────────
  // 「重看开场」会卸载主舞台 <video>（videoRef.current 变 null），但 status 仍停在 'connected'
  // → 回到首页时 `g.status !== 'connected'` 的「开始」按钮不渲染，而播放器挂的是已弃的旧 DOM 节点
  // → 永久黑屏、只能刷新页面。故重看开场前必须调它，让首页重新给出「开始」按钮走正常 connect()。
  const disconnect = useCallback(() => {
    wantStreamRef.current = false
    reconnectingRef.current = false
    if (reconnectTimerRef.current) { clearTimeout(reconnectTimerRef.current); reconnectTimerRef.current = null }
    stopRtcStats()
    if (playerRef.current) { try { playerRef.current.destroy() } catch { /* ignore */ } playerRef.current = null }
    startedRef.current = false
    greetedRef.current = false      // 重新进场要再迎宾一次，否则"开场白没了"
    setStatus('idle')
    setSpeaking(false)
    setBusy(false); setThinking(false); setCaptionStreaming(false); setCaption(''); setClipUrl('')
  }, [stopRtcStats])

  // ── 连接：默认 WebRTC 低延迟；HLS 只作为 Safari/iOS 可用性兜底（用户手势内 play 允许带声）──
  const connect = useCallback(async () => {
    const v = videoRef.current
    if (!v) return
    setStatus('connecting')
    wantStreamRef.current = true
    try {
      // 优先 WebRTC（杭州网关：亚秒延迟 + 抗抖动）。iOS/Safari 也走 WebRTC，
      // 由浏览器 WebRTC A/V clock 同步音画；HLS 只在 WebRTC 不可用时兜底。
      let usedWebRTC = false
      if (!forceHls) {
        try { await startWebRTC(v); usedWebRTC = true } catch { /* 回退 FLV */ }
      }
      // 回退：iOS/macOS Safari 原生 HLS；安卓/桌面 Chrome 低延迟 FLV。
      if (!usedWebRTC) {
        if (isIOS || isSafari) {
          stopRtcStats()
          if (playerRef.current) { try { playerRef.current.destroy() } catch { /* ignore */ } playerRef.current = null }
          try { v.srcObject = null } catch { /* ignore */ }
          v.preload = 'auto'
          v.src = liveHlsUrl()
          v.load()
          await v.play().catch((err: unknown) => { if (!(err instanceof DOMException) || err.name !== 'AbortError') throw err })
          if (!v.dataset.hlsRecover) {
            v.dataset.hlsRecover = '1'
            v.addEventListener('error', () => {
              if (!wantStreamRef.current || reconnectingRef.current) return
              reconnectingRef.current = true
              setStatus('buffering')
              const retry = () => {
                if (!wantStreamRef.current) { reconnectingRef.current = false; return }
                try {
                  v.src = liveHlsUrl(); v.load()
                  v.play().then(() => { reconnectingRef.current = false; setStatus('connected') })
                           .catch(() => { reconnectTimerRef.current = setTimeout(retry, 1500) })
                } catch { reconnectTimerRef.current = setTimeout(retry, 1500) }
              }
              reconnectTimerRef.current = setTimeout(retry, 1500)
            })
          }
        } else {
          await startFlv(v)
        }
      }
      startedRef.current = true
      setStatus('connected')
      commitTrace(trace.recordConnected())
      setTimeout(greet, 1500)
    } catch (e) {
      setStatus('error')
      pushMsg({ role: 'assistant', text: '画面播放失败：' + (e instanceof Error ? e.message : String(e)) })
    }
  }, [greet, videoRef, startFlv, startWebRTC, stopRtcStats, pushMsg, commitTrace])

  // ── 提问 → 桥接 /live/ask → 数字人开口 ──────────────────────
  // barge-in（提问打断）：回答中再次提问 → 立即转答新问题。不再因 busy 拦截；用递增序号
  // 标记"最新一问"，旧问的异步结果回来时按序号丢弃（桥接侧同步会让旧问停止驱动数字人、
  // 新问首句 interrupt 冲掉旧音频），UI 只跟随最新一问。
  // opts.voice：本问来自语音转写 → 用户气泡标「语音」，舞台上「你说：…」持续可见供核对
  const ask = useCallback(async (message: string, opts?: { voice?: boolean }) => {
    const msg = message.trim()
    if (!msg) return
    const seq = ++askSeqRef.current        // 本次提问序号
    // barge-in：新问到来，把上一轮仍在 thinking 的助手气泡撤掉（其异步结果会按 seq 丢弃）
    setMessages((prev) => prev.filter((m) => !(m.role === 'assistant' && m.thinking)))
    // 对话流：先推用户气泡，再推一条 pending 助手气泡（thinking 态）
    pushMsg({ role: 'user', text: msg, voice: opts?.voice })
    const aid = pushMsg({ role: 'assistant', text: '', thinking: true })
    // 不强制先连数字人：未连接时答案以文字/缓存片返回（实时人脸是增强项，非必需）
    setBusy(true); setThinking(true); setMeta({}); setClipUrl('')   // 立即反馈=打断
    // 打断/新问立刻清空字幕 → 显「新问题 + 正在讲解…」，绝不让上一条答案残留与新问错配
    setCaption(''); setCaptionStreaming(false)
    const t0 = Date.now()

    // ── 卡拉OK式字幕：桥接逐句下发（句子已送数字人开口），前端按"说话速率"推进字符游标，
    //    让文字与数字人吐字同步流式出现（歌词跟唱）。生成完(done)后游标继续走完，不跳到结尾。──
    let full = ''                  // 已到达的完整文字（句子累积）
    let shown = 0                  // 已显示字符游标（可含小数，按速率累积）
    let lastN = -1                 // 上次 patch 的整数字数（只在变化时 patch，省渲染）
    let genDone = false            // 整段是否生成完
    let driveOn = true             // 本轮是否真开口（决定吐字速率）
    let started = false            // 揭示循环是否已启动（至少到了一句）
    let firstWordAt = 0            // 首字显示时刻（≈开口，诚实延迟口径）
    let finalText = ''; let finalMeta: Meta | undefined
    let timer: number | undefined
    const TICK = 40                // ms
    const CPS_SPEAK = 5.0          // 开口时≈中文说话速率（与 TTS 0.9 语速大致同步，略带前导=领唱感）
    const CPS_TEXT = 45            // 降级纯文字时快吐（无语音可同步）
    // 首句已生成≠iPhone 已听到：音频还要走 TTS 合成→Ditto 渲染→北京→杭州中继→WebRTC→抖动缓冲(~2s)。
    // 故字幕延后约这段时间再开吐，与语音对齐（否则字幕领先语音 ~2s）。降级纯文字无语音→不延后。
    const START_DELAY_MS = 1500

    const stop = () => { if (timer) { clearInterval(timer); timer = undefined } }
    const finalizeBubble = () => {
      setThinking(false)
      setCaptionStreaming(false)
      setCaption(finalText || full)                                       // 字幕停在完整答案（贴脸）
      patchMsg(aid, { text: finalText || full, thinking: false, meta: finalMeta })  // 聊天流落完整成句（含 meta）
      if (finalText || full) setReply(finalText || full)
    }
    const start = () => {
      if (started) return
      started = true
      // 延后到音频大致抵达再开吐（降级无语音→立即）。延后期间句子继续累积进 full。
      window.setTimeout(() => {
        if (seq !== askSeqRef.current) return                   // 延后期间被新问取代 → 放弃
        firstWordAt = Date.now()                                // 首字出现≈开口（延迟徽章口径）
        setThinking(false)
        setCaption('')                                          // 开吐前清掉上一轮字幕
        setCaptionStreaming(true)
        timer = window.setInterval(() => {
        if (seq !== askSeqRef.current) { stop(); return }       // 被新问取代 → 停
        const cps = driveOn ? CPS_SPEAK : CPS_TEXT
        shown = Math.min(full.length, shown + cps * (TICK / 1000))
        const n = Math.floor(shown)
        if (n !== lastN) {
          lastN = n
          setCaption(full.slice(0, n))                          // 舞台字幕逐字推进（卡拉OK），聊天流不动
        }
        if (genDone && n >= full.length) { stop(); finalizeBubble() }   // 走完且生成结束 → 收尾（聊天流落成句）
        }, TICK)
      }, driveOn ? START_DELAY_MS : 0)
    }

    try {
      const { ok, data } = await api.liveAskStream(
        msg, scenicRef.current, groupRef.current, backendLang(), voiceRef.current || undefined,
        {
          onOpen: (d) => { driveOn = d },
          // 首句已送去驱动数字人 = 嘴即将开口 → 乐观点亮 speaking，随后交给 now-playing 轮询维持真值。
          // 少了这一手，busy 转 false 与轮询首次返回 speaking=true 之间有最长 ~800ms 的空档，
          // 「终止播报」按钮会在那一瞬闪掉一下（实测 t=1s 复现）。
          onSentence: (text) => {
            if (seq !== askSeqRef.current) return   // 已被打断/新问取代 → 不再点亮，让抑制窗生效
            full += text
            if (driveOn) { setSpeaking(true); speakingMuteUntil.current = 0 }
            start()
          },
        },
        undefined, sitPayload(), interestsRef.current,
      )
      if (seq !== askSeqRef.current) { stop(); setMessages((prev) => prev.filter((m) => m.id !== aid)); return }  // 被新问取代 → 撤气泡
      if (!ok) {
        stop(); setThinking(false); setCaptionStreaming(false)
        const txt = '出错：' + (data.detail || '请稍后再试')
        // 也要上字幕：主屏不渲染 messages，且 caption 开头已被清空 → 只写 reply/messages 等于整条字幕栏卸载，屏幕上零提示
        setReply(txt); setCaption(txt); patchMsg(aid, { text: txt, thinking: false }); return
      }
      // 延迟口径 = 首字出现时刻（≈数字人开口），而非整段生成完——故事类长答案此前被误记成 9s+
      const timing = ((firstWordAt ? firstWordAt - t0 : Date.now() - t0) / 1000).toFixed(1)
      finalText = data.reply || full || '(无回答)'
      finalMeta = { intent: data.intent, emotion: data.emotion, timing, degraded: data.degraded, cached: data.cached }
      setMeta(finalMeta)
      // L1 命中：直接在舞台播成品视频（不依赖实时流/GPU）
      if (data.mode === 'clip' && data.clip_url) { setClipUrl(data.clip_url); stop(); finalizeBubble() }
      else if (!started) { finalizeBubble() }      // 没产出任何句子（异常）→ 直接补全
      else { genDone = true }                       // 让揭示循环按说话速率走完后再收尾显 meta
      commitTrace(trace.recordAsk())
    } catch (e) {
      stop()
      if (seq !== askSeqRef.current) { setMessages((prev) => prev.filter((m) => m.id !== aid)); return }  // 旧问出错也不打扰新问
      setThinking(false); setCaptionStreaming(false)
      const txt = '请求失败：' + (e instanceof Error ? e.message : String(e))
      setReply(txt); setCaption(txt); patchMsg(aid, { text: txt, thinking: false })
    } finally {
      if (seq === askSeqRef.current) setBusy(false)    // 仅最新一问负责解除 busy（揭示循环仍会继续走完字幕）
    }
  }, [pushMsg, patchMsg, commitTrace])

  // ── 拍照视觉定位 ────────────────────────────────────────────
  const photo = useCallback(async (file: File) => {
    if (!file || busy || !startedRef.current) return
    const seq = ++askSeqRef.current   // 与 ask() 同一把序号：识别期间被打断/被新问取代 → 结果作废，不再开口
    setBusy(true); setThinking(true); setMeta({})
    // 清字幕：否则识别等待的几秒里，舞台还挂着上一题的旧答案，看着像"拍照的回答"
    setCaption(''); setCaptionStreaming(false)
    // 「我发出去的是哪张」必须看得见：把 File 转成 object URL 挂在用户气泡上，
    // 舞台与对话记录都渲染这张缩略图。URL 存进 photoUrlsRef，卸载时统一 revoke 防泄漏。
    const imgUrl = URL.createObjectURL(file)
    photoUrlsRef.current.push(imgUrl)
    // 对话流：用户气泡（带照片本体）+ pending 助手气泡
    pushMsg({ role: 'user', text: '拍了一张照片', image: imgUrl })
    const aid = pushMsg({ role: 'assistant', text: '', thinking: true })
    const t0 = Date.now()
    try {
      const dataUrl: string = await new Promise((res, rej) => {
        const r = new FileReader(); r.onload = () => res(r.result as string); r.onerror = rej; r.readAsDataURL(file)
      })
      const b64 = dataUrl.slice(dataUrl.indexOf(',') + 1)
      const m = /data:image\/(\w+);/.exec(dataUrl)
      const fmt = m ? m[1] : 'jpeg'
      const { ok, data } = await api.chatImage(b64, fmt, scenicRef.current)
      if (seq !== askSeqRef.current) return          // 识别期间被打断/新问取代 → 丢弃，绝不再开口
      setThinking(false)
      if (!ok) {
        const txt = '出错：' + (data.detail || '识别失败')
        setReply(txt); setCaption(txt); patchMsg(aid, { text: txt, thinking: false }); return
      }
      const txt = data.reply || '(无结果)'
      const meta: Meta = { location: data.location, emotion: data.emotion, timing: ((Date.now() - t0) / 1000).toFixed(1) }
      setReply(txt); setMeta(meta)
      patchMsg(aid, { text: txt, thinking: false, meta })
      setCaption(txt); setCaptionStreaming(false)   // 拍照定位结果也上字幕（贴脸）
      const afterPhoto = trace.recordPhoto()
      commitTrace(data.location ? trace.recordVisit(data.location) : afterPhoto)
      track('photo_locate', { location: data.location || '' })
      if (data.reply) {
        api.liveSay(data.reply, scenicRef.current, data.emotion || 'neutral', voiceRef.current || undefined)
        // 嘴刚开始说（要说 20-30s），此刻 busy 转 false 会让打断按钮消失 →
        // 先乐观点亮 speaking，后续由 /live/now-playing 轮询接管真值。
        setSpeaking(true)
        speakingMuteUntil.current = 0
      }
    } catch (e) {
      if (seq !== askSeqRef.current) return
      setThinking(false)
      const txt = '识别失败：' + (e instanceof Error ? e.message : String(e))
      setReply(txt); setCaption(txt); patchMsg(aid, { text: txt, thinking: false })
    } finally { if (seq === askSeqRef.current) setBusy(false) }
  }, [busy, pushMsg, patchMsg, track, commitTrace])

  // ── 语音输入：手动停止为唯一出口（VAD 只做电平/状态显示，不再自动断句——
  //    500ms 静音阈值两头不讨好：安静时说话中途换气就被切，嘈杂时又永不触发）──
  const vad = useRef<{ stream?: MediaStream; mr?: MediaRecorder; chunks: Blob[]; ctx?: AudioContext; raf?: number; want: boolean }>({ chunks: [], want: false })
  const cleanupMic = () => { const s = vad.current.stream; if (s) { s.getTracks().forEach((t) => t.stop()); vad.current.stream = undefined } }

  const stopVoice = useCallback((transcribe: boolean) => {
    vad.current.want = transcribe
    if (vad.current.raf) { cancelAnimationFrame(vad.current.raf); vad.current.raf = undefined }
    if (vad.current.ctx) { vad.current.ctx.close().catch(() => {}); vad.current.ctx = undefined }
    const mr = vad.current.mr
    if (mr && mr.state !== 'inactive') mr.stop()
    else cleanupMic()
    setMicLevel(0)
  }, [])

  // 「说完了，发出去」——结束录音并转写的**唯一出口**（自动断句已移除，误判太多），
  // 必须转写而不是丢弃。
  const finishVoice = useCallback(() => { stopVoice(true) }, [stopVoice])
  // 「不说了」——丢弃本段录音，不转写、不提问。
  const cancelVoice = useCallback(() => { stopVoice(false); setMicState('idle') }, [stopVoice])

  const toggleVoice = useCallback(async () => {
    // 录音中再点麦克风 = 「说完了」→ 转写发送（旧实现是 stopVoice(false) 直接丢弃，
    // 用户按下停止却什么都没发生，看起来就是按钮坏了）。要丢弃请用 cancelVoice()。
    if (mic === 'listening' || mic === 'recording') { finishVoice(); return }
    if (mic === 'recognizing') return          // 识别在途，忽略（已无录音可停）
    if (!startedRef.current) return
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { noiseSuppression: true, echoCancellation: true } })
    } catch (e) {
      // 不用 alert（阻塞且丑）：走字幕，与其它失败路径一致
      const t = location.protocol === 'https:'
        ? '麦克风打不开，请在浏览器里允许本页使用麦克风'
        : '麦克风需要 HTTPS 才能使用，请用 https 地址打开本页'
      pushMsg({ role: 'assistant', text: t }); setCaption(t); setCaptionStreaming(false)
      console.warn('[mic] getUserMedia failed:', e)
      return
    }
    vad.current = { stream, chunks: [], want: false }
    const mr = new MediaRecorder(stream)
    vad.current.mr = mr
    mr.ondataavailable = (e) => { if (e.data.size) vad.current.chunks.push(e.data) }
    mr.onstop = async () => {
      cleanupMic()
      if (!vad.current.want || !vad.current.chunks.length) { setMicState('idle'); setHeard(''); return }
      setMicState('recognizing')
      try {
        const d = await api.asr(new Blob(vad.current.chunks, { type: 'audio/webm' }), scenicRef.current, backendLang())
        setMicState('idle')
        const text = d.text?.trim()
        // 失败也要上字幕：主屏不渲染 messages，只写 pushMsg 等于屏幕上零反馈（用户会以为按钮坏了）
        if (text) { setHeard(text); ask(text, { voice: true }) }
        else { setHeard(''); const t = '没听清，请再说一次'; pushMsg({ role: 'assistant', text: t }); setCaption(t); setCaptionStreaming(false) }
      } catch (e) {
        setMicState('idle'); setHeard('')
        const t = '识别失败：' + (e instanceof Error ? e.message : e)
        pushMsg({ role: 'assistant', text: t }); setCaption(t); setCaptionStreaming(false)
      }
    }
    mr.start()
    setMicState('listening')
    setHeard('')
    setMicMs(0)
    micStartRef.current = performance.now()

    const ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)()
    vad.current.ctx = ctx
    const src = ctx.createMediaStreamSource(stream)
    const an = ctx.createAnalyser(); an.fftSize = 512; src.connect(an)
    const buf = new Uint8Array(an.fftSize)
    // 不再自动断句：录音只由「说完了/取消」结束；MAX_MS 仅作忘停的安全上限
    const VOICE_TH = 0.018, MAX_MS = 30000
    let spoke = false
    let lastPub = 0                       // 电平/计时上报节流
    const t0 = performance.now()
    const loop = () => {
      an.getByteTimeDomainData(buf)
      let sum = 0
      for (let i = 0; i < buf.length; i++) { const v = (buf[i] - 128) / 128; sum += v * v }
      const rms = Math.sqrt(sum / buf.length), now = performance.now()
      // 把能量与已录时长喂给 UI：录音条的电平柱 + 计时器 = 用户能看见「它真的在听我说」。
      // rms 说话约 0.02~0.15 → ×6 归一到 0~1 再钳制；节流到 ~12fps 避免每帧 setState。
      if (now - lastPub > 80) {
        lastPub = now
        setMicLevel(Math.max(0, Math.min(1, rms * 6)))
        setMicMs(now - t0)
      }
      if (rms > VOICE_TH && !spoke) { spoke = true; setMicState('recording') }
      // 安全上限：说过话就转写（别浪费用户已说的），没说过话就当没录（避免把环境噪音送去识别）
      if (now - t0 > MAX_MS) { stopVoice(spoke); return }
      vad.current.raf = requestAnimationFrame(loop)
    }
    vad.current.raf = requestAnimationFrame(loop)
  }, [mic, ask, stopVoice, finishVoice, pushMsg])

  const recordVisit = useCallback((name: string) => commitTrace(trace.recordVisit(name)), [commitTrace])
  const recordRouteDone = useCallback((id: string) => commitTrace(trace.recordRouteDone(id)), [commitTrace])
  const recordRating = useCallback((score: number) => commitTrace(trace.recordRating(score)), [commitTrace])

  // ── 打断（barge-in）：立即停当前讲解，语音逐渐减弱，不影响下一条输入 ──────────────
  // ①++askSeqRef 让在跑的揭示循环/旧问异步结果作废 ②清 busy/thinking/字幕态（UI 立刻空出）
  // ③音量 ~400ms 淡到 0（"逐渐减弱"）后恢复到 1（下一条回答仍可听见）④POST /live/interrupt 硬清引擎。
  const interrupt = useCallback(() => {
    askSeqRef.current += 1
    setBusy(false); setThinking(false); setCaptionStreaming(false); setCaption(''); setClipUrl('')
    setSpeaking(false)          // 乐观：按钮立刻消失，不等下一次轮询（后端也会同刻清 now-playing）
    speakingMuteUntil.current = Date.now() + 2500   // 抑制窗：别让在途的旧轮询把按钮又点亮
    rampVolume(0, 400)
    window.setTimeout(() => rampVolume(1, 300), 480)   // 恢复音量，保证下一条输入的语音可听见
    api.interrupt(api.SESSION_ID, 'main')
  }, [rampVolume])

  // 「还在说吗」轮询：只在连接后跑，~800ms 一次。停说后自然转 false，打断/新问时由抑制窗压住在途响应。
  useEffect(() => {
    if (status !== 'connected') { setSpeaking(false); return }
    let alive = true
    let timer: number | undefined
    const tick = async () => {
      const { speaking: sp } = await api.nowPlaying(api.SESSION_ID, 'main')
      if (!alive) return
      if (Date.now() >= speakingMuteUntil.current) setSpeaking(sp)
      timer = window.setTimeout(tick, 800)
    }
    timer = window.setTimeout(tick, 800)
    return () => { alive = false; if (timer) clearTimeout(timer) }
  }, [status])

  // ── 告别（step 11）：结束导览的温暖收尾 = 个性化告别语 + 数字人开口道别 + 随后弹出电子明信片 ──
  // 明信片的弹出由 App 承接（hook 不持有抽屉状态）。此处只负责说出告别 + 上字幕 + 落聊天流。
  const farewell = useCallback(() => {
    askSeqRef.current += 1                              // 打断当前讲解，让位给告别
    setBusy(false); setThinking(false); setCaptionStreaming(false)
    const t = makeT(langRef.current)
    const sName = SCENICS.find((s) => s.id === scenicRef.current)?.name || scenicRef.current
    const text = t('farewell', { guide: guideNameRef.current, scenic: sName })
    const m: Meta = { emotion: 'happy' }
    setReply(text); setMeta(m); setCaption(text)
    pushMsg({ role: 'assistant', text, meta: m })
    api.liveSay(text, scenicRef.current, 'happy', voiceRef.current || undefined)
  }, [pushMsg])

  // ── 扫码接力：把另一设备的快照注水到本机（画像 + 历史对话）──────────────
  // 个性化(景区/同行人/兴趣/语言/音色/形象)直接套用 → localStorage 持久化由现有 effect 负责；
  // 历史对话注入聊天流，最后一条助手语上字幕(贴脸)，让"接着上一句继续"自然成立。
  const importHandoff = useCallback((snap: api.HandoffSnapshot): number => {
    if (snap.scenic_id) setScenic(snap.scenic_id)
    if (snap.group_type) setGroupType(snap.group_type)
    if (Array.isArray(snap.interests)) setInterests(snap.interests)
    if (snap.lang) setLang(snap.lang as Lang)
    if (snap.voice_id) setVoiceId(snap.voice_id)
    if (snap.avatar_id) setAvatarPref(snap.avatar_id)
    // 自身情况标签（Phase C 起随快照带走；老快照无此字段 → 跳过保留本机默认）
    if (snap.age) setAge(snap.age)
    if (snap.pace) setPace(snap.pace)
    if (snap.mobility) setMobility(snap.mobility)
    if (snap.purpose) setPurpose(snap.purpose)
    if (snap.first_time) setFirstTime(snap.first_time)
    const imported: Msg[] = (snap.messages || [])
      .filter((m) => (m.text || '').trim())
      .map((m) => ({
        id: newId(),
        role: m.role === 'user' ? 'user' : 'assistant',
        text: m.text,
        meta: (m.emotion || m.intent)
          ? { emotion: m.emotion || undefined, intent: m.intent || undefined }
          : undefined,
      }))
    if (imported.length) {
      setMessages(imported)
      const lastA = [...imported].reverse().find((m) => m.role === 'assistant')
      if (lastA) { setReply(lastA.text); setMeta(lastA.meta || {}); setCaption(lastA.text); setCaptionStreaming(false) }
    }
    return imported.length
  }, [setVoiceId, setAvatarPref])

  // ── 主动开讲（地理围栏）：开关开 + 已连接 → 持续定位，进入景点 50m 自动开讲 ──────────
  //    带迟滞(离开 80m 重新武装)+冷却(5min)防反复；关闭/断连/卸载即停。定位失败静默，手动定位仍可用。
  useEffect(() => {
    if (!autoNarrate || status !== 'connected') return
    const fence = makeGeofence(scenic, { radius: 50 })
    const w = watchPositionGCJ02(
      (fix) => {
        const hit = fence.feed(fix.lng, fix.lat, Date.now())
        if (hit) {
          setGeoArrival(hit.name)
          commitTrace(trace.recordVisit(hit.name))
          track('geo_arrival', { name: hit.name, distance: hit.distance })
          ask(`请讲讲${hit.name}的故事`)   // 数字人主动开讲（复用问答链路，情境/同行人照常带）
        }
      },
      () => { /* 定位失败静默：不打扰，手动定位仍可用 */ },
    )
    return () => w.stop()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoNarrate, status, scenic])
  // 到达提示条自动收起
  useEffect(() => {
    if (!geoArrival) return
    const id = setTimeout(() => setGeoArrival(''), 6000)
    return () => clearTimeout(id)
  }, [geoArrival])

  return {
    scenic, setScenic, groupType, setGroupType, interests, setInterests, lang, setLang, guideName,
    age, setAge, pace, setPace, mobility, setMobility, purpose, setPurpose, firstTime, setFirstTime,
    voiceId, setVoiceId, avatarPref, setAvatarPref,
    autoNarrate, setAutoNarrate, geoArrival, clearGeoArrival: () => setGeoArrival(''),
    status, setStatus, thinking, busy, reply, meta, messages, mic,
    micLevel, micMs, heard, clearHeard: () => setHeard(''),
    trace: traceState, recordVisit, recordRouteDone, recordRating, track,
    clipUrl, clearClip: () => setClipUrl(''),
    caption, captionStreaming, speaking,
    recos, recoBasis, recosLoading, loadRecos,
    connect, disconnect, ask, toggleVoice, finishVoice, cancelVoice, photo, isIOS,
    importHandoff,
    interrupt, farewell, rampVolume, resetTrace,
    celebration: celebrations[0] ?? null, dismissCelebration,
  }
}
