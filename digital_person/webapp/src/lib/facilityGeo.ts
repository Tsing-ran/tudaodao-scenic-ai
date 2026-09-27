// 设施坐标解析（地图导航用）。
// 背景：后端 /tour/facilities 只给设施「名称」（如「梵宫一层」「胜境广场东侧」），没有经纬度。
// 本模块把每个设施点位映射到 GCJ-02 坐标（高德底图同基准），供「设施速查」在地图上画路线到该设施。
//
// 坐标来源分两类，均已逐条注释：
//   1) 真实锚点 = routeData 里景点的真实 GCJ-02 坐标（高德 POI 检索得来）——设施名含该景点名时直接用它；
//   2) 假设锚点(ASSUMED) = 后端设施名里出现、但 routeData 无对应景点的地标（游客中心/胜境广场/菩提大道/
//      灵山精舍/佛前广场）——按其相对真实景点的合理方位「假设」经纬度（用户已明确授权：坐标未知时可假设合理数据）。
// 若设施名无任何锚点命中，则落到景区质心 + 基于名字哈希的小抖动（~15m），保证仍能在地图上落一个合理点位。
import { SCENIC_ROUTES } from '@/lib/routeData'
import { haversine } from '@/lib/geo'

export interface FacilityAnchor {
  keys: string[]                 // 设施名中出现即命中的关键词（按从具体到宽泛排序）
  lng: number
  lat: number
  assumed: boolean               // true = 该锚点坐标为假设值（非 routeData 真实景点）
}

// —— 灵山胜境：设施锚点表 ——（真实景点坐标取自 routeData.LINGSHAN_ROUTE.stops）
// 顺序重要：先匹配更具体的关键词（「佛前广场」要早于「广场」，否则会被「胜境广场」抢走）。
const LINGSHAN_ANCHORS: FacilityAnchor[] = [
  // ① 真实景点锚点（GCJ-02，与 routeData 完全一致）
  { keys: ['九龙灌浴'], lng: 120.099984, lat: 31.424601, assumed: false },
  { keys: ['祥符禅寺', '祥符'], lng: 120.098012, lat: 31.427949, assumed: false },
  { keys: ['五印坛城', '坛城'], lng: 120.103054, lat: 31.424676, assumed: false },
  { keys: ['阿育王柱', '阿育王'], lng: 120.099261, lat: 31.426188, assumed: false },
  { keys: ['梵宫'], lng: 120.102420, lat: 31.428218, assumed: false },
  // ② 假设锚点（ASSUMED：后端设施名有、routeData 无对应景点，按真实方位合理假设）
  //    佛前广场 = 灵山大佛(120.096477,31.430194)前的广场，略偏南留出广场纵深
  { keys: ['佛前广场', '佛前'], lng: 120.096520, lat: 31.429980, assumed: true },
  //    菩提大道 = 连接梵宫与大佛的主轴大道，取两点之间偏中位置
  { keys: ['菩提大道', '菩提'], lng: 120.099500, lat: 31.429100, assumed: true },
  //    灵山精舍 = 大佛/梵宫片区内的禅意休息院落，假设在两者之间
  { keys: ['灵山精舍', '精舍'], lng: 120.100600, lat: 31.428700, assumed: true },
  //    游客中心 = 景区入口（门楼 120.101730,31.422257）南侧集散区
  { keys: ['游客中心'], lng: 120.101880, lat: 31.421500, assumed: true },
  //    胜境广场 = 进门后的第一大集散广场，紧邻门楼北侧
  { keys: ['胜境广场', '胜境', '广场'], lng: 120.101600, lat: 31.422750, assumed: true },
  // ③ 兜底：大佛 / 门楼（放最后，避免抢占带「佛/门」字的更具体名）
  { keys: ['灵山大佛', '大佛'], lng: 120.096477, lat: 31.430194, assumed: false },
  { keys: ['门楼'], lng: 120.101730, lat: 31.422257, assumed: false },
]

const ANCHORS: Record<string, FacilityAnchor[]> = {
  lingshan: LINGSHAN_ANCHORS,
}

// 是否具备「地图导航版设施速查」的能力：该景区有路线坐标（能画图 + 定入口）即算有。
// 无坐标的景区在 FacilitySheet 里回退为「让数字人语音指路」。
export function hasFacilityMap(scenic: string): boolean {
  return !!SCENIC_ROUTES[scenic]
}

// 字符串确定性哈希 → 用于给「同锚点多设施 / 无锚点设施」加稳定的小抖动，避免坐标完全重叠。
function hashStr(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return h
}

export interface FacilityLoc {
  lng: number
  lat: number
  assumed: boolean               // 命中的锚点是否为假设坐标（用于 UI 上标注「参考位置」）
  anchorHit: boolean             // 是否命中了某锚点（false = 落到质心兜底）
}

// 景区质心（所有真实景点的平均坐标）——无锚点命中时的兜底中心。
function centroid(scenic: string): [number, number] | null {
  const stops = SCENIC_ROUTES[scenic]?.stops ?? []
  if (!stops.length) return null
  const lng = stops.reduce((a, s) => a + s.lng, 0) / stops.length
  const lat = stops.reduce((a, s) => a + s.lat, 0) / stops.length
  return [lng, lat]
}

// 解析某设施点位名 → GCJ-02 坐标。命中锚点用锚点坐标；否则落质心。均加名字哈希的小抖动（~10-15m）。
export function facilityCoord(scenic: string, pointName: string): FacilityLoc | null {
  const anchors = ANCHORS[scenic]
  const h = hashStr(pointName)
  // 抖动幅度：经度 ~ ±14m（此纬度 1° 经度≈95km），纬度 ~ ±11m（1°≈111km）；确定性、稳定不跳。
  const jLng = (((h & 0xff) / 255) - 0.5) * 0.0003
  const jLat = ((((h >> 8) & 0xff) / 255) - 0.5) * 0.0002
  if (anchors) {
    for (const a of anchors) {
      if (a.keys.some((k) => pointName.includes(k))) {
        return { lng: a.lng + jLng, lat: a.lat + jLat, assumed: a.assumed, anchorHit: true }
      }
    }
  }
  const c = centroid(scenic)
  if (!c) return null
  // 兜底：质心 + 抖动，坐标视为「假设」（不精确）。
  return { lng: c[0] + jLng * 2, lat: c[1] + jLat * 2, assumed: true, anchorHit: false }
}

export interface Entrance { name: string; lng: number; lat: number }

// 景区入口（起点兜底）= 路线第一站（灵山=门楼，本就是正门）。
export function facilityEntrance(scenic: string): Entrance | null {
  const s = SCENIC_ROUTES[scenic]?.stops?.[0]
  if (!s) return null
  return { name: s.name, lng: s.lng, lat: s.lat }
}

// 最近景点下标（按球面距离）。
function nearestStopIdx(scenic: string, lng: number, lat: number): number {
  const stops = SCENIC_ROUTES[scenic]?.stops ?? []
  let best = 0
  let bestD = Infinity
  stops.forEach((s, i) => {
    const d = haversine([lng, lat], [s.lng, s.lat])
    if (d < bestD) { bestD = d; best = i }
  })
  return best
}

// 构造从 origin 到 dest 的「沿景区步道」路线（尽量贴真实路网，导航软件式）：
//   起点/终点各就近吸附到最近景点 → 沿 routeData.walkPaths 的相邻段拼出中段 → 首尾接直连段。
//   无 walkPaths 或首尾同一最近站 → 退化为直线（origin→dest）。返回 [lng,lat][]。
export function facilityRoutePath(
  scenic: string,
  origin: [number, number],
  dest: [number, number],
): [number, number][] {
  const route = SCENIC_ROUTES[scenic]
  if (!route) return [origin, dest]
  const walk = route.walkPaths
  const oi = nearestStopIdx(scenic, origin[0], origin[1])
  const di = nearestStopIdx(scenic, dest[0], dest[1])
  if (!walk || oi === di) return [origin, dest]
  const lo = Math.min(oi, di)
  const hi = Math.max(oi, di)
  // walk[k] 连接 stop k → stop k+1；取 lo..hi-1 段前向拼接。
  let seg: [number, number][] = []
  for (let k = lo; k < hi; k++) {
    if (walk[k]) seg = seg.concat(walk[k])
  }
  if (oi > di) seg = seg.slice().reverse()  // origin 在后 → 整体反向，使路径从 origin 侧出发
  if (!seg.length) return [origin, dest]
  return [origin, ...seg, dest]
}

// 沿路径累计步行距离（米）。
export function pathLengthM(path: [number, number][]): number {
  let sum = 0
  for (let i = 1; i < path.length; i++) sum += haversine(path[i - 1], path[i])
  return Math.round(sum)
}
