import { useEffect, useRef, useState } from 'react'
import { NavigationArrow, CircleNotch, Crosshair, SpeakerHigh, PersonSimpleWalk, MapPin, WarningCircle, X } from '@phosphor-icons/react'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer'
import { loadAMap, amapConfigured } from '@/lib/amap'
import { facilityCoord, facilityEntrance, facilityRoutePath, pathLengthM } from '@/lib/facilityGeo'
import { requestBrowserPosition, nearestPOIs } from '@/lib/geo'
import { FACILITY_ICONS } from '@/lib/icons'

/* eslint-disable @typescript-eslint/no-explicit-any */

export interface FacilityTarget { typeId: string; label: string; pointName: string }

// 定位点到本景区最近景点的容许上限。超出即判定「人不在景区」：此时若拿真实 GPS 当起点，
// 路线会拼成一条跨省直线、setFitView 把镜头拉到省级尺度使景区缩成一个点（异地调试/录制必现）。
const GEO_FENCE_M = 3000

// 玻璃质感底（与 RouteMapSheet 同款）：任意底色叠斜向高光 → 立体不扁平。
const gloss = (c: string) => `linear-gradient(150deg, rgba(255,255,255,.5), rgba(255,255,255,.08) 52%, rgba(0,0,0,.16)), ${c}`

// 起点 pin（你的位置 / 景区入口）：绿色圆点 + 白环 + 顶部气泡标签。
function originPin(label: string): string {
  return `<div style="position:relative;width:22px;height:22px;font-family:-apple-system,system-ui,sans-serif;">`
    + `<span style="position:absolute;left:50%;top:-19px;transform:translateX(-50%);white-space:nowrap;background:#10b981;color:#fff;font-size:10px;font-weight:600;padding:1.5px 7px;border-radius:9px;box-shadow:0 2px 7px rgba(16,185,129,.4)">${label}</span>`
    + `<span style="position:absolute;inset:0;border-radius:50%;background:${gloss('#10b981')};border:2px solid rgba(255,255,255,.95);box-shadow:0 1px 2px rgba(0,0,0,.28),0 5px 12px rgba(0,0,0,.22)"></span>`
    + `</div>`
}

// 终点 pin（目标设施）：主色水滴 + 白环 + 呼吸光晕 + 顶部设施名气泡。
function destPin(label: string): string {
  return `<div style="position:relative;width:30px;height:30px;font-family:-apple-system,system-ui,sans-serif;">`
    + `<span style="position:absolute;inset:-8px;border-radius:50%;background:radial-gradient(circle,rgba(109,94,252,.5),rgba(109,94,252,0) 68%);animation:halo-breathe 2.4s ease-in-out infinite"></span>`
    + `<span style="position:absolute;left:50%;top:-20px;transform:translateX(-50%);white-space:nowrap;max-width:150px;overflow:hidden;text-overflow:ellipsis;background:linear-gradient(160deg,#7c6efd,#6d5efc);color:#fff;font-size:10px;font-weight:600;padding:1.5px 8px;border-radius:9px;box-shadow:0 2px 7px rgba(109,94,252,.4)">${label}</span>`
    + `<span style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;border-radius:50%;background:${gloss('#6d5efc')};border:2.5px solid rgba(255,255,255,.95);box-shadow:0 1px 2px rgba(0,0,0,.3),0 6px 14px rgba(0,0,0,.24);color:#fff;font-size:15px;font-weight:700">◎</span>`
    + `</div>`
}

export default function FacilityMapSheet({ open, onOpenChange, scenic, target, onAsk }: {
  open: boolean
  onOpenChange: (o: boolean) => void
  scenic: string
  target: FacilityTarget | null
  onAsk: (q: string) => void
}) {
  const mapElRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<any>(null)
  // err = 地图级故障（Key/脚本加载失败）→ 整图不可用，才盖满屏错误层。
  // geoErr = 定位这一次没成功/不在景区 → 路线图仍旧有效（起点退回景区入口），只在距离条下提示一行。
  // 两者混用会让一次定位失败把已画好的路线整个盖掉，且 origin 未变 → 重建 effect 不跑 → 错误层再也退不掉。
  const [err, setErr] = useState('')
  const [geoErr, setGeoErr] = useState('')
  const [loading, setLoading] = useState(true)
  const [locating, setLocating] = useState(false)
  // 起点：默认景区入口；点「用我的位置」后换成真实 GPS（GCJ-02）。
  const [origin, setOrigin] = useState<{ name: string; lng: number; lat: number; real: boolean } | null>(null)
  const [distM, setDistM] = useState(0)
  const [assumed, setAssumed] = useState(false)

  const dest = target ? facilityCoord(scenic, target.pointName) : null
  const FIcon = target ? (FACILITY_ICONS[target.typeId] || MapPin) : MapPin

  // 打开时初始化起点为景区入口（兜底）。关闭时清理。
  useEffect(() => {
    setGeoErr('')
    if (!open || !target) { setOrigin(null); return }
    const ent = facilityEntrance(scenic)
    if (ent) setOrigin({ name: `入口·${ent.name}`, lng: ent.lng, lat: ent.lat, real: false })
    else setOrigin(null)
  }, [open, target, scenic])

  // 建图 + 画路线（起点/目标/景区变化即重建）。关闭即销毁。
  useEffect(() => {
    if (!open || !target || !dest || !origin) return
    if (!amapConfigured()) { setErr('高德 Key 未配置'); setLoading(false); return }
    let disposed = false
    setLoading(true); setErr('')
    const originLL: [number, number] = [origin.lng, origin.lat]
    const destLL: [number, number] = [dest.lng, dest.lat]
    const path = facilityRoutePath(scenic, originLL, destLL)
    setDistM(pathLengthM(path))
    setAssumed(dest.assumed)
    loadAMap().then((AMapU) => {
      const AMap = AMapU as any
      if (disposed || !mapElRef.current) return
      const map = new AMap.Map(mapElRef.current, {
        viewMode: '3D', pitch: 25, zoom: 16, center: destLL,
        mapStyle: 'amap://styles/whitesmoke', showLabel: true, rotateEnable: true, pitchEnable: true,
      })
      mapRef.current = map
      const overlays: any[] = []
      // 路线：白描边 + 主色填充 + 方向箭头（导航软件式），沿景区步道折线。
      overlays.push(new AMap.Polyline({
        path, isOutline: true, outlineColor: '#ffffff', borderWeight: 2.5,
        strokeColor: '#6d5efc', strokeWeight: 6, strokeOpacity: 0.95,
        lineJoin: 'round', lineCap: 'round', showDir: true, map,
      }))
      const om = new AMap.Marker({ position: originLL, anchor: 'center', zIndex: 100, content: originPin(origin.real ? '你的位置' : '入口') })
      om.setMap(map); overlays.push(om)
      const dm = new AMap.Marker({ position: destLL, anchor: 'center', zIndex: 120, content: destPin(target.pointName) })
      dm.setMap(map); overlays.push(dm)
      const fit = () => { try { map.setFitView(overlays, true, [40, 40, 40, 40], 17) } catch { /* ignore */ } }
      map.on('complete', () => { if (!disposed) { setLoading(false); fit() } })
      fit()
      ;[280, 700, 1200].forEach((d) => setTimeout(() => { if (!disposed) fit() }, d))
      setTimeout(() => { if (!disposed) setLoading(false) }, 1400)
    }).catch((e) => { if (!disposed) { setErr(e?.message || '地图加载失败'); setLoading(false) } })
    return () => {
      disposed = true
      if (mapRef.current) { try { mapRef.current.destroy() } catch { /* ignore */ } mapRef.current = null }
    }
    // dest 每次渲染都会新建对象，但值稳定；用其经纬度做依赖避免无谓重建。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, target, scenic, origin?.lng, origin?.lat, origin?.real])

  // 「用我的真实位置出发」：iOS 要求定位调用紧贴手势 → 不 await，回调里更新起点触发重建。
  const useMyLocation = () => {
    setGeoErr('')
    setLocating(true)
    requestBrowserPosition(
      (fix) => {
        // 闸门：人不在景区就别拿真实坐标当起点，保留入口起点，路线图照常可用。
        const near = nearestPOIs(scenic, fix.lng, fix.lat, 1)[0]
        if (near && near.distance > GEO_FENCE_M) {
          setGeoErr('你还不在景区内，已按景区入口为你规划')
          setLocating(false)
          return
        }
        setOrigin({ name: '你的位置', lng: fix.lng, lat: fix.lat, real: true })
        setLocating(false)
      },
      (msg) => { setGeoErr(msg); setLocating(false) },
    )
  }

  const walkMin = Math.max(1, Math.round(distM / 70))   // ~70 m/min 步行

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="mx-auto flex max-h-[92vh] max-w-[480px] flex-col">
        <DrawerHeader className="relative pb-1">
          <DrawerClose aria-label="关闭" className="absolute right-3 top-2 z-10 flex size-8 items-center justify-center rounded-full bg-muted text-muted-foreground transition active:scale-90">
            <X className="size-4" />
          </DrawerClose>
          <DrawerTitle className="flex items-center gap-2.5 pr-9">
            <span className="flex size-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <FIcon className="size-[18px]" weight="duotone" />
            </span>
            <span className="min-w-0">
              <span className="block truncate text-[16px] font-semibold leading-tight">{target?.pointName || '设施导航'}</span>
              {target && <span className="block text-[12px] font-normal text-muted-foreground">{target.label}</span>}
            </span>
          </DrawerTitle>
        </DrawerHeader>

        {!target || !dest ? (
          <div className="px-4 pb-8 pt-2 text-[14px] leading-relaxed text-muted-foreground">
            该设施暂无地图坐标，试试让数字人语音指路吧。
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col">
            {/* 地图：画出「起点 → 设施」路线 */}
            <div data-vaul-no-drag className="relative mx-4 shrink-0 overflow-hidden rounded-2xl border bg-muted" style={{ height: '46vh' }}>
              <div ref={mapElRef} className="size-full" />
              {loading && !err && (
                <div className="absolute inset-0 flex items-center justify-center gap-2 bg-background/60 text-[13px] text-muted-foreground backdrop-blur-sm">
                  <CircleNotch className="size-4 animate-spin" /> 正在规划路线…
                </div>
              )}
              {err && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6 text-center">
                  <p className="text-[13px] font-medium text-foreground">地图暂时不可用</p>
                  <p className="text-[12px] leading-relaxed text-muted-foreground">{err}</p>
                  <button
                    onClick={() => { onAsk(`${target.pointName}怎么走`); onOpenChange(false) }}
                    className="inline-flex items-center gap-1.5 rounded-full bg-primary px-4 py-2 text-[13px] font-semibold text-primary-foreground active:scale-95"
                  >
                    <SpeakerHigh className="size-4" /> 让数字人语音指路
                  </button>
                </div>
              )}
            </div>

            {/* 距离/时长条 + 参考位置标注 */}
            {!err && (
              <div className="mx-4 mt-3 flex items-center gap-3 rounded-2xl border bg-card px-4 py-3">
                <span className="flex size-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <PersonSimpleWalk className="size-5" weight="duotone" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-[17px] font-semibold">步行约 {distM} 米</span>
                    <span className="text-[13px] text-muted-foreground">约 {walkMin} 分钟</span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-1 text-[12px] text-muted-foreground">
                    <MapPin className="size-3 shrink-0" /> 从「{origin?.name}」出发{assumed && ' · 设施为参考位置'}
                  </div>
                </div>
              </div>
            )}

            {/* 定位提示：只占一行，不遮挡已画好的路线；再次点击定位即清除 */}
            {!err && geoErr && (
              <p className="mx-4 mt-2 flex items-start gap-1.5 px-1 text-[12px] leading-relaxed text-muted-foreground">
                <WarningCircle className="mt-[1px] size-3.5 shrink-0 text-sweet" weight="duotone" />
                <span className="min-w-0">{geoErr}</span>
              </p>
            )}

            {/* 操作：用我的位置重规划 + 让数字人语音指路 */}
            <div className="mx-4 mb-[max(20px,env(safe-area-inset-bottom))] mt-3 flex gap-2.5">
              <button
                onClick={useMyLocation}
                disabled={locating}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-2xl border border-primary/50 bg-primary/[0.04] py-3 text-[14px] font-medium text-primary transition duration-200 ease-[var(--ease-out)] hover:bg-primary/[0.08] active:scale-[0.98] disabled:opacity-60"
              >
                {locating ? <CircleNotch className="size-4 animate-spin" /> : <Crosshair className="size-4" />}
                {locating ? '定位中…' : '从我的位置出发'}
              </button>
              <button
                onClick={() => { onAsk(`${target.pointName}怎么走`); onOpenChange(false) }}
                className="flex flex-1 items-center justify-center gap-1.5 rounded-2xl bg-primary py-3 text-[14px] font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition duration-200 ease-[var(--ease-out)] hover:shadow-xl active:scale-[0.98]"
              >
                <NavigationArrow className="size-4" weight="duotone" /> 语音指路
              </button>
            </div>
          </div>
        )}
      </DrawerContent>
    </Drawer>
  )
}
