// 客户端行为埋点：上报服务端从对话里看不到的信号（画像/功能/到访/满意度）。
// 失败永远静默——埋点绝不能影响游客体验。

// 每次访问一个唯一会话 id（sessionStorage：关标签即新会话，"会话数"才有意义）
function visitorId(): string {
  const KEY = 'lingjing.sid'
  try {
    let id = sessionStorage.getItem(KEY)
    if (!id) {
      id = 's_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36)
      sessionStorage.setItem(KEY, id)
    }
    return id
  } catch {
    return 's_anon'
  }
}

export interface TrackCtx { scenic: string; groupType?: string; lang?: string }

export function track(type: string, ctx: TrackCtx, payload?: Record<string, unknown>) {
  try {
    const body: Record<string, unknown> = { session_id: visitorId(), scenic_id: ctx.scenic, type }
    if (payload) body.payload = payload
    // 画像随 session_start 携带（管理端 /analytics/profile 据此聚合）
    if (type === 'session_start') { body.group_type = ctx.groupType; body.lang = ctx.lang }
    const json = JSON.stringify(body)
    // 退出类事件用 sendBeacon，保证页面卸载时也能送达
    if (type === 'session_end' && navigator.sendBeacon) {
      navigator.sendBeacon('/rag/analytics/event', new Blob([json], { type: 'application/json' }))
      return
    }
    void fetch('/rag/analytics/event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: json,
      keepalive: true,
    }).catch(() => {})
  } catch { /* 埋点失败静默 */ }
}
