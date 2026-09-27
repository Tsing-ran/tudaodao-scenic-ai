import { useEffect, useState } from 'react'
import { MapPin, Crosshair, SpeakerHigh, CircleNotch, NavigationArrow, CheckCircle, X } from '@phosphor-icons/react'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer'
import { requestBrowserPosition, nearestPOIs, simSpots } from '@/lib/geo'
import * as api from '@/lib/api'
import type { Route } from '@/lib/api'
import { cn } from '@/lib/utils'

interface Props {
  open: boolean; onOpenChange: (o: boolean) => void
  scenic: string
  onAsk: (stationName: string) => void
  onArrive: (stationName: string) => void   // 「我已到达」：只记录到访（触发徽章），不发起问答
}

// 页面上「选当前位置」入口的标题。定位失败文案要指向它，故收成常量，防两处措辞各改各的。
const PICKER_LABEL = '选择我的当前位置'

// 无本地坐标景区的可选站点 = 后端 /tour/routes 给的全部信息（站名 + 一句指路 + 在某条游线里的次序），没有经纬度。
interface Waypoint { id: string; name: string; hint: string; routeId: string; idx: number }
// 结果卡。note 要么是实测距离，要么是该站的指路语——两种来源都不编造距离。
interface ResultCard { id: string; name: string; note: string }

// 多条游线里的同名站以首次出现为准，保住那条线的站序（推进「接下来」要靠它）。
function flattenStations(rs: Route[]): Waypoint[] {
  const seen = new Set<string>()
  const out: Waypoint[] = []
  rs.forEach((r) => r.stations.forEach((s, i) => {
    if (seen.has(s.name)) return
    seen.add(s.name)
    out.push({ id: `${r.id}-${i}`, name: s.name, hint: s.hint, routeId: r.id, idx: i })
  }))
  return out
}

export default function GpsSheet({ open, onOpenChange, scenic, onAsk, onArrive }: Props) {
  const [arrived, setArrived] = useState<Set<string>>(new Set())   // 本次已标记到达的站（按钮态）
  const [items, setItems] = useState<ResultCard[]>([])
  const [sims, setSims] = useState<{ label: string; lng: number; lat: number }[]>([])
  const [waypoints, setWaypoints] = useState<Waypoint[]>([])
  const [loading, setLoading] = useState(false)
  const [origin, setOrigin] = useState('')      // 当前定位来源描述
  const [locating, setLocating] = useState(false)
  const [err, setErr] = useState('')

  // 点位来源分档：coords=本地有真坐标（能算距离、能接真实 GPS）；stations=只有后端站名（按游线顺序推进）；none=该景区两者皆无
  const mode: 'coords' | 'stations' | 'none' = sims.length ? 'coords' : waypoints.length ? 'stations' : 'none'

  // 抽屉打开时取该景区可选点位：优先前端 routeData 的真坐标（GCJ-02，与高德底图同基准），
  // 没有就退到后端游线站名——宁可只给站序，也不为无坐标景区臆造经纬度。
  useEffect(() => {
    if (!open) return
    const local = simSpots(scenic)
    setSims(local)
    setWaypoints([])
    if (local.length) return
    setLoading(true)
    let alive = true
    api.routes(scenic)
      .then((rs) => { if (alive) setWaypoints(flattenStations(rs)) })
      .catch(() => { if (alive) setWaypoints([]) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [open, scenic])

  // 坐标统一为 GCJ-02（高德底图同基准）→ 前端算最近 POI，无需后端
  const resolve = (lng: number, lat: number, label: string) => {
    setErr('')
    setItems(nearestPOIs(scenic, lng, lat).map((p) => ({ id: p.id, name: p.name, note: `约 ${p.distance} 米` })))
    setOrigin(label)
  }

  // 无坐标景区：把选中的站当起点，沿同一条游线列出接下来的站。只用后端给的站序与指路语，不显示（也不假造）距离。
  const pickStation = (w: Waypoint) => {
    setErr('')
    setItems(waypoints
      .filter((x) => x.routeId === w.routeId && x.idx >= w.idx)
      .slice(0, 4)
      .map((x, i) => ({ id: x.id, name: x.name, note: i === 0 ? '' : x.hint || '沿游线继续前行' })))
    setOrigin(w.name)
  }

  // geoErrorMessage 只讲定位本身（UI 中立，多个抽屉共用），替代入口由本页自己追加——
  // 且只在本页真有该入口时才提，否则等于把用户指向一个不存在的控件。
  const rephrase = (msg: string) => (mode === 'coords' ? `${msg}也可以直接在下方「${PICKER_LABEL}」里点一个点位。` : msg)

  // ⚠️ 不能写成 async/await：iOS Safari 要求定位调用紧贴点击手势，先 await 会丢手势 → 不弹授权框。
  const useRealGps = () => {
    setErr(''); setLocating(true)
    requestBrowserPosition(
      (fix) => { resolve(fix.lng, fix.lat, `你的位置（±${fix.accuracy}m）`); setLocating(false) },
      (msg) => { setErr(rephrase(msg)); setLocating(false) },
    )
  }

  const speak = (name: string) => { onAsk(name); onOpenChange(false) }
  // 「我已到达」：记录到访（解锁足迹类徽章），本页保持打开，方便逐个点位连着标
  const arrive = (name: string) => { onArrive(name); setArrived((s) => new Set(s).add(name)) }

  const chip = (on: boolean) => cn('rounded-full border px-3.5 py-2 text-[13px] font-medium transition duration-200 ease-[var(--ease-out)] active:scale-95',
    on ? 'border-primary bg-primary text-primary-foreground shadow-sm shadow-primary/25' : 'bg-card hover:border-primary/30')

  return (
    <Drawer open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) { setItems([]); setOrigin(''); setErr('') } }}>
      <DrawerContent className="mx-auto max-h-[88vh] max-w-[480px]">
        <DrawerHeader className="relative pb-1">
          <DrawerClose aria-label="关闭" className="absolute right-3 top-2 z-10 flex size-8 items-center justify-center rounded-full bg-muted text-muted-foreground transition active:scale-90">
            <X className="size-4" />
          </DrawerClose>
          <DrawerTitle className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <NavigationArrow className="size-[18px]" weight="duotone" />
            </span>
            定位讲解
          </DrawerTitle>
        </DrawerHeader>

        <div className="overflow-y-auto px-4 pb-[max(20px,env(safe-area-inset-bottom))] pt-1">
          {/* 真实定位只给有真坐标的景区：其余景区点了必然算不出最近点，与其给个必错的按钮，不如只留手动选点 */}
          {mode === 'coords' && (
            <button
              onClick={useRealGps}
              disabled={locating}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-primary py-3.5 text-[15px] font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition duration-200 ease-[var(--ease-out)] hover:shadow-xl hover:shadow-primary/30 active:scale-[0.98] disabled:opacity-60"
            >
              {locating ? <CircleNotch className="size-4 animate-spin" /> : <Crosshair className="size-4" />}
              {locating ? '定位中…' : '用我的真实位置'}
            </button>
          )}

          {loading && (
            <div className="flex items-center justify-center gap-2 py-6 text-[13px] text-muted-foreground">
              <CircleNotch className="size-4 animate-spin" /> 正在读取该景区的点位…
            </div>
          )}

          {/* 选当前位置：不依赖 GPS 的主路径，任何有点位数据的景区都必须给得出 */}
          {!loading && mode !== 'none' && (
            <div className={cn(mode === 'coords' && 'mt-4')}>
              <div className="text-[13px] font-semibold text-muted-foreground">{mode === 'coords' ? `或${PICKER_LABEL}` : PICKER_LABEL}</div>
              {mode === 'stations' && (
                <div className="mt-0.5 text-[12px] text-muted-foreground/80">该景区暂无精确坐标，点你此刻所在的站即可</div>
              )}
              <div className="mt-2 flex flex-wrap gap-2">
                {mode === 'coords'
                  ? sims.map((s) => (
                    <button key={s.label} onClick={() => resolve(s.lng, s.lat, s.label)} className={chip(origin === s.label)}>
                      {s.label}
                    </button>
                  ))
                  : waypoints.map((w) => (
                    <button key={w.id} onClick={() => pickStation(w)} className={chip(origin === w.name)}>
                      {w.name}
                    </button>
                  ))}
              </div>
            </div>
          )}

          {/* 该景区连站点数据都没有：如实说明 + 指一条真的走得通的路（首页问答对全部景区可用） */}
          {!loading && mode === 'none' && (
            <div className="rounded-2xl border bg-card p-4">
              <div className="flex items-center gap-2 text-[13.5px] font-medium">
                <MapPin className="size-4 text-primary" weight="duotone" />
                该景区还没有站点数据
              </div>
              <p className="mt-1.5 text-[12.5px] leading-relaxed text-muted-foreground">
                暂时没法按位置给你指路。回到首页用语音或文字直接问一句就行，比如「我在正门，附近有什么值得看」。
              </p>
            </div>
          )}

          {err && <p className="mt-3 rounded-xl bg-amber-500/10 px-3 py-2.5 text-[12.5px] leading-relaxed text-amber-700 dark:text-amber-400">{err}</p>}

          {/* 结果：最近景点 */}
          {items.length > 0 && (
            <div className="mt-5">
              <div className="mb-2 flex items-center gap-1.5 text-[13px] text-muted-foreground">
                <MapPin className="size-3.5 text-primary" weight="duotone" />
                <span>{mode === 'coords' ? `从「${origin}」出发，离你最近的` : `你在「${origin}」，沿这条游线接下来`}</span>
              </div>
              <div className="flex flex-col gap-2">
                {items.map((it, i) => (
                  <div key={it.id}
                    className={cn('flex items-center gap-3 rounded-2xl border p-3.5 transition duration-200 ease-[var(--ease-out)]',
                      i === 0 ? 'border-sweet/40 bg-sweet/[0.07]' : 'bg-card')}>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 font-medium">
                        {it.name}
                        {i === 0 && <span className="rounded-full bg-sweet px-1.5 py-0.5 text-[10px] font-medium text-sweet-foreground shadow-sm">{mode === 'coords' ? '最近' : '你在这'}</span>}
                      </div>
                      {it.note && <div className="mt-0.5 text-[12px] text-muted-foreground">{it.note}</div>}
                    </div>
                    <div className="flex shrink-0 flex-col items-stretch gap-1.5">
                      <button
                        onClick={() => speak(it.name)}
                        className="inline-flex items-center justify-center gap-1.5 rounded-full bg-primary/10 px-3 py-1.5 text-[13px] font-medium text-primary transition duration-200 ease-[var(--ease-out)] hover:bg-primary/15 active:scale-95"
                      >
                        <SpeakerHigh className="size-3.5" /> 听讲解
                      </button>
                      <button
                        onClick={() => arrive(it.name)}
                        disabled={arrived.has(it.name)}
                        className={cn('inline-flex items-center justify-center gap-1.5 rounded-full px-3 py-1.5 text-[13px] font-medium transition duration-200 ease-[var(--ease-out)] active:scale-95',
                          arrived.has(it.name) ? 'bg-emerald-500/12 text-emerald-600' : 'bg-sweet/12 text-sweet hover:bg-sweet/20')}
                      >
                        <CheckCircle className="size-3.5" weight={arrived.has(it.name) ? 'fill' : 'regular'} />
                        {arrived.has(it.name) ? '已到达' : '我已到达'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  )
}
