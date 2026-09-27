// 坐标与定位工具。
// 背景：浏览器 navigator.geolocation 返回 WGS-84，而高德底图与项目 POI 坐标是 GCJ-02（火星坐标），
// 直接比较会有 50~500m 偏移。本模块统一一切定位到 GCJ-02：
//   优先用高德定位插件（原生 GCJ-02、国内最准、芯片已融合北斗/GPS/GLONASS/Galileo），
//   失败回退浏览器定位再做 WGS-84 → GCJ-02 转换。
// POI 真坐标取自 routeData（高德 POI 检索的 GCJ-02），不再依赖后端那套粗糙坐标。
import { SCENIC_ROUTES } from '@/lib/routeData'

const PI = Math.PI
const A = 6378245.0                     // 克拉索夫斯基椭球长半轴
const EE = 0.00669342162296594323       // 偏心率平方

function outOfChina(lng: number, lat: number): boolean {
  return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271
}
function transformLat(x: number, y: number): number {
  let ret = -100 + 2 * x + 3 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x))
  ret += (20 * Math.sin(6 * x * PI) + 20 * Math.sin(2 * x * PI)) * 2 / 3
  ret += (20 * Math.sin(y * PI) + 40 * Math.sin(y / 3 * PI)) * 2 / 3
  ret += (160 * Math.sin(y / 12 * PI) + 320 * Math.sin(y * PI / 30)) * 2 / 3
  return ret
}
function transformLng(x: number, y: number): number {
  let ret = 300 + x + 2 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x))
  ret += (20 * Math.sin(6 * x * PI) + 20 * Math.sin(2 * x * PI)) * 2 / 3
  ret += (20 * Math.sin(x * PI) + 40 * Math.sin(x / 3 * PI)) * 2 / 3
  ret += (150 * Math.sin(x / 12 * PI) + 300 * Math.sin(x / 30 * PI)) * 2 / 3
  return ret
}

// WGS-84 → GCJ-02（高德/火星坐标）。境外坐标无偏移，原样返回。
export function wgs84ToGcj02(lng: number, lat: number): [number, number] {
  if (outOfChina(lng, lat)) return [lng, lat]
  let dLat = transformLat(lng - 105.0, lat - 35.0)
  let dLng = transformLng(lng - 105.0, lat - 35.0)
  const radLat = (lat / 180.0) * PI
  let magic = Math.sin(radLat)
  magic = 1 - EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  dLat = (dLat * 180.0) / (((A * (1 - EE)) / (magic * sqrtMagic)) * PI)
  dLng = (dLng * 180.0) / ((A / sqrtMagic) * Math.cos(radLat) * PI)
  return [lng + dLng, lat + dLat]
}

// 球面两点距离（米）。a/b = [lng, lat]
export function haversine(a: [number, number], b: [number, number]): number {
  const R = 6371000
  const toRad = (d: number) => (d * PI) / 180
  const dLat = toRad(b[1] - a[1])
  const dLng = toRad(b[0] - a[0])
  const s = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a[1])) * Math.cos(toRad(b[1])) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(s))
}

export interface GeoFix { lng: number; lat: number; accuracy: number; source: 'browser' }

// 浏览器定位失败 → 按错误码给可操作的中文提示（区分"拒绝/不可用/超时"）。
function geoErrorMessage(e: GeolocationPositionError): string {
  // 文案保持「UI 中立」：本函数被多个抽屉复用，各家页面上的替代入口并不相同
  // （GpsSheet 有手动选点、FacilityMapSheet 没有）→ 这里只讲定位本身，替代路径由各调用方自己追加。
  if (e.code === 1) {   // PERMISSION_DENIED
    return '无法定位：定位权限被拒绝或未授权。请用 Safari/系统浏览器打开（微信/扫码内置浏览器会拦截定位），'
      + '并在 iPhone「设置 → 隐私与安全性 → 定位服务」开启、且把 Safari 设为「使用 App 期间」。'
  }
  if (e.code === 2) return '位置暂不可用，请到开阔处重试。'   // POSITION_UNAVAILABLE
  if (e.code === 3) return '定位超时，请重试。'              // TIMEOUT
  return '定位失败：' + e.message
}

// 直接在用户手势内请求浏览器定位（关键修复）：iOS Safari 要求 geolocation 调用紧贴用户手势——
// 调用前不能先 await 任何异步（如加载高德脚本），否则会丢失手势激活；且短时间重复调用会触发
// iOS 17.4+ 限流，表现为"无弹窗直接拒绝"。故这里只用浏览器原生定位、单次同步调用，再就地转 GCJ-02。
export function requestBrowserPosition(onFix: (f: GeoFix) => void, onError: (msg: string) => void, timeout = 10000): void {
  if (!('geolocation' in navigator)) { onError('当前浏览器不支持定位，请用 Safari 打开。'); return }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const [lng, lat] = wgs84ToGcj02(pos.coords.longitude, pos.coords.latitude)
      onFix({ lng, lat, accuracy: Math.round(pos.coords.accuracy), source: 'browser' })
    },
    (e) => onError(geoErrorMessage(e)),
    { enableHighAccuracy: true, timeout, maximumAge: 0 },
  )
}

// Promise 版（供非手势/异步场景）。⚠️ 用户手势内取定位请直接用 requestBrowserPosition（同步调用，iOS 才弹窗）。
export function getPositionGCJ02(opts: { timeout?: number } = {}): Promise<GeoFix> {
  return new Promise((resolve, reject) => requestBrowserPosition(resolve, (m) => reject(new Error(m)), opts.timeout ?? 10000))
}

export interface ScenicPOI { id: string; name: string; lng: number; lat: number }
export interface NearbyPOI extends ScenicPOI { distance: number }   // distance 单位：米

// 该景区的真实 POI（GCJ-02，来自 routeData）。无路线数据的景区返回空。
export function scenicPOIs(scenic: string): ScenicPOI[] {
  return (SCENIC_ROUTES[scenic]?.stops ?? []).map((s) => ({ id: s.id, name: s.name, lng: s.lng, lat: s.lat }))
}

// 给定 GCJ-02 坐标，返回该景区最近的 N 个 POI（升序）。
export function nearestPOIs(scenic: string, lng: number, lat: number, n = 4): NearbyPOI[] {
  const here: [number, number] = [lng, lat]
  return scenicPOIs(scenic)
    .map((p) => ({ ...p, distance: Math.round(haversine(here, [p.lng, p.lat])) }))
    .sort((a, b) => a.distance - b.distance)
    .slice(0, n)
}

// 演示用「模拟位置」：取该景区首/中/尾三个 POI（与真坐标同基准 GCJ-02）。
export function simSpots(scenic: string): { label: string; lng: number; lat: number }[] {
  const stops = SCENIC_ROUTES[scenic]?.stops ?? []
  if (!stops.length) return []
  const idx = Array.from(new Set([0, Math.floor(stops.length / 2), stops.length - 1]))
  return idx.map((i) => ({ label: stops[i].name, lng: stops[i].lng, lat: stops[i].lat }))
}

// ── 主动开讲（地理围栏）────────────────────────────────────────────────
export interface GeoWatcher { stop: () => void }

// 持续定位（统一 GCJ-02）。连续监听用浏览器 watchPosition + 转换（稳定省心）；
// 一次性精确定位才用高德插件（见 getPositionGCJ02）。返回停止函数。
export function watchPositionGCJ02(onFix: (f: GeoFix) => void, onError?: (e: Error) => void): GeoWatcher {
  if (!('geolocation' in navigator)) { onError?.(new Error('设备不支持定位')); return { stop: () => {} } }
  const id = navigator.geolocation.watchPosition(
    (pos) => {
      const [lng, lat] = wgs84ToGcj02(pos.coords.longitude, pos.coords.latitude)
      onFix({ lng, lat, accuracy: Math.round(pos.coords.accuracy), source: 'browser' })
    },
    (e) => onError?.(new Error(e.message)),
    { enableHighAccuracy: true, maximumAge: 5000, timeout: 15000 },
  )
  return { stop: () => { try { navigator.geolocation.clearWatch(id) } catch { /* ignore */ } } }
}

export interface GeofenceOpts { radius?: number; rearm?: number; cooldownMs?: number }

// 地理围栏判定器（带迟滞 + 冷却，防反复触发）：
//   进入某 POI 半径(默认 50m) 且 距上次触发超冷却 → 返回该 POI（最近者优先）；
//   离开 > rearm(默认 80m) 才重新武装该点；每点 cooldown(默认 5min) 内不重复。
export function makeGeofence(scenic: string, opts: GeofenceOpts = {}) {
  const R = opts.radius ?? 50
  const REARM = opts.rearm ?? 80
  const COOL = opts.cooldownMs ?? 5 * 60 * 1000
  const inside = new Set<string>()              // 已在围栏内（已触发，等离开重新武装）
  const lastAt: Record<string, number> = {}     // 每点上次触发时刻
  return {
    feed(lng: number, lat: number, now: number): NearbyPOI | null {
      let trigger: NearbyPOI | null = null
      for (const p of scenicPOIs(scenic)) {
        const d = haversine([lng, lat], [p.lng, p.lat])
        if (d <= R) {
          if (!inside.has(p.id) && now - (lastAt[p.id] || 0) > COOL) {
            inside.add(p.id); lastAt[p.id] = now
            if (!trigger || d < trigger.distance) trigger = { ...p, distance: Math.round(d) }
          }
        } else if (d > REARM) {
          inside.delete(p.id)                     // 离开足够远 → 重新武装
        }
      }
      return trigger
    },
    reset() { inside.clear() },
  }
}
