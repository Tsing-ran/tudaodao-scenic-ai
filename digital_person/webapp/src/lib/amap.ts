// 高德地图 JSAPI 2.0 加载器
// - 先设安全密钥（必须在脚本加载前），再注入 <script>，Promise 缓存避免重复加载。
// - 凭据走 Vite env（webapp/.env.local，不进 git）。未配 key 时优雅报错，不崩页面。
const KEY = import.meta.env.VITE_AMAP_KEY as string | undefined
const SECURITY = import.meta.env.VITE_AMAP_SECURITY as string | undefined

declare global {
  interface Window {
    _AMapSecurityConfig?: { securityJsCode?: string }
    AMap?: unknown
  }
}

let loadPromise: Promise<unknown> | null = null

export function amapConfigured(): boolean {
  return !!KEY
}

// 返回 window.AMap（类型为 any，AMap 无官方 d.ts；调用处按需断言）。
export function loadAMap(): Promise<unknown> {
  if (typeof window === 'undefined') return Promise.reject(new Error('无 window'))
  if (window.AMap) return Promise.resolve(window.AMap)
  if (loadPromise) return loadPromise
  if (!KEY) return Promise.reject(new Error('高德 Key 未配置：请在 webapp/.env.local 设 VITE_AMAP_KEY'))
  if (SECURITY) window._AMapSecurityConfig = { securityJsCode: SECURITY }
  loadPromise = new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = `https://webapi.amap.com/maps?v=2.0&key=${KEY}`
    s.async = true
    s.onerror = () => { loadPromise = null; reject(new Error('高德地图脚本加载失败（检查网络/Key/域名白名单）')) }
    s.onload = () => { window.AMap ? resolve(window.AMap) : reject(new Error('AMap 未就绪')) }
    document.head.appendChild(s)
  })
  return loadPromise
}
