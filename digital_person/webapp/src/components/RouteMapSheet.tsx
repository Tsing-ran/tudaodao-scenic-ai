import { useEffect, useRef, useState } from 'react'
import { Compass, Camera, ChatCircleDots, CircleNotch, Clock, PersonSimpleWalk, CheckCircle, Sparkle, SealCheck, Question, ArrowsClockwise, MapPin, CaretUp, CaretDown, Minus, FilmSlate, X } from '@phosphor-icons/react'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer'
import { loadAMap, amapConfigured } from '@/lib/amap'
import { CROWD_META, LEVEL_TO_CROWD } from '@/lib/routeData'
import type { ScenicRoute, RouteStop, Crowd } from '@/lib/routeData'
import * as api from '@/lib/api'
import { cn } from '@/lib/utils'

/* eslint-disable @typescript-eslint/no-explicit-any */

// 玻璃质感底：在纯色上叠白→透→暗的斜向渐变 = 立体光泽（任意底色通用），告别扁平纯色。
const gloss = (c: string) => `linear-gradient(150deg, rgba(255,255,255,.5), rgba(255,255,255,.08) 52%, rgba(0,0,0,.16)), ${c}`

// 地图上的景点 pin（自定义 HTML）：渐变玻璃质感 + 分层投影 + 白环；当前站呼吸光晕 + 主色环 + 「你在这」；到达打勾。
function pinHtml(idx: number, crowdColor: string, st: { active: boolean; done: boolean; here: boolean }): string {
  const size = st.active ? 30 : 25
  const base = st.done ? '#10b981' : crowdColor
  const label = st.done ? '✓' : String(idx + 1)
  const ringColor = st.active ? '#6d5efc' : 'rgba(255,255,255,.95)'
  const ringW = st.active ? 2.5 : 2
  const halo = st.active
    ? `<span style="position:absolute;inset:-8px;border-radius:50%;background:radial-gradient(circle,rgba(109,94,252,.5),rgba(109,94,252,0) 68%);animation:halo-breathe 2.4s ease-in-out infinite"></span>`
    : ''
  const here = st.here
    ? `<span style="position:absolute;left:50%;top:-21px;transform:translateX(-50%);white-space:nowrap;background:linear-gradient(160deg,#7c6efd,#6d5efc);color:#fff;font-size:10px;font-weight:600;letter-spacing:.02em;padding:1.5px 7px;border-radius:9px;box-shadow:0 2px 7px rgba(109,94,252,.4)">你在这</span>`
    : ''
  return `<div style="position:relative;width:${size}px;height:${size}px;font-family:-apple-system,system-ui,sans-serif;">${halo}<span style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;border-radius:50%;background:${gloss(base)};border:${ringW}px solid ${ringColor};box-shadow:0 1px 2px rgba(0,0,0,.28),0 5px 12px rgba(0,0,0,.22);color:#fff;font-size:${st.active ? 13 : 12}px;font-weight:700;text-shadow:0 1px 1.5px rgba(0,0,0,.38)">${label}</span>${here}</div>`
}

// 打卡核验结果卡（浮在地图底部）：核验中转圈；出结果显理由 + 证据信号(外观/置信/距离) + 按决策给操作。
function CheckinCard({ verifying, result, onAction, onDismiss }: {
  verifying: boolean
  result: api.CheckinResult | null
  onAction: () => void
  onDismiss: () => void
}) {
  if (!verifying && !result) return null
  const dec = result?.decision
  const ok = dec === 'confirmed'
  const Icon = ok ? SealCheck : dec === 'wrong_stop' ? ArrowsClockwise : Question
  return (
    <div className="absolute inset-x-0 bottom-0 z-40 p-3">
      <div className="rounded-2xl border bg-card/95 p-3.5 shadow-lg backdrop-blur">
        {verifying ? (
          <div className="flex items-center gap-2 text-[13px] font-medium text-muted-foreground">
            <CircleNotch className="size-4 animate-spin" /> 正在核验照片…
          </div>
        ) : result && (
          <>
            <div className="flex items-start gap-2.5">
              <span className={cn('mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full',
                ok ? 'bg-emerald-100 text-emerald-600' : 'bg-amber-100 text-amber-600')}>
                <Icon className="size-4" weight="fill" />
              </span>
              <p className="text-[13px] leading-snug text-foreground">{result.reason}</p>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-1.5 pl-[38px] text-[11px] text-muted-foreground">
              {result.matched_id && <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5"><CheckCircle className="size-3" weight="fill" /> 外观核验</span>}
              {result.confidence > 0 && <span className="rounded-full bg-muted px-2 py-0.5">置信 {Math.round(result.confidence * 100)}%</span>}
              {result.distance_m != null && <span className="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-0.5"><MapPin className="size-3" /> 距 {Math.round(result.distance_m)}m</span>}
            </div>
            <div className="mt-2.5 flex justify-end gap-2">
              {ok && <button onClick={onDismiss} className="rounded-full bg-primary px-4 py-1.5 text-[12px] font-semibold text-primary-foreground active:scale-95">好的</button>}
              {dec === 'wrong_stop' && (<>
                <button onClick={onDismiss} className="rounded-full border px-3.5 py-1.5 text-[12px] font-medium text-muted-foreground active:scale-95">取消</button>
                <button onClick={onAction} className="rounded-full bg-primary px-4 py-1.5 text-[12px] font-semibold text-primary-foreground active:scale-95">按「{result.matched_name}」打卡</button>
              </>)}
              {dec === 'uncertain' && (<>
                <button onClick={onDismiss} className="rounded-full border px-3.5 py-1.5 text-[12px] font-medium text-muted-foreground active:scale-95">取消</button>
                <button onClick={onAction} className="inline-flex items-center gap-1 rounded-full bg-primary px-4 py-1.5 text-[12px] font-semibold text-primary-foreground active:scale-95"><ArrowsClockwise className="size-3.5" /> 重拍</button>
              </>)}
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default function RouteMapSheet({ open, onOpenChange, route, visited, onAsk, onArrive, onRouteDone }: {
  open: boolean
  onOpenChange: (o: boolean) => void
  route: ScenicRoute | undefined
  visited: string[]                         // 已到访站名（trace 口径存 name 不是 id），与「足迹」抽屉同源
  onAsk: (q: string) => void
  onArrive: (stationName: string) => void   // 记录到访（触发到访/探索者徽章）
  onRouteDone: (routeId: string) => void    // 全程打卡（触发「全程打卡」徽章）
}) {
  const mapElRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<any>(null)
  const markersRef = useRef<Record<string, any>>({})
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(true)
  const [activeId, setActiveId] = useState('')
  const [hereId, setHereId] = useState('')
  const [done, setDone] = useState<string[]>([])
  const [verifying, setVerifying] = useState(false)       // 正在调 /checkin 核验
  const [result, setResult] = useState<api.CheckinResult | null>(null)
  const [liveCrowd, setLiveCrowd] = useState<Record<string, api.LiveCrowdPoi>>({})  // poi_id → 实时客流
  const [asOf, setAsOf] = useState('')                    // 实时客流快照时刻
  const fileRef = useRef<HTMLInputElement | null>(null)
  const pendingTargetRef = useRef<string>('')             // 当前要打卡的站 id

  const stops = route?.stops ?? []
  // 实时档位优先：拉到 /analytics/crowd 就按 poi_id 覆盖静态 crowd，拉不到回落静态值
  const crowdKey = (s: RouteStop): Crowd => {
    const lv = liveCrowd[s.id]?.crowd_level
    return (lv && LEVEL_TO_CROWD[lv]) || s.crowd
  }

  // 拉 POI 级实时客流（演出聚集×天气×时段）；打开时取一次 + 每 45s 刷新，关闭即停。
  useEffect(() => {
    if (!open || !route) { setLiveCrowd({}); setAsOf(''); return }
    let alive = true
    const pull = async () => {
      const d = await api.crowdLive(route.scenic)
      if (!alive || !d) return
      const m: Record<string, api.LiveCrowdPoi> = {}
      for (const p of d.attractions) m[p.poi_id] = p
      setLiveCrowd(m); setAsOf(d.as_of || '')
    }
    pull()
    const t = setInterval(pull, 45000)
    return () => { alive = false; clearInterval(t) }
  }, [open, route])

  // 初始：按已到访记录还原打卡进度，当前站 = 第一个未打卡的站（全打完则回第一站）。
  // deps 只跟 open/route：抽屉打开期间 visited 会随打卡变化，若进 deps 会重跑本 effect
  // 把用户手选的 hereId/activeId 冲掉，故只在打开那一瞬读一次。
  useEffect(() => {
    if (!open || !route) return
    const dn = route.stops.filter((s) => visited.includes(s.name)).map((s) => s.id)
    setDone(dn)
    const first = route.stops.find((s) => !dn.includes(s.id)) ?? route.stops[0]
    setActiveId(first.id); setHereId(first.id)
    setVerifying(false); setResult(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, route])

  // 建图（打开 + 有数据时）。关闭即销毁，重开重建。
  useEffect(() => {
    if (!open || !route) return
    if (!amapConfigured()) { setErr('高德 Key 未配置'); setLoading(false); return }
    let disposed = false
    setLoading(true); setErr('')
    loadAMap().then((AMapU) => {
      const AMap = AMapU as any
      if (disposed || !mapElRef.current) return
      // pitch 越大透视越夸张、fitView 越易缩太远→景点挤成一团。用温和 30° 保留 3D 立体感又不过度放大。
      const map = new AMap.Map(mapElRef.current, {
        viewMode: '3D', pitch: 30, zoom: route.zoom, center: route.center,
        mapStyle: 'amap://styles/whitesmoke', showLabel: true, rotateEnable: true, pitchEnable: true,
      })
      mapRef.current = map
      const overlays: any[] = []
      // 路线：优先用真实步行路径（沿景区步道，导航软件式：白色描边 + 主色填充 + 方向箭头），无则回退直线
      const linePath = route.walkPaths ? route.walkPaths.flat() : route.stops.map((s) => [s.lng, s.lat])
      overlays.push(new AMap.Polyline({
        path: linePath,
        isOutline: true, outlineColor: '#ffffff', borderWeight: 2.5,
        strokeColor: '#6d5efc', strokeWeight: 6, strokeOpacity: 0.95,
        lineJoin: 'round', lineCap: 'round', showDir: true, map,
      }))
      route.stops.forEach((s, i) => {
        const m = new AMap.Marker({
          position: [s.lng, s.lat], anchor: 'center', zIndex: 100 + i,
          content: pinHtml(i, CROWD_META[crowdKey(s)].dot, { active: i === 0, done: false, here: i === 0 }),
        })
        m.on('click', () => setActiveId(s.id))
        m.setMap(map)
        markersRef.current[s.id] = m
        overlays.push(m)
      })
      // 框选所有站点撑满视野：紧 padding + 较高 maxZoom；抽屉是动画展开的，故多次 fit（含延迟）
      // 确保容器拿到最终尺寸后再框一次，避免按半截尺寸缩太远 → 景点清晰分散、路线完整。
      // 框好后再额外放大 ~20%（log2(1.2)≈0.26 级），默认视野更聚焦。多次调用不累加（fitView 每次先复位）。
      const fit = () => { try { map.setFitView(overlays, true, [24, 24, 24, 24], 18) } catch { /* ignore */ } }
      map.on('complete', () => { if (!disposed) { setLoading(false); fit() } })
      fit()
      ;[280, 700, 1200].forEach((d) => setTimeout(() => { if (!disposed) fit() }, d))
      // 默认再放大 ~20%：setFitView(immediately) 实为异步、同步 setZoom 会被覆盖，故在所有 fit 落定后单独放大一次。
      // 地图可自由平移（data-vaul-no-drag），故首尾站略贴边可接受。
      setTimeout(() => {
        if (disposed || !mapRef.current) return
        try { mapRef.current.setZoom(mapRef.current.getZoom() + 0.26, true) } catch { /* ignore */ }
        setLoading(false)
      }, 1450)
    }).catch((e) => { if (!disposed) { setErr(e?.message || '地图加载失败'); setLoading(false) } })
    return () => {
      disposed = true
      markersRef.current = {}
      if (mapRef.current) { try { mapRef.current.destroy() } catch { /* ignore */ } mapRef.current = null }
    }
  }, [open, route])

  // active / done / here 变化 → 同步 pin 外观 + 地图平移到当前站
  useEffect(() => {
    if (!mapRef.current || !route) return
    route.stops.forEach((s, i) => {
      const m = markersRef.current[s.id]
      if (m) m.setContent(pinHtml(i, CROWD_META[crowdKey(s)].dot, {
        active: s.id === activeId, done: done.includes(s.id), here: s.id === hereId,
      }))
    })
    const am = markersRef.current[activeId]
    if (am) { try { mapRef.current.panTo(am.getPosition()) } catch { /* ignore */ } }
  }, [activeId, hereId, done, route, liveCrowd])

  // 打卡成功：标记到达 → 记录到访（徽章）→ 你在这前进到下一站 → 全程走完则记路线完成（徽章）
  const checkIn = (id: string) => {
    const st = stops.find((s) => s.id === id)
    if (st) onArrive(st.name)                       // 记录到访 → 解锁到访/探索者徽章
    setDone((d) => (d.includes(id) ? d : [...d, id]))
    // 判断是否全程走完（用当前 done + 本次 id 推算，避免读到滞后的 state）
    const willDone = new Set([...done, id])
    if (route && willDone.size === stops.length && stops.length > 0) onRouteDone(route.scenic)
    const idx = stops.findIndex((s) => s.id === id)
    const next = stops[idx + 1]
    if (next) { setHereId(next.id); setActiveId(next.id) }
  }

  // 拍照打卡：开相机 → /checkin 闭集核验 → 按决策处理（confirmed 直接打卡 / wrong_stop 建议 / uncertain 再拍）
  const startCapture = (targetId: string) => { pendingTargetRef.current = targetId; setResult(null); fileRef.current?.click() }
  const onFile = async (file: File) => {
    const target = pendingTargetRef.current
    if (!target || !route) return
    setVerifying(true); setResult(null)
    try {
      const dataUrl: string = await new Promise((res, rej) => {
        const r = new FileReader(); r.onload = () => res(r.result as string); r.onerror = rej; r.readAsDataURL(file)
      })
      const b64 = dataUrl.slice(dataUrl.indexOf(',') + 1)
      const fmt = /data:image\/(\w+);/.exec(dataUrl)?.[1] || 'jpeg'
      const cands = route.stops.map((s) => ({ id: s.id, name: s.name, lng: s.lng, lat: s.lat }))
      const { ok, data } = await api.checkin({ scenic: route.scenic, b64, fmt, targetId: target, candidates: cands })
      setVerifying(false)
      if (!ok) { setResult({ decision: 'uncertain', confidence: 0, evidence: [], reason: '核验服务暂时不可用，请稍后再试。' }); return }
      setResult(data)
      if (data.decision === 'confirmed' && data.matched_id) checkIn(data.matched_id)  // 确认→直接打卡推进
    } catch {
      setVerifying(false)
      setResult({ decision: 'uncertain', confidence: 0, evidence: [], reason: '核验失败，请重试。' })
    }
  }

  const askDetail = (s: RouteStop) => { onAsk(`请讲讲${s.name}`); onOpenChange(false) }

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="mx-auto flex max-h-[94vh] max-w-[480px] flex-col">
        <DrawerHeader className="relative pb-1">
          <DrawerClose aria-label="关闭" className="absolute right-3 top-2 z-10 flex size-8 items-center justify-center rounded-full bg-muted text-muted-foreground transition active:scale-90">
            <X className="size-4" />
          </DrawerClose>
          <DrawerTitle className="flex items-center gap-2.5 pr-9">
            <span className="flex size-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Compass className="size-[18px]" weight="duotone" />
            </span>
            {route ? route.title : '专属路线'}
            {route && <span className="ml-auto text-[12px] font-normal text-muted-foreground">{stops.length} 站 · 约 {Math.round(route.totalMin / 60 * 10) / 10} 小时</span>}
          </DrawerTitle>
        </DrawerHeader>

        {!route ? (
          <div className="px-4 pb-8 pt-2 text-[14px] leading-relaxed text-muted-foreground">
            该景区的地图路线即将上线，当前先用「跟我游」的清单路线哦。
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col">
            {/* 上：高德 3D 地图 */}
            {/* data-vaul-no-drag：在地图上双指缩放/拖动时不被抽屉误判为下滑关闭（Vaul shouldDrag 见此属性即跳过） */}
            <div data-vaul-no-drag className="relative mx-4 shrink-0 overflow-hidden rounded-2xl border bg-muted" style={{ height: '40vh' }}>
              <div ref={mapElRef} className="size-full" />
              {loading && !err && (
                <div className="absolute inset-0 flex items-center justify-center gap-2 bg-background/60 text-[13px] text-muted-foreground backdrop-blur-sm">
                  <CircleNotch className="size-4 animate-spin" /> 地图加载中…
                </div>
              )}
              {err && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-6 text-center">
                  <p className="text-[13px] font-medium text-foreground">地图加载失败</p>
                  <p className="text-[12px] leading-relaxed text-muted-foreground">{err}</p>
                </div>
              )}
              <CheckinCard
                verifying={verifying}
                result={result}
                onDismiss={() => setResult(null)}
                onAction={() => {
                  if (result?.decision === 'wrong_stop' && result.matched_id) { checkIn(result.matched_id); setResult(null) }
                  else if (result?.decision === 'uncertain') { setResult(null); startCapture(pendingTargetRef.current) }
                }}
              />
            </div>
            {/* 拍照打卡相机/相册输入（隐藏；capture=environment 在手机直接开后置相机） */}
            <input
              ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = '' }}
            />

            {/* 下：联动旅程线（点站 ↔ 地图 pin 高亮平移） */}
            <div className="mt-3 min-h-0 flex-1 overflow-y-auto px-4 pb-[max(20px,env(safe-area-inset-bottom))]">
              {asOf && (
                <div className="mb-2 flex items-center gap-1.5 px-1 text-[11px] text-muted-foreground">
                  <span className="relative flex size-1.5">
                    <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex size-1.5 rounded-full bg-emerald-500" />
                  </span>
                  实时客流 · {asOf.slice(11)} 更新 · 随演出/天气/时段变化
                </div>
              )}
              {stops.map((s, i) => {
                const isActive = s.id === activeId
                const isDone = done.includes(s.id)
                const isHere = s.id === hereId
                const live = liveCrowd[s.id]
                const cm = CROWD_META[crowdKey(s)]
                return (
                  <div key={s.id}>
                    <button
                      onClick={() => setActiveId(s.id)}
                      className={cn(
                        'flex w-full items-start gap-3 rounded-2xl border px-3 py-2.5 text-left transition duration-200',
                        isActive ? 'border-primary/40 bg-primary/[0.05] shadow-sm' : 'border-transparent hover:bg-accent/40',
                      )}
                    >
                      <span
                        className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full text-[13px] font-bold text-white"
                        style={{
                          background: gloss(isDone ? '#10b981' : cm.dot),
                          boxShadow: 'inset 0 1px 0 rgba(255,255,255,.35), 0 1px 2px rgba(0,0,0,.18)',
                          textShadow: '0 1px 1px rgba(0,0,0,.3)',
                        }}
                      >
                        {isDone ? <CheckCircle className="size-4" weight="fill" /> : i + 1}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-2">
                          <span className={cn('truncate text-[15px] font-semibold', isDone && 'text-muted-foreground line-through')}>{s.name}</span>
                          {isHere && <span className="shrink-0 rounded-full bg-primary px-1.5 py-0.5 text-[10px] font-semibold text-primary-foreground">你在这</span>}
                        </span>
                        <span className="mt-0.5 flex flex-wrap items-center gap-x-2.5 gap-y-0.5 text-[11px] text-muted-foreground">
                          <span className={cn('inline-flex items-center gap-1 font-medium', cm.color)}>
                            <span className="size-1.5 rounded-full" style={{ background: cm.dot }} /> {cm.label}
                            {live && (live.trend === '上升'
                              ? <CaretUp className="size-3 text-orange-500" weight="bold" />
                              : live.trend === '下降'
                                ? <CaretDown className="size-3 text-emerald-500" weight="bold" />
                                : <Minus className="size-3 opacity-60" weight="bold" />)}
                          </span>
                          <span className="inline-flex items-center gap-0.5"><Clock className="size-3" /> 停留{s.stayMin}分</span>
                          {s.indoor && <span className="text-primary">室内</span>}
                          {live && (live.in_show || (live.next_show && live.minutes_to_show != null && live.minutes_to_show >= 0 && live.minutes_to_show <= 60)) && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-1.5 py-0.5 font-medium text-primary">
                              <FilmSlate className="size-3" weight="duotone" />
                              {live.in_show ? '演出中' : `${live.next_show} 演出·${live.minutes_to_show}分后`}
                            </span>
                          )}
                        </span>
                        <span className="mt-1 block text-[12.5px] leading-snug text-foreground/80">{s.reason}</span>
                        {isActive && (
                          <span className="mt-2 flex flex-wrap gap-2">
                            <button
                              onClick={(e) => { e.stopPropagation(); askDetail(s) }}
                              className="inline-flex items-center gap-1 rounded-full bg-primary px-3 py-1.5 text-[12px] font-semibold text-primary-foreground shadow-sm shadow-primary/25 active:scale-95"
                            >
                              <ChatCircleDots className="size-3.5" weight="duotone" /> 问详情
                            </button>
                            {!isDone && (
                              <button
                                onClick={(e) => { e.stopPropagation(); checkIn(s.id) }}
                                className="inline-flex items-center gap-1 rounded-full bg-sweet/15 px-3 py-1.5 text-[12px] font-semibold text-sweet transition hover:bg-sweet/25 active:scale-95"
                              >
                                <CheckCircle className="size-3.5" weight="duotone" /> 我已到达
                              </button>
                            )}
                            {!isDone && (
                              <button
                                onClick={(e) => { e.stopPropagation(); startCapture(s.id) }}
                                disabled={verifying}
                                className="inline-flex items-center gap-1 rounded-full border px-3 py-1.5 text-[12px] font-semibold text-foreground transition hover:border-primary/30 hover:text-primary active:scale-95 disabled:opacity-50"
                              >
                                <Camera className="size-3.5" /> 拍照打卡
                              </button>
                            )}
                          </span>
                        )}
                      </span>
                    </button>
                    {i < stops.length - 1 && (
                      <div className="ml-[26px] flex items-center gap-1.5 py-1 text-[11px] text-muted-foreground">
                        <PersonSimpleWalk className="size-3.5" weight="duotone" />
                        <span className="h-px w-4 bg-border" /> 步行 {s.walkMin} 分
                      </div>
                    )}
                  </div>
                )
              })}
              {done.length === stops.length && stops.length > 0 && (
                <div className="mt-3 flex items-center justify-center gap-2 rounded-2xl border border-primary/20 bg-primary/[0.05] px-4 py-3 text-[13px] font-medium text-primary">
                  <Sparkle className="size-4" weight="duotone" /> 全程走完啦，去「足迹」生成你的电子游记 →
                </div>
              )}
            </div>
          </div>
        )}
      </DrawerContent>
    </Drawer>
  )
}
