// 与桥接(:9000)同源的端点封装。契约对照 talk_mobile.html（即行为规格）。
// 全部相对路径：dev 经 vite proxy、生产经桥接反代，单源无 mixed-content。
import type { Situation } from '@/lib/i18n'

export const SESSION_ID = '0' // RTMP 单路固定 sessionid（LiveTalking WebRTC 通道，多路共享）

// RAG 业务会话 id：per-tab 稳定 id，用于历史/分析/游中画像。复用 track.ts 的 lingjing.sid
// （同 key → 与埋点 events 的 session_id 对齐，画像可 join 轨迹）。sessionStorage 失败 → s_anon
// （被后端 profiler 的 _SKIP_SESSIONS 忽略，不建串人的画像）。
export function bizSessionId(): string {
  try {
    let id = sessionStorage.getItem('lingjing.sid')
    if (!id) {
      id = 's_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36)
      sessionStorage.setItem('lingjing.sid', id)
    }
    return id
  } catch {
    return 's_anon'
  }
}

// 自身情况标签：仅非默认值才有意义注入后端（全默认 = 不传 → 后端缓存键与 prompt 与现状一致）。
// undefined 时不进 body，避免给存量链路引入 situation 字段。
type Sit = Partial<Situation> | undefined

export interface GreetResp { text?: string; emotion?: string }
export interface AskResp { reply?: string; intent?: string; emotion?: string; detail?: string; mode?: string; degraded?: boolean; clip_url?: string; cached?: boolean }
export interface ImageResp { reply?: string; location?: string; emotion?: string; detail?: string }

export async function greeting(scenic: string, groupType = 'adult', sit?: Sit): Promise<GreetResp> {
  const q = new URLSearchParams({ scenic_id: scenic, group_type: groupType })
  // 仅非默认情境维度入参（迎宾口吻按年龄/目的/初访微调；缺省=原迎宾词）
  if (sit?.age) q.set('age', sit.age)
  if (sit?.purpose) q.set('purpose', sit.purpose)
  if (sit?.first_time) q.set('first_time', sit.first_time)
  const r = await fetch(`/rag/trip/greeting?${q.toString()}`)
  return r.json()
}

// 预渲染「含手势」欢迎片清单（仿 L1 FAQ）：连接时若该景区×同行人有片，先播含手势+自带语音的成片，
// 播完回归实时问答（实时 Ditto 出不了手，故手势走离线预渲染片）。空清单/无命中 → 回退实时迎宾。
export interface GreetingClip { clip: string; text?: string; emotion?: string }
export async function greetingClip(scenic: string, groupType: string): Promise<GreetingClip | null> {
  try {
    const r = await fetch('/greeting/manifest.json', { cache: 'no-cache' })
    if (!r.ok) return null
    const m = await r.json()
    const byScenic = m?.scenics?.[scenic]
    const c: GreetingClip | undefined = byScenic?.[groupType] || byScenic?.adult   // 同行人缺则回落 adult
    return c?.clip ? c : null
  } catch { return null }
}

export interface TodayResp { weather?: string; period?: string; crowd?: string; tip?: string }
export async function today(scenic: string): Promise<TodayResp> {
  const r = await fetch(`/rag/trip/today?scenic_id=${scenic}`)
  if (!r.ok) return {}
  return r.json()
}

// POI 级实时客流（后端 /analytics/crowd?scenic_id=lingshan 返回 granularity:poi）
export interface LiveCrowdPoi {
  poi_id: string
  name: string
  crowd_level: string          // 空闲 / 适中 / 较多 / 繁忙
  crowd_index: number
  trend: '上升' | '平稳' | '下降'
  indoor: boolean
  next_show: string | null     // "15:00"
  minutes_to_show: number | null
  in_show: boolean
  hint: string
}
export interface LiveCrowdResp {
  scenic_id: string
  granularity: string          // poi | attraction
  as_of: string
  has_data: boolean
  next_show?: { poi: string; at: string; minutes: number } | null
  attractions: LiveCrowdPoi[]
}
// 拉某景区实时客流；失败/无数据返回 null（调用方回落静态档位）。
export async function crowdLive(scenic: string): Promise<LiveCrowdResp | null> {
  try {
    const r = await fetch(`/rag/analytics/crowd?scenic_id=${encodeURIComponent(scenic)}`)
    if (!r.ok) return null
    const d = await r.json()
    return d?.has_data ? d : null
  } catch { return null }
}

export interface Station { name: string; hint: string }
export interface Route { id: string; title: string; duration: string; tag: string; group: string; stations: Station[] }
export async function routes(scenic: string): Promise<Route[]> {
  const r = await fetch(`/rag/tour/routes?scenic_id=${scenic}`)
  if (!r.ok) return []
  return (await r.json()).routes || []
}

export interface FacilityGroup { id: string; label: string; emoji: string; points: string[] }
export async function facilities(scenic: string): Promise<FacilityGroup[]> {
  const r = await fetch(`/rag/tour/facilities?scenic_id=${scenic}`)
  if (!r.ok) return []
  return (await r.json()).groups || []
}

export interface ScenicTheme { scenic_id: string; name: string; primary: string; sweet: string; guide_name: string; scenic_type?: string; type_label?: string }

// —— 数字人形象管理（管理端配默认，游客端精调）——
export interface AvatarPreset {
  id: string; name: string; gender: 'female' | 'male'; style: string
  persona?: string; outfit?: string; age?: string; fit?: string
  scenic?: string   // 该形象专属绑定的景区（身份库 dh_<scenic> 才有），用于「本景区专属」浮顶
  stage_name?: string   // 艺名（文艺平实，游客端展示）
  welcome_text?: string // 欢迎语（换形象后播报）
  published?: boolean   // 仅 admin 视角返回
  preview?: string; recommended?: boolean; coming_soon?: boolean; legacy?: boolean
}
export interface VoicePreset { id: string; name: string; gender: 'female' | 'male'; tone: string }
export interface BackgroundPreset { id: string; name: string; scenic?: string | null; preview?: string | null; source?: string; status?: string }

function normalizePreviewUrl(url?: string | null): string | null | undefined {
  if (!url) return url
  const ragMarker = '/rag/digital-human/avatar-preview/'
  const previewMarker = '/digital-human/avatar-preview/'
  if (url.includes(ragMarker)) return ragMarker + url.split(ragMarker, 2)[1]
  if (url.includes(previewMarker)) return '/rag' + previewMarker + url.split(previewMarker, 2)[1]
  if (url.startsWith('http')) {
    try {
      const u = new URL(url)
      if (u.pathname.startsWith('/avatars/') || u.pathname.startsWith('/avatar_backgrounds/') || u.pathname.startsWith('/rag/')) {
        return `${u.pathname}${u.search}`
      }
    } catch {
      return url
    }
  }
  return url
}

export async function dhPresets(scenic?: string, audience: 'visitor' | 'admin' = 'visitor'): Promise<{ avatars: AvatarPreset[]; voices: VoicePreset[]; backgrounds?: BackgroundPreset[] }> {
  // 游客端默认按景区过滤（生产者/消费者分离）：灵山模式只见与灵山有关的已发布形象
  const qs = scenic ? `?scenic_id=${encodeURIComponent(scenic)}&audience=${audience}` : ''
  const r = await fetch(`/rag/digital-human/presets${qs}`)
  if (!r.ok) return { avatars: [], voices: [] }
  const data = await r.json()
  return {
    avatars: (data.avatars ?? []).map((a: AvatarPreset) => ({ ...a, preview: normalizePreviewUrl(a.preview) ?? undefined })),
    voices: data.voices ?? [],
    backgrounds: (data.backgrounds ?? []).map((b: BackgroundPreset) => ({ ...b, preview: normalizePreviewUrl(b.preview) ?? null })),
  }
}
export interface DhConfig {
  scenic_id: string; avatar_id: string; avatar_name: string; voice_id: string; voice_name: string
  background_id?: string; background_name?: string; stage_name?: string
}
export async function dhConfig(scenic: string): Promise<DhConfig | null> {
  const r = await fetch(`/rag/digital-human/config?scenic_id=${scenic}`)
  if (!r.ok) return null
  return r.json()
}
export async function getTheme(scenic: string): Promise<ScenicTheme> {
  const r = await fetch(`/rag/scenic/theme?scenic_id=${scenic}`)
  return r.json()
}

export interface NearbyItem { name: string; distance: number }
export interface SimSpot { label: string; lat: number; lng: number }
export interface NearbyResp { nearest: NearbyItem | null; items: NearbyItem[]; sim_spots: SimSpot[] }
export async function nearby(scenic: string, lat?: number, lng?: number): Promise<NearbyResp> {
  const q = lat != null && lng != null ? `&lat=${lat}&lng=${lng}` : ''
  const r = await fetch(`/rag/tour/nearby?scenic_id=${scenic}${q}`)
  if (!r.ok) return { nearest: null, items: [], sim_spots: [] }
  return r.json()
}

// 立即打断数字人：停当前播报、清队列、硬清引擎残句（后端 POST /live/interrupt）。
// fire-and-forget：失败静默（打断是尽力而为，前端已先做 UI/音量处理）。返回后端是否清掉了内容。
export async function interrupt(sessionid: string = SESSION_ID, screen: 'main' | 'portrait' = 'main'): Promise<{ ok: boolean; dropped?: number }> {
  try {
    const r = await fetch('/live/interrupt', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionid, screen }),
    })
    const d = await r.json().catch(() => ({}))
    return { ok: Boolean(d?.ok), dropped: d?.dropped }
  } catch { return { ok: false } }
}

// 数字人此刻是否真的还在说话（桥接内存查表，零下游调用，~800ms 轮询友好）。
// 前端字幕按 5.0 字/秒推进、桥接按 4.5 字/秒喂句，故字幕总比嘴先收尾几秒——「还在说」只能问后端。
// 失败静默返回 false：宁可少显示打断按钮，也不要因为一次网络抖动就卡住 UI。
export async function nowPlaying(
  sessionid: string = SESSION_ID, screen: 'main' | 'portrait' = 'main',
): Promise<{ speaking: boolean; text: string }> {
  try {
    const r = await fetch(`/live/now-playing?screen=${screen}&sessionid=${encodeURIComponent(sessionid)}`)
    const d = await r.json().catch(() => ({}))
    return { speaking: Boolean(d?.speaking), text: String(d?.text || '') }
  } catch { return { speaking: false, text: '' } }
}

export function liveSay(text: string, scenic: string, emotion = 'happy', voiceId?: string) {
  return fetch('/live/say', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sessionid: SESSION_ID, text, scenic_id: scenic, emotion,
      ...(voiceId ? { voice_id: voiceId } : {}),
    }),
  }).catch(() => {})
}

export async function liveAsk(
  message: string, scenic: string, groupType = 'adult', lang = 'auto', voiceId?: string, situation?: Sit,
  interests?: string[],
): Promise<{ ok: boolean; data: AskResp }> {
  const r = await fetch('/live/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sessionid: SESSION_ID, session_id: bizSessionId(), message, scenic_id: scenic, group_type: groupType, lang,
      ...(voiceId ? { voice_id: voiceId } : {}),
      ...(situation ? { situation } : {}),
      ...(interests && interests.length ? { interests } : {}),
    }),
  })
  return { ok: r.ok, data: await r.json() }
}

// SSE 字幕流版：桥接每把一句送数字人开口就下发该句，前端据此按说话速率逐字吐字（与语音同步）。
// 回调：onOpen(本轮是否真开口) / onSentence(逐句到达) / onDone(完整结果，含 meta)。
// 返回 ok=false 时 data.detail 含错误信息。AskResp 同 liveAsk。
export interface AskStreamHandlers {
  onOpen?: (driveEnabled: boolean) => void
  onSentence?: (text: string, index: number, emotion?: string) => void
}
export async function liveAskStream(
  message: string, scenic: string, groupType = 'adult', lang = 'auto', voiceId: string | undefined,
  h: AskStreamHandlers, signal?: AbortSignal, situation?: Sit, interests?: string[],
): Promise<{ ok: boolean; data: AskResp }> {
  const r = await fetch('/live/ask_stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      sessionid: SESSION_ID, session_id: bizSessionId(), message, scenic_id: scenic, group_type: groupType, lang,
      ...(voiceId ? { voice_id: voiceId } : {}),
      ...(situation ? { situation } : {}),
      ...(interests && interests.length ? { interests } : {}),
    }),
    signal,
  })
  if (!r.ok || !r.body) return { ok: false, data: { detail: `HTTP ${r.status}` } }
  const reader = r.body.getReader()
  const dec = new TextDecoder()
  let buf = ''
  let done: AskResp | null = null
  let err: AskResp | null = null
  for (;;) {
    const { value, done: streamDone } = await reader.read()
    if (streamDone) break
    buf += dec.decode(value, { stream: true })
    // 按行切分；每个 data: 行是一个 JSON 事件
    let nl: number
    while ((nl = buf.indexOf('\n')) >= 0) {
      const line = buf.slice(0, nl).trim()
      buf = buf.slice(nl + 1)
      if (!line.startsWith('data:')) continue
      let evt: Record<string, unknown>
      try { evt = JSON.parse(line.slice(5).trim()) } catch { continue }
      const type = evt.type as string
      if (type === 'open') h.onOpen?.(!!evt.drive_enabled)
      else if (type === 'sentence') h.onSentence?.(String(evt.text ?? ''), Number(evt.index ?? 0), evt.emotion as string | undefined)
      else if (type === 'done') done = evt as AskResp
      else if (type === 'error') err = { detail: String(evt.detail ?? '请求失败') }
    }
  }
  if (err) return { ok: false, data: err }
  return { ok: !!done, data: done ?? { detail: '流式中断' } }
}

// AI 定制形象：万相「人景一体」在线生成 → 落 ditto_avatars 双比例 → 即时入库可热切（~30s）。
// 返回新形象 preset（ready:true），前端直接加入形象库并可热切上身。见 API_DOC 4.9。
export interface GenAvatarReq { prompt?: string; scenic_id: string; gender?: 'female' | 'male'; style?: string; name?: string }
export async function generateAvatar(req: GenAvatarReq): Promise<{ ok: boolean; avatar?: AvatarPreset; detail?: string }> {
  try {
    const r = await fetch('/rag/digital-human/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ gender: 'female', style: '现代', ...req }),
    })
    const d = await r.json().catch(() => ({}))
    if (!r.ok) return { ok: false, detail: d?.detail || `HTTP ${r.status}` }
    const avatar = d?.avatar ? { ...d.avatar, preview: normalizePreviewUrl(d.avatar.preview) ?? undefined } : undefined
    return { ok: Boolean(d?.ok), avatar }
  } catch (e) { return { ok: false, detail: String(e) } }
}

// 热拔插换形象：把正在直播的数字人当场换成 avatarId（~1s，不重连）。见 API_DOC 4.7。
export async function liveSetAvatar(avatarId: string, scenic: string): Promise<{ ok: boolean }> {
  try {
    const r = await fetch('/live/avatar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ avatar_id: avatarId, scenic_id: scenic, sessionid: SESSION_ID, screen: 'main' }),
    })
    const d = await r.json().catch(() => ({}))
    return { ok: Boolean(d?.ok) }
  } catch { return { ok: false } }
}

export async function asr(blob: Blob, scenic: string, lang = 'auto'): Promise<{ text?: string }> {
  const fd = new FormData()
  fd.append('file', blob, 'voice.webm')
  fd.append('scenic_id', scenic)
  fd.append('language', lang)   // 跟随 UI 语言：en→识别英文、zh→中文+景区热词、auto→自动检测
  const r = await fetch('/rag/asr', { method: 'POST', body: fd })
  return r.json()
}

export async function chatImage(b64: string, fmt: string, scenic: string): Promise<{ ok: boolean; data: ImageResp }> {
  const r = await fetch('/rag/chat/image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: 'talk', scenic_id: scenic, image_b64: b64, image_format: fmt,
      question: '我面前是什么？帮我定位、讲解，并指引我接下来去哪。',
    }),
  })
  return { ok: r.ok, data: await r.json() }
}

// 拍照打卡核验：闭集 VL + 位置软门 + 融合决策（后端 /checkin）
export interface CheckinCand { id: string; name: string; lng?: number; lat?: number }
export interface CheckinResult {
  decision: 'confirmed' | 'wrong_stop' | 'uncertain'
  matched_id?: string | null
  matched_name?: string | null
  confidence: number
  evidence: string[]
  distance_m?: number | null
  reason: string
  alt_id?: string | null
}
export async function checkin(body: {
  scenic: string; b64: string; fmt: string; targetId: string; candidates: CheckinCand[]; gps?: [number, number] | null
}): Promise<{ ok: boolean; data: CheckinResult }> {
  const r = await fetch('/rag/checkin', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      scenic_id: body.scenic, image_b64: body.b64, image_format: body.fmt,
      target_id: body.targetId, candidates: body.candidates, gps: body.gps ?? null,
    }),
  })
  return { ok: r.ok, data: await r.json() }
}

// 个性化推荐「为你定制」（后端 /recommend）：画像×兴趣×此刻 → 带依据的推荐卡
export interface RecoCard {
  icon: string
  title: string
  reason: string
  basis: string[]
  action: 'ask' | 'route' | 'facility'
  query?: string | null
}
export async function recommend(body: {
  scenic: string; groupType: string; interests: string[]; lang?: string; situation?: Sit
}): Promise<{ cards: RecoCard[]; basis: string[] }> {
  try {
    const r = await fetch('/rag/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenic_id: body.scenic, group_type: body.groupType, interests: body.interests, lang: body.lang || 'zh',
        session_id: bizSessionId(),
        ...(body.situation ? { situation: body.situation } : {}),
      }),
    })
    if (!r.ok) return { cards: [], basis: [] }
    return await r.json()
  } catch { return { cards: [], basis: [] } }
}

// —— 扫码接力 / 同游（后端 /handoff）——
// 把本机「对话 + 个性化画像」打成短时快照(token)，另一台设备扫码即接着逛：
// 大屏→手机（带走导览）、手机→手机（家人同游）双向通用。见 API_DOC「扫码接力」节。
export interface HandoffMsg { role: 'user' | 'assistant'; text: string; emotion?: string | null; intent?: string | null }
export interface HandoffSnapshot {
  scenic_id: string; group_type: string; lang: string; interests: string[]
  avatar_id?: string | null; voice_id?: string | null
  // 自身情况标签（Phase C 起随快照带走；老快照无此字段 → 注水时跳过）
  age?: string | null; pace?: string | null; mobility?: string | null; purpose?: string | null; first_time?: string | null
  messages: HandoffMsg[]; trace?: unknown; poi?: string | null; source?: string
}
export async function createHandoff(body: {
  scenic: string; groupType: string; lang: string; interests: string[]
  voiceId?: string; avatarPref?: string; messages: HandoffMsg[]; trace?: unknown; source?: string; situation?: Sit
}): Promise<{ ok: boolean; token?: string; expiresIn?: number; msgCount?: number }> {
  try {
    const r = await fetch('/rag/handoff/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenic_id: body.scenic, group_type: body.groupType, lang: body.lang, interests: body.interests,
        voice_id: body.voiceId || null, avatar_id: body.avatarPref || null,
        messages: body.messages, trace: body.trace ?? null, source: body.source || 'phone',
        ...(body.situation ? { situation: body.situation } : {}),
      }),
    })
    const d = await r.json().catch(() => ({}))
    return { ok: Boolean(d?.ok), token: d?.token, expiresIn: d?.expires_in, msgCount: d?.msg_count }
  } catch { return { ok: false } }
}
export async function claimHandoff(token: string): Promise<{ ok: boolean; reason?: string; snapshot?: HandoffSnapshot }> {
  try {
    const r = await fetch('/rag/handoff/claim', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, session_id: bizSessionId() }),
    })
    const d = await r.json().catch(() => ({}))
    if (!d?.ok) return { ok: false, reason: d?.reason || (r.status === 410 ? 'expired' : 'failed') }
    // 后端把快照字段平铺在响应里（{ ok, scenic_id, ... }），剥掉 ok 即快照
    const { ok: _ok, ...snap } = d
    return { ok: true, snapshot: snap as HandoffSnapshot }
  } catch { return { ok: false, reason: 'network' } }
}
// 二维码图片 URL：用本机 origin 拼完整 claim_url 交给后端渲染 → 跨公网网关/局域网都扫得通。
export function handoffQrUrl(token: string): string {
  const claim = `${location.origin}/?h=${encodeURIComponent(token)}`
  return `/rag/handoff/qr.png?data=${encodeURIComponent(claim)}`
}
