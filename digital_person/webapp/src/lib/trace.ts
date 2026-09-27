// 我的足迹 + 徽章：纯前端 localStorage，记录游客本次旅程行为，解锁成就徽章。
const KEY = 'lingjing.trace.v1'

export interface Trace {
  visited: string[]   // 到访过的站点/景点名
  asks: number        // 提问次数
  photos: number      // 拍照定位次数
  routesDone: string[] // 走完的路线 id
  connected: boolean
  rating: number      // 本次导览满意度评分 1-5（0=未评）
}

const empty = (): Trace => ({ visited: [], asks: 0, photos: 0, routesDone: [], connected: false, rating: 0 })

export function load(): Trace {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) return { ...empty(), ...JSON.parse(raw) }
  } catch { /* ignore */ }
  return empty()
}

function save(t: Trace) {
  try { localStorage.setItem(KEY, JSON.stringify(t)) } catch { /* ignore */ }
}

export function recordVisit(name: string): Trace {
  const t = load()
  if (name && !t.visited.includes(name)) t.visited.push(name)
  save(t); return t
}
export function recordAsk(): Trace { const t = load(); t.asks += 1; save(t); return t }
export function recordPhoto(): Trace { const t = load(); t.photos += 1; save(t); return t }
export function recordConnected(): Trace { const t = load(); t.connected = true; save(t); return t }
export function recordRating(score: number): Trace { const t = load(); t.rating = score; save(t); return t }
export function recordRouteDone(id: string): Trace {
  const t = load()
  if (id && !t.routesDone.includes(id)) t.routesDone.push(id)
  save(t); return t
}
export function reset() { save(empty()) }

// 图标见 lib/icons.tsx 的 BADGE_ICONS（按 id 取）
export interface Badge { id: string; label: string; desc: string; earned: boolean }
export function badges(t: Trace): Badge[] {
  return [
    { id: 'meet', label: '初次见面', desc: '开启导览', earned: t.connected },
    // 到访 1 个景点即解锁：首次打卡就该有正反馈，否则第一次「我已到达」什么都不弹（探索者要 3 个）
    { id: 'footprint', label: '第一个足迹', desc: '到访 1 个景点', earned: t.visited.length >= 1 },
    { id: 'explorer', label: '探索者', desc: '到访 3 个景点', earned: t.visited.length >= 3 },
    { id: 'curious', label: '好奇宝宝', desc: '提问 5 次', earned: t.asks >= 5 },
    { id: 'scholar', label: '博学之星', desc: '提问 12 次', earned: t.asks >= 12 },
    { id: 'shutter', label: '摄影达人', desc: '拍照定位 1 次', earned: t.photos >= 1 },
    { id: 'pilgrim', label: '全程打卡', desc: '走完一条路线', earned: t.routesDone.length >= 1 },
  ]
}
