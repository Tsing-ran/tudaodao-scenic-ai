/**
 * 云端后端 API 封装
 * Base URL: http://116.62.136.211:8000（通过 vite proxy /cloud 转发）
 */

// 直连桥接公网 /rag（CORS 全开，与服务来源无关：:8443/admin 下、:6008 下、dev 下都通）
const CLOUD_BASE = '/cloud'

/**
 * 流式对话（SSE）
 * 收到 emotion 事件 → 更新数字人表情
 * 收到 sentence 事件 → 送 DVH 驱动数字人说话
 * 收到 end 事件 → 结束
 *
 * @param {Object} params
 * @param {string} params.message      用户问题
 * @param {string} params.scenicId     景区ID（lingshan / nihuawan / xihu...）
 * @param {string} params.sessionId    会话ID
 * @param {Array}  params.history      历史对话 [{role, content}]
 * @param {Function} params.onEmotion  (emotion: string) => void
 * @param {Function} params.onSentence (text: string, index: number) => void
 * @param {Function} params.onEnd      (fullText: string) => void
 */
export async function chatStream({ message, scenicId, sessionId, history = [], onEmotion, onSentence, onEnd }) {
  const response = await fetch(`${CLOUD_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      scenic_id: scenicId,
      session_id: sessionId,
      history,
      stream: true,
    }),
  })

  if (!response.ok) {
    throw new Error(`云端接口错误: ${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()

    let currentEvent = ''
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          if (currentEvent === 'emotion' && onEmotion)   onEmotion(data.value)
          if (currentEvent === 'sentence' && onSentence) onSentence(data.text, data.index)
          if (currentEvent === 'end' && onEnd)           onEnd(data.full_text)
        } catch {}
        currentEvent = ''
      }
    }
  }
}

/**
 * 同步对话（调试用）
 */
export async function chatSync({ message, scenicId, sessionId, history = [] }) {
  const res = await fetch(`${CLOUD_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, scenic_id: scenicId, session_id: sessionId, history }),
  })
  return res.json()
}

/**
 * 图片对话（多模态）
 * @param {File} file        图片文件
 * @param {string} question  问题
 * @param {string} scenicId  景区ID
 */
export async function chatImage({ file, question, scenicId, sessionId }) {
  const base64 = await new Promise(resolve => {
    const reader = new FileReader()
    reader.onload = e => resolve(e.target.result.split(',')[1])
    reader.readAsDataURL(file)
  })
  const res = await fetch(`${CLOUD_BASE}/chat/image`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_b64: base64,
      image_format: file.type.includes('png') ? 'png' : 'jpeg',
      question: question || '请介绍一下图片里的内容',
      scenic_id: scenicId,
      session_id: sessionId,
    }),
  })
  return res.json()
}

/**
 * 数据大屏
 */
export async function getDashboard(scenicId = 'lingshan', days = 7) {
  const res = await fetch(`${CLOUD_BASE}/analytics/dashboard?scenic_id=${scenicId}&days=${days}`)
  return res.json()
}

/**
 * 热门话题
 */
export async function getHotTopics(scenicId = 'lingshan', days = 7, limit = 10) {
  const res = await fetch(`${CLOUD_BASE}/analytics/hot-topics?scenic_id=${scenicId}&days=${days}&limit=${limit}`)
  return res.json()
}

/**
 * 满意度趋势
 */
export async function getSentimentTrend(scenicId = 'lingshan', days = 30) {
  const res = await fetch(`${CLOUD_BASE}/analytics/sentiment-trend?scenic_id=${scenicId}&days=${days}`)
  return res.json()
}

/**
 * 知识库状态
 */
export async function getKbList() {
  const res = await fetch(`${CLOUD_BASE}/kb/list`)
  return res.json()
}

/**
 * 话题意图分类（比词云更准确）
 */
export async function getTopicIntents(scenicId = 'lingshan', days = 30, limit = 8) {
  const res = await fetch(`${CLOUD_BASE}/analytics/topic-intents?scenic_id=${scenicId}&days=${days}&limit=${limit}`)
  return res.json()
}

/**
 * 客群画像
 */
export async function getProfile(scenicId = 'lingshan', days = 7) {
  const res = await fetch(`${CLOUD_BASE}/analytics/profile?scenic_id=${scenicId}&days=${days}`)
  return res.json()
}

/**
 * 功能使用率
 */
export async function getFeatureUsage(scenicId = 'lingshan', days = 7) {
  const res = await fetch(`${CLOUD_BASE}/analytics/feature-usage?scenic_id=${scenicId}&days=${days}`)
  return res.json()
}

/**
 * 游客行为事件上报
 */
export async function reportEvent(payload) {
  await fetch(`${CLOUD_BASE}/analytics/event`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  }).catch(() => {})
}

/**
 * 数字人形象/音色/背景列表
 * @param {string} [scenicId]  传景区 id 时按景区过滤/标注
 * @param {string} [audience]  'admin'(默认,全量+published) | 'visitor'(仅已发布)
 */
export async function getDigitalHumanPresets(scenicId, audience) {
  const q = scenicId ? `?scenic_id=${scenicId}&audience=${audience || 'admin'}` : ''
  const res = await fetch(`${CLOUD_BASE}/digital-human/presets${q}`)
  return res.json()
}

/** 形象艺名/欢迎语/该景区发布状态列表 */
export async function getAvatarMeta(scenicId = 'lingshan') {
  const res = await fetch(`${CLOUD_BASE}/digital-human/avatar-meta?scenic_id=${scenicId}`)
  return res.json()
}

/** 更新形象艺名/欢迎语（全局，部分更新） */
export async function putAvatarMeta(payload) {
  const res = await fetch(`${CLOUD_BASE}/digital-human/avatar-meta`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })
  return res.json()
}

/** 设置形象在某景区的发布/排序/艺名覆盖（UPSERT） */
export async function putAvatarPublish(payload) {
  const res = await fetch(`${CLOUD_BASE}/digital-human/avatar-publish`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })
  return res.json()
}

/**
 * 获取景区数字人配置
 */
export async function getDigitalHumanConfig(scenicId = 'lingshan') {
  const res = await fetch(`${CLOUD_BASE}/digital-human/config?scenic_id=${scenicId}`)
  return res.json()
}

/**
 * 保存景区数字人配置
 */
export async function saveDigitalHumanConfig(payload) {
  const res = await fetch(`${CLOUD_BASE}/digital-human/config`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return res.json()
}

/**
 * 获取景区主题色
 */
export async function getScenicTheme(scenicId = 'lingshan') {
  const res = await fetch(`${CLOUD_BASE}/scenic/theme?scenic_id=${scenicId}`)
  return res.json()
}

/**
 * 获取全部景区主题
 */
export async function getScenicThemes() {
  const res = await fetch(`${CLOUD_BASE}/scenic/themes`)
  return res.json()
}

/**
 * 更新景区主题色
 */
export async function updateScenicTheme(payload) {
  const res = await fetch(`${CLOUD_BASE}/scenic/theme`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return res.json()
}

// ── 桥接（数字人直播 / 热拔插）直连公网：CORS 全开，dev/prod 通用，无需后端代理 ──
const BRIDGE = ''
// 管理端预览用 9:16 大屏流（与游客 16:9 主流隔离：换形象不打断游客）
export const PORTRAIT_FLV = `${BRIDGE}/stream_portrait.flv`

/**
 * 热拔插换形象：让正在直播的数字人当场换形象（~1s，不重连）。见 API_DOC 4.7。
 * screen='portrait' → 9:16 大屏流(8011)，与游客 16:9 主流隔离。
 * backgroundId（可选）：手动指定场景背景一并热切换；该形象+背景若已烘出底板会当场生效，
 * 未烘出时后端自动回退到原有默认背景，不影响换形象本身。
 */
export async function liveSetAvatar(avatarId, scenicId = 'lingshan', screen = 'portrait', backgroundId = '') {
  try {
    const body = { avatar_id: avatarId, scenic_id: scenicId, sessionid: '0', screen }
    if (backgroundId) body.background_id = backgroundId
    const res = await fetch(`${BRIDGE}/live/avatar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    return res.json()
  } catch (e) { return { ok: false, error: String(e) } }
}

/**
 * AI 定制形象：万相「人景一体」在线生成 → 落 ditto_avatars 双比例 → 即时入库可热切（~30s）。
 * 返回 { ok, avatar }（avatar.ready=true）。见 API_DOC 4.9。
 */
export async function generateAvatarAI({ prompt = '', scenic_id = 'lingshan', gender = 'female', style = '现代', name } = {}) {
  try {
    const res = await fetch(`${CLOUD_BASE}/digital-human/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, scenic_id, gender, style, name }),
    })
    return res.json()
  } catch (e) { return { ok: false, detail: String(e) } }
}

/**
 * 离线预览底板 URL（桥接 /live/avatar-plate）：与 /live/avatar 同候选解析，返回底板 JPEG。
 * 管理端调参即换此图，**不触碰直播流**，多用户零串扰。见 API_DOC 4.7.2。
 */
export function platePreviewUrl(avatarId, scenicId = 'lingshan', screen = 'portrait', backgroundId = '') {
  const q = new URLSearchParams({ avatar_id: avatarId, scenic_id: scenicId, screen })
  if (backgroundId) q.set('background_id', backgroundId)
  q.set('_t', String(Date.now()))   // 破缓存：参数变即换图
  return `${BRIDGE}/live/avatar-plate?${q.toString()}`
}

/** 热调数字人说话嘴幅（DITTO_LIP_SCALE，1=原始，越小张口越含蓄）。见 API_DOC 4.7.y */
export async function liveSetLip(scale, screen = 'both') {
  try {
    const res = await fetch(`${BRIDGE}/live/lip`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scale, screen }),
    })
    return res.json()
  } catch (e) { return { ok: false, error: String(e) } }
}

/** 甜美候选：批量生成（后台任务，立即返回）。见 API_DOC 4.10 */
export async function generateCandidates(scenicId = 'lingshan', count = 6, prompt = '') {
  const res = await fetch(`${CLOUD_BASE}/digital-human/generate-candidates`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ scenic_id: scenicId, count, prompt }),
  })
  return res.json()
}
/** 甜美候选：列表 + 进度 */
export async function listCandidates() {
  const res = await fetch(`${CLOUD_BASE}/digital-human/candidates`)
  return res.json()
}
/** 甜美候选：预览 URL（asp 空=缩略；16x9/9x16=原比例） */
export function candidatePreviewUrl(cid, asp = '') {
  const q = asp ? `?asp=${asp}` : ''
  return `${CLOUD_BASE}/digital-human/candidate-preview/${cid}${q}`
}
/** 甜美候选：采用为可驱动形象（拒未居中） */
export async function adoptCandidate(cid, payload = {}) {
  const res = await fetch(`${CLOUD_BASE}/digital-human/candidates/${cid}/adopt`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
  })
  return res.json()
}

/** 热切数字人默认情绪基调（set_emotion）。见 API_DOC 4.7.z */
export async function liveSetEmotion(emotion, screen = 'portrait', sessionid = '0') {
  try {
    const res = await fetch(`${BRIDGE}/live/emotion`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ emotion, screen, sessionid }),
    })
    return res.json()
  } catch (e) { return { ok: false, error: String(e) } }
}
