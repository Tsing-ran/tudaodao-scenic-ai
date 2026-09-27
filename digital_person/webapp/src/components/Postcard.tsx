import { useEffect, useRef, useState } from 'react'
import { X, DownloadSimple, CircleNotch, ShareNetwork } from '@phosphor-icons/react'
import type { Trace } from '@/lib/trace'
import { badges } from '@/lib/trace'
import { tripBlessing } from '@/lib/personalize'
import type { Lang } from '@/lib/i18n'

interface Props {
  open: boolean; onClose: () => void
  scenic: string; scenicName: string
  guideName: string
  groupType: string; lang: Lang
  trace: Trace
}

// 景区祝福语（明信片落款；未配置景区走通用兜底）
const BLESS: Record<string, string> = {
  lingshan: '愿灵山的钟声与禅意，伴你一路平安喜乐。',
  nihuawan: '愿拈花一笑的从容，常驻你心间。',
  xihu: '愿西湖的山色空蒙，长留你记忆里。',
  huangshan: '愿黄山的云海与劲松，赠你向上的力量。',
  gugong: '愿故宫的红墙金瓦，为你收藏这段好时光。',
}

const W = 720, H = 1280
const SCALE = 2          // 2× 超采样：物理画布 1440×2560，导出高清（逻辑坐标仍按 720×1280）
// 实体明信片配色（固定雅致配色，比跟随换肤更高级、跨景区不冲突）
const PAPER = '#f3eee4'        // 暖白相纸（白边）

// ⚠️ 现有 public/postcard/*.jpg 是万相生成的"伪明信片插画"，自带 AIGC 乱码标题、非纯风景，
// 叠前端文字会打架 → 暂用程序化水墨兜底（干净、按景区分色调）。
// 窗口① 用 gen_postcard_bg.py 出"纯风景无文字"图后，将此开关改 true 即用真景区图。
const USE_AIGC_BG = false

// 程序化水墨色板（按景区分暖/青/冷/金，给 8 景区辨识度）
type Palette = { sky: [string, string, string, string]; sun: string; hills: [string, string, string]; water: string }
const PALETTES: Record<string, Palette> = {
  warm: { sky: ['#f6e6cf', '#e4ddc7', '#cdd6cf', '#b6c4bb'], sun: 'rgba(244,198,150,0.85)', hills: ['rgba(150,176,168,0.55)', 'rgba(115,150,140,0.70)', 'rgba(86,122,112,0.85)'], water: 'rgba(120,140,134,0.30)' },
  cyan: { sky: ['#e8f0ec', '#d6e4de', '#c2d6d2', '#a8c6c2'], sun: 'rgba(230,224,198,0.70)', hills: ['rgba(140,180,175,0.50)', 'rgba(100,150,148,0.68)', 'rgba(70,118,116,0.85)'], water: 'rgba(110,148,144,0.30)' },
  cool: { sky: ['#e6e9ee', '#d2d8e0', '#bcc6d2', '#a4b4c4'], sun: 'rgba(220,222,230,0.62)', hills: ['rgba(150,164,182,0.55)', 'rgba(108,124,148,0.70)', 'rgba(74,90,116,0.86)'], water: 'rgba(110,124,146,0.30)' },
  gold: { sky: ['#f7e8d2', '#efd9b8', '#e6c79c', '#d6b182'], sun: 'rgba(232,150,90,0.82)', hills: ['rgba(178,150,118,0.55)', 'rgba(150,116,80,0.72)', 'rgba(120,86,56,0.86)'], water: 'rgba(150,124,92,0.30)' },
}
const SCENIC_PALETTE: Record<string, keyof typeof PALETTES> = {
  lingshan: 'warm', nihuawan: 'warm', bingmayong: 'warm', mogaoku: 'gold',
  xihu: 'cyan', zhangjiajie: 'cyan', huangshan: 'cool', gugong: 'gold',
}
const scenicPostcardSrc = (scenic: string) => `/postcard/${scenic}.jpg${scenic === 'lingshan' ? '?v=20260702' : ''}`

export default function Postcard({ open, onClose, scenic, scenicName, guideName, groupType, lang, trace }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [drawing, setDrawing] = useState(true)
  const [dataUrl, setDataUrl] = useState('')

  useEffect(() => {
    if (!open) return
    setDrawing(true); setDataUrl('')
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')!
    const bg = new Image()
    bg.crossOrigin = 'anonymous'
    bg.onload = () => { paint(ctx, bg); finish() }
    bg.onerror = () => { paint(ctx, null); finish() }
    bg.src = scenicPostcardSrc(scenic)
    function finish() {
      try { setDataUrl(canvas!.toDataURL('image/png')) } catch { /* tainted */ }
      setDrawing(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, scenic, scenicName, guideName, groupType, lang, trace])

  // 满版完整风景明信片：实体白边 + 整图铺满(同比例零裁切，主体不被斩断) + 底部影院渐变信息区 + 邮戳点缀
  function paint(ctx: CanvasRenderingContext2D, bg: HTMLImageElement | null) {
    ctx.setTransform(SCALE, 0, 0, SCALE, 0, 0)              // 2× 超采样，逻辑坐标不变
    const EDGE = 26                                          // 实体相纸白边
    const IMG = { x: EDGE, y: EDGE, w: W - EDGE * 2, h: H - EDGE * 2 }
    const GOLD = '#e6c08a'                                   // 图上暖金点缀（朱墨在深图上偏暗，改暖金更亮）
    const now = new Date()
    const date = `${now.getFullYear()}.${String(now.getMonth() + 1).padStart(2, '0')}.${String(now.getDate()).padStart(2, '0')}`

    // ① 白边相纸底
    ctx.fillStyle = PAPER
    ctx.fillRect(0, 0, W, H)

    // ② 风景图满版铺入白边内（IMG 与原图近乎同比例 → cover 几乎零裁切，风景完整）
    ctx.save()
    roundRect(ctx, IMG.x, IMG.y, IMG.w, IMG.h, 20)
    ctx.clip()
    if (bg && USE_AIGC_BG) {
      const r = Math.max(IMG.w / bg.width, IMG.h / bg.height)
      const w = bg.width * r, h = bg.height * r
      ctx.drawImage(bg, IMG.x + (IMG.w - w) / 2, IMG.y + (IMG.h - h) / 2, w, h)
    } else {
      // 程序化动漫风景（按景区分色调 + 标志性地标剪影），干净无乱码、不依赖图素材
      drawLandscape(ctx, IMG.x, IMG.y, IMG.w, IMG.h, PALETTES[SCENIC_PALETTE[scenic] || 'cyan'], scenic)
    }
    // 顶部轻渐变（托住品牌字标/邮戳）
    const tg = ctx.createLinearGradient(0, IMG.y, 0, IMG.y + 200)
    tg.addColorStop(0, 'rgba(16,14,22,0.40)'); tg.addColorStop(1, 'rgba(16,14,22,0)')
    ctx.fillStyle = tg; ctx.fillRect(IMG.x, IMG.y, IMG.w, 200)
    // 底部影院渐变（托住信息区文字，落在图的水面/前景低信息区）
    const bgGrad = ctx.createLinearGradient(0, IMG.y + IMG.h - 560, 0, IMG.y + IMG.h)
    bgGrad.addColorStop(0, 'rgba(16,14,22,0)')
    bgGrad.addColorStop(0.5, 'rgba(16,14,22,0.55)')
    bgGrad.addColorStop(1, 'rgba(16,14,22,0.90)')
    ctx.fillStyle = bgGrad; ctx.fillRect(IMG.x, IMG.y + IMG.h - 560, IMG.w, 560)

    ctx.textBaseline = 'alphabetic'
    const tx = IMG.x + 38, rx = IMG.x + IMG.w - 38

    // ③ 顶部：品牌小字标（左）+ 邮戳（右上，盖在天空留白）
    ctx.textAlign = 'left'
    ctx.fillStyle = 'rgba(255,255,255,0.82)'
    ctx.font = '600 25px system-ui, sans-serif'
    ctx.fillText('P O S T C A R D · 途叨叨', tx, IMG.y + 56)
    drawPostmark(ctx, rx - 56, IMG.y + 104, 56, now)

    // ④ 底部信息区（自底向上累加：内容多寡都不碰撞、都锚在底部渐变内）
    // 寄语优先用本程足迹×画像的个性化收尾（导游"收尾关怀"），无足迹则回退景区通用祝福
    const blessing = tripBlessing(trace.visited, groupType, guideName, scenicName, lang) || BLESS[scenic] || '愿这段旅程，成为你心里的好风景。'
    const earnedCount = badges(trace).filter((b) => b.earned).length
    const statBits = [
      trace.visited.length && `到访 ${trace.visited.length} 处`,
      trace.asks && `提问 ${trace.asks} 次`,
      earnedCount && `解锁 ${earnedCount} 枚徽章`,
    ].filter(Boolean) as string[]

    let y = IMG.y + IMG.h - 52
    // 落款（最底，右对齐，暖金斜体）
    ctx.textAlign = 'right'
    ctx.fillStyle = GOLD
    ctx.font = 'italic 600 27px Georgia, "Songti SC", serif'
    ctx.fillText(`您的专属AI导览 敬上 · ${date}`, rx, y)
    ctx.textAlign = 'left'
    y -= 50
    // 统计
    if (statBits.length) {
      ctx.fillStyle = 'rgba(255,255,255,0.72)'
      ctx.font = '400 25px system-ui, sans-serif'
      ctx.fillText(statBits.join('　·　'), tx, y); y -= 44
    }
    // 途经（超宽省略）
    if (trace.visited.length) {
      ctx.fillStyle = 'rgba(255,255,255,0.72)'
      ctx.font = '500 26px system-ui, sans-serif'
      ctx.fillText('途经　' + ellipsize(ctx, trace.visited, ' · ', IMG.w - 76), tx, y); y -= 50
    }
    // 祝福语（情感主角，衬线斜体，自下而上排）
    ctx.fillStyle = 'rgba(255,255,255,0.96)'
    ctx.font = 'italic 500 37px Georgia, "Songti SC", serif'
    const blessLines = layoutLines(ctx, blessing, IMG.w - 76)
    y -= 4
    for (let i = blessLines.length - 1; i >= 0; i--) { ctx.fillText(blessLines[i], tx, y); y -= 54 }
    y -= 18
    // 暖金短线
    ctx.fillStyle = GOLD
    ctx.fillRect(tx, y, 64, 4); y -= 26
    // 主标题（白，黑体粗）
    ctx.fillStyle = '#fff'
    ctx.font = '800 78px system-ui, sans-serif'
    ctx.fillText(scenicName, tx, y)
    ctx.restore()

    // ⑤ 白边内描边（实体相纸微立体）
    roundRect(ctx, IMG.x, IMG.y, IMG.w, IMG.h, 20)
    ctx.lineWidth = 2; ctx.strokeStyle = 'rgba(0,0,0,0.12)'; ctx.stroke()
  }

  const download = () => {
    if (!dataUrl) return
    const a = document.createElement('a')
    a.href = dataUrl; a.download = `途叨叨旅记_${scenicName}.png`; a.click()
  }

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/80 px-5 backdrop-blur-sm">
      <button onClick={onClose} className="absolute right-4 top-[max(16px,env(safe-area-inset-top))] flex size-10 items-center justify-center rounded-full bg-white/15 text-white active:scale-90">
        <X className="size-5" />
      </button>

      <div className="relative w-full max-w-[300px] overflow-hidden rounded-3xl shadow-2xl">
        <canvas ref={canvasRef} width={W * SCALE} height={H * SCALE} className="block h-auto w-full" />
        {drawing && (
          <div className="absolute inset-0 flex items-center justify-center bg-black/40 text-white">
            <CircleNotch className="size-6 animate-spin" />
          </div>
        )}
      </div>

      <div className="mt-5 flex w-full max-w-[300px] gap-2.5">
        <button
          onClick={download} disabled={!dataUrl}
          className="flex flex-1 items-center justify-center gap-2 rounded-2xl bg-white py-3.5 text-[15px] font-semibold text-slate-900 transition active:scale-[0.98] disabled:opacity-50"
        >
          <DownloadSimple className="size-4" /> 保存明信片
        </button>
        <button onClick={onClose} className="flex items-center justify-center gap-2 rounded-2xl bg-white/15 px-5 text-[15px] font-medium text-white active:scale-95">
          <ShareNetwork className="size-4" /> 完成
        </button>
      </div>
      <p className="mt-3 text-center text-[12px] text-white/60">背景由通义万相 AIGC 生成 · 长按可分享</p>
    </div>
  )
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath()
  ctx.moveTo(x + r, y)
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

// 程序化动漫风氛围风景（无图兜底 / 主背景）：晨昏天空 + 太阳光晕 + 云层 + 五层雾山 + 景区地标剪影 + 水面倒影 + 飞鸟
function drawLandscape(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, pal: Palette, scenic: string) {
  const sunX = x + w * 0.32, sunY = y + h * 0.24, waterTop = y + h * 0.80
  // ① 天空渐变
  const sky = ctx.createLinearGradient(0, y, 0, waterTop)
  sky.addColorStop(0, pal.sky[0]); sky.addColorStop(0.4, pal.sky[1])
  sky.addColorStop(0.72, pal.sky[2]); sky.addColorStop(1, pal.sky[3])
  ctx.fillStyle = sky; ctx.fillRect(x, y, w, h)
  // ② 太阳光晕（径向）+ 日轮
  const halo = ctx.createRadialGradient(sunX, sunY, 0, sunX, sunY, 200)
  halo.addColorStop(0, pal.sun); halo.addColorStop(0.4, withAlpha(pal.sun, 0.28)); halo.addColorStop(1, withAlpha(pal.sun, 0))
  ctx.fillStyle = halo; ctx.fillRect(x, y, w, h * 0.6)
  ctx.fillStyle = pal.sun
  ctx.beginPath(); ctx.arc(sunX, sunY, 50, 0, Math.PI * 2); ctx.fill()
  // ③ 云层（多圆叠加成蓬松云团，避开太阳，近地平偏舒展）
  ctx.save(); ctx.beginPath(); ctx.rect(x, y, w, h * 0.5); ctx.clip()
  const clouds = [
    { cx: 0.20, cy: 0.13, s: 1.0, a: 0.5 }, { cx: 0.80, cy: 0.10, s: 0.8, a: 0.42 },
    { cx: 0.30, cy: 0.40, s: 1.1, a: 0.3 }, { cx: 0.88, cy: 0.36, s: 0.7, a: 0.28 },
  ]
  for (const c of clouds) {
    ctx.fillStyle = `rgba(255,255,255,${c.a})`
    const bx = x + w * c.cx, by = y + h * c.cy, s = c.s
    // 5 个不同大小的圆叠成蓬松团
    const puffs = [[0, 0, 34], [38, 4, 26], [-36, 6, 24], [18, -12, 22], [-16, -10, 20]]
    for (const [dx, dy, r] of puffs) {
      ctx.beginPath(); ctx.arc(bx + dx * s, by + dy * s, r * s, 0, Math.PI * 2); ctx.fill()
    }
  }
  ctx.restore()
  // ④ 五层雾山（由远及近加深、起伏加大；每层顶部叠天空色雾气过渡）
  const layers = [
    { base: 0.44, amp: 22, freq: 0.013, phase: 1, col: blend(pal.hills[0], pal.sky[2], 0.5) },
    { base: 0.52, amp: 30, freq: 0.011, phase: 3, col: pal.hills[0] },
    { base: 0.60, amp: 40, freq: 0.009, phase: 0, col: blend(pal.hills[0], pal.hills[1], 0.5) },
    { base: 0.68, amp: 52, freq: 0.0075, phase: 4, col: pal.hills[1] },
    { base: 0.76, amp: 64, freq: 0.006, phase: 2, col: pal.hills[2] },
  ]
  for (const L of layers) {
    const topY = y + h * L.base - L.amp
    ctx.fillStyle = L.col
    ctx.beginPath(); ctx.moveTo(x, y + h)
    for (let px = 0; px <= w; px += 6) {
      ctx.lineTo(x + px, y + h * L.base + Math.sin(px * L.freq + L.phase) * L.amp + Math.sin(px * L.freq * 2.7) * L.amp * 0.3)
    }
    ctx.lineTo(x + w, y + h); ctx.closePath(); ctx.fill()
    // 山脚雾气（天空色横向渐变，制造空气透视）
    const fog = ctx.createLinearGradient(0, topY, 0, topY + 70)
    fog.addColorStop(0, withAlpha(pal.sky[2], 0.55)); fog.addColorStop(1, withAlpha(pal.sky[2], 0))
    ctx.fillStyle = fog; ctx.fillRect(x, topY, w, 70)
  }
  // ④.5 景区标志性地标剪影（立于右侧雾山脊、文字区之上，逆光剪影 → 一眼认出是哪个景区）
  const lm = LANDMARKS[scenic]
  if (lm) {
    const silhouette = blend(pal.hills[2], '#20222c', 0.42)
    lm(ctx, x + w * 0.66, y + h * 0.63, w / 720, silhouette)
  }

  // ⑤ 水面 + 太阳竖向倒影光带 + 波光
  ctx.fillStyle = pal.water; ctx.fillRect(x, waterTop, w, y + h - waterTop)
  const refl = ctx.createLinearGradient(sunX, waterTop, sunX, y + h)
  refl.addColorStop(0, withAlpha(pal.sun, 0.5)); refl.addColorStop(1, withAlpha(pal.sun, 0))
  ctx.fillStyle = refl
  ctx.beginPath(); ctx.moveTo(sunX - 34, waterTop); ctx.lineTo(sunX + 34, waterTop)
  ctx.lineTo(sunX + 70, y + h); ctx.lineTo(sunX - 70, y + h); ctx.closePath(); ctx.fill()
  ctx.strokeStyle = 'rgba(255,255,255,0.32)'; ctx.lineWidth = 2
  for (let i = 0; i < 5; i++) {
    const ly = waterTop + (y + h - waterTop) * (0.18 + i * 0.18)
    ctx.beginPath(); ctx.moveTo(x + w * (0.2 + (i % 2) * 0.1), ly); ctx.lineTo(x + w * (0.8 - (i % 2) * 0.1), ly); ctx.stroke()
  }
  // ⑥ 远处飞鸟（极简 v 形剪影）
  ctx.strokeStyle = withAlpha(pal.hills[2], 0.7); ctx.lineWidth = 2.5
  const birds = [[0.3, 0.2], [0.37, 0.17], [0.44, 0.21]]
  for (const [bx, by] of birds) {
    const px = x + w * bx, py = y + h * by, s = 11
    ctx.beginPath(); ctx.moveTo(px - s, py); ctx.quadraticCurveTo(px, py - 7, px, py); ctx.quadraticCurveTo(px, py - 7, px + s, py); ctx.stroke()
  }
}

// 景区标志性地标剪影（cx=中心x, gy=底部y, s=缩放, col=逆光剪影色）——让每个景区一眼可辨
type Landmark = (ctx: CanvasRenderingContext2D, cx: number, gy: number, s: number, col: string) => void

// 中式飞檐屋顶（凹曲屋面 + 两端起翘的檐角，故宫用）
function flyingRoof(ctx: CanvasRenderingContext2D, cx: number, by: number, hw: number, hh: number, col: string) {
  ctx.fillStyle = col
  ctx.beginPath()
  ctx.moveTo(cx - hw, by - hh * 0.28)                                  // 左檐角起翘尖
  ctx.quadraticCurveTo(cx - hw + 6 * (hw / 100), by, cx - hw + 16 * (hw / 100), by)
  ctx.quadraticCurveTo(cx - hw * 0.5, by - hh * 0.42, cx - hw * 0.22, by - hh)  // 凹曲屋面 → 屋脊
  ctx.lineTo(cx + hw * 0.22, by - hh)                                  // 屋脊
  ctx.quadraticCurveTo(cx + hw * 0.5, by - hh * 0.42, cx + hw - 16 * (hw / 100), by)
  ctx.quadraticCurveTo(cx + hw - 6 * (hw / 100), by, cx + hw, by - hh * 0.28)   // 右檐角起翘
  ctx.closePath(); ctx.fill()
}
// 多层塔（雷峰塔/九层楼/禅塔通用，tiers 层数 / w0 底层半宽 / taper 收窄）
function pagoda(ctx: CanvasRenderingContext2D, cx: number, gy: number, s: number, col: string, tiers: number, w0: number, th: number) {
  ctx.fillStyle = col
  for (let i = 0; i < tiers; i++) {
    const ty = gy - (i + 1) * th * s, hw = w0 * (1 - i * 0.11) * s
    ctx.fillRect(cx - hw, ty, hw * 2, th * s)                          // 塔身
    ctx.fillRect(cx - hw - 9 * s, ty, hw * 2 + 18 * s, 8 * s)          // 出檐
  }
  const topY = gy - tiers * th * s                                     // 塔刹
  ctx.beginPath(); ctx.moveTo(cx - 9 * s, topY); ctx.lineTo(cx, topY - 30 * s); ctx.lineTo(cx + 9 * s, topY); ctx.closePath(); ctx.fill()
  ctx.fillRect(cx - w0 * 1.15 * s, gy, w0 * 2.3 * s, 12 * s)           // 基座
}

const LANDMARKS: Record<string, Landmark> = {
  // 灵山大佛：头光 + 立佛 + 莲座
  lingshan(ctx, cx, gy, s, col) {
    ctx.fillStyle = col; ctx.strokeStyle = col
    const topY = gy - 250 * s
    ctx.lineWidth = 5 * s
    ctx.beginPath(); ctx.arc(cx, topY + 38 * s, 48 * s, 0, Math.PI * 2); ctx.stroke()   // 头光
    ctx.beginPath(); ctx.arc(cx, topY + 16 * s, 10 * s, 0, Math.PI * 2); ctx.fill()     // 肉髻
    ctx.beginPath(); ctx.ellipse(cx, topY + 40 * s, 24 * s, 28 * s, 0, 0, Math.PI * 2); ctx.fill() // 头
    ctx.beginPath()                                                                     // 袈裟身
    ctx.moveTo(cx - 28 * s, topY + 64 * s)
    ctx.quadraticCurveTo(cx - 66 * s, gy - 54 * s, cx - 78 * s, gy)
    ctx.lineTo(cx + 78 * s, gy)
    ctx.quadraticCurveTo(cx + 66 * s, gy - 54 * s, cx + 28 * s, topY + 64 * s)
    ctx.closePath(); ctx.fill()
    ctx.beginPath(); ctx.ellipse(cx, gy, 92 * s, 18 * s, 0, 0, Math.PI * 2); ctx.fill() // 莲座
  },
  // 拈花湾：秀气禅意五重塔
  nihuawan(ctx, cx, gy, s, col) { pagoda(ctx, cx, gy, s, col, 5, 36, 34) },
  // 西湖：雷峰塔 + 旁边断桥拱
  xihu(ctx, cx, gy, s, col) {
    pagoda(ctx, cx + 14 * s, gy, s, col, 5, 50, 38)
    ctx.fillStyle = col                                                                 // 断桥（左侧半拱）
    ctx.beginPath()
    ctx.moveTo(cx - 150 * s, gy); ctx.quadraticCurveTo(cx - 96 * s, gy - 56 * s, cx - 44 * s, gy)
    ctx.lineTo(cx - 44 * s, gy + 8 * s); ctx.lineTo(cx - 150 * s, gy + 8 * s); ctx.closePath(); ctx.fill()
  },
  // 黄山：奇峰 + 迎客松（标志性右伸平展树冠）
  huangshan(ctx, cx, gy, s, col) {
    ctx.fillStyle = col; ctx.strokeStyle = col
    ctx.beginPath(); ctx.moveTo(cx - 130 * s, gy); ctx.lineTo(cx - 64 * s, gy - 200 * s); ctx.lineTo(cx - 4 * s, gy); ctx.closePath(); ctx.fill()
    ctx.beginPath(); ctx.moveTo(cx + 36 * s, gy); ctx.lineTo(cx + 96 * s, gy - 150 * s); ctx.lineTo(cx + 150 * s, gy); ctx.closePath(); ctx.fill()
    ctx.lineWidth = 7 * s                                                                // 松干
    ctx.beginPath(); ctx.moveTo(cx, gy); ctx.lineTo(cx, gy - 110 * s); ctx.stroke()
    ctx.lineWidth = 4 * s                                                                // 向右平展的主枝
    ctx.beginPath(); ctx.moveTo(cx, gy - 104 * s); ctx.lineTo(cx + 96 * s, gy - 124 * s); ctx.stroke()
    // 标志性扁平华盖（横向多层叠加，越往右越收，伞状平展）
    ctx.beginPath(); ctx.ellipse(cx + 52 * s, gy - 126 * s, 60 * s, 8 * s, -0.07, 0, Math.PI * 2); ctx.fill()
    ctx.beginPath(); ctx.ellipse(cx + 44 * s, gy - 116 * s, 48 * s, 6 * s, -0.05, 0, Math.PI * 2); ctx.fill()
    ctx.beginPath(); ctx.ellipse(cx - 6 * s, gy - 108 * s, 20 * s, 7 * s, 0, 0, Math.PI * 2); ctx.fill() // 干顶小簇
  },
  // 故宫：太和殿（三层汉白玉台基 + 殿身 + 重檐庑殿顶，高耸醒目）
  gugong(ctx, cx, gy, s, col) {
    ctx.fillStyle = col
    ctx.fillRect(cx - 150 * s, gy - 16 * s, 300 * s, 16 * s)                             // 台基三层
    ctx.fillRect(cx - 128 * s, gy - 34 * s, 256 * s, 18 * s)
    ctx.fillRect(cx - 106 * s, gy - 52 * s, 212 * s, 18 * s)
    ctx.fillRect(cx - 96 * s, gy - 132 * s, 192 * s, 80 * s)                             // 殿身（含立柱感）
    flyingRoof(ctx, cx, gy - 132 * s, 140 * s, 32 * s, col)                              // 下重檐
    flyingRoof(ctx, cx, gy - 172 * s, 104 * s, 36 * s, col)                              // 上重檐
  },
  // 张家界：石柱峰林（顶部植被簇）
  zhangjiajie(ctx, cx, gy, s, col) {
    ctx.fillStyle = col
    for (const [dx, ph, pw] of [[-92, 150, 28], [-30, 226, 36], [34, 184, 26], [104, 130, 22]] as [number, number, number][]) {
      const px = cx + dx * s
      ctx.fillRect(px - pw * s / 2, gy - ph * s, pw * s, ph * s)
      ctx.beginPath(); ctx.ellipse(px, gy - ph * s, pw * s * 0.75, 10 * s, 0, 0, Math.PI * 2); ctx.fill() // 顶部植被
    }
  },
  // 兵马俑：陶俑军阵（戴冠武士剪影一排）
  bingmayong(ctx, cx, gy, s, col) {
    ctx.fillStyle = col
    for (const dx of [-96, -32, 32, 96]) {
      const px = cx + dx * s, fh = 150 * s
      ctx.beginPath(); ctx.arc(px, gy - fh, 17 * s, 0, Math.PI * 2); ctx.fill()          // 头
      ctx.beginPath(); ctx.arc(px + 9 * s, gy - fh - 13 * s, 8 * s, 0, Math.PI * 2); ctx.fill() // 发髻
      ctx.beginPath()                                                                    // 铠甲身（上窄下宽）
      ctx.moveTo(px - 17 * s, gy - fh + 16 * s); ctx.lineTo(px - 28 * s, gy)
      ctx.lineTo(px + 28 * s, gy); ctx.lineTo(px + 17 * s, gy - fh + 16 * s); ctx.closePath(); ctx.fill()
    }
  },
  // 莫高窟：标志性九层楼（高瘦多层塔楼）
  mogaoku(ctx, cx, gy, s, col) { pagoda(ctx, cx, gy, s, col, 6, 44, 32) },
}

// 颜色工具：解析 rgba/hex 取分量，调整透明度 / 两色混合（用于雾气、山层过渡）
function parseColor(c: string): [number, number, number, number] {
  const m = c.match(/rgba?\(([^)]+)\)/)
  if (m) { const p = m[1].split(',').map((s) => parseFloat(s)); return [p[0], p[1], p[2], p[3] ?? 1] }
  const h = c.replace('#', '')
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16), 1]
}
function withAlpha(c: string, a: number): string {
  const [r, g, b] = parseColor(c)
  return `rgba(${r | 0},${g | 0},${b | 0},${a})`
}
function blend(c1: string, c2: string, t: number): string {
  const a = parseColor(c1), b = parseColor(c2)
  return `rgba(${(a[0] + (b[0] - a[0]) * t) | 0},${(a[1] + (b[1] - a[1]) * t) | 0},${(a[2] + (b[2] - a[2]) * t) | 0},${a[3] + (b[3] - a[3]) * t})`
}

// 顶/底弧各自允许的最大张角：两弧都居中于 12/6 点，各 ≤154.8° 时在 3、9 点方向恒留 ≥25° 空档，
// 既不会绕圈自我重叠，也不会两弧首尾相撞
const ARC_MAX = Math.PI * 0.86

// 邮戳：双环 + 顶弧品牌 + 底弧日期 + 中心纪念字，半透明油墨、轻微旋转，盖在邮票一角
function drawPostmark(ctx: CanvasRenderingContext2D, cx: number, cy: number, r: number, date: Date) {
  ctx.save()
  ctx.translate(cx, cy); ctx.rotate(-0.18)
  ctx.strokeStyle = 'rgba(44,39,34,0.62)'; ctx.fillStyle = 'rgba(44,39,34,0.62)'
  ctx.lineWidth = 3
  const RING = 14                                        // 双环间距 = 弧字唯一可用带宽
  ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.stroke()
  ctx.beginPath(); ctx.arc(0, 0, r - RING, 0, Math.PI * 2); ctx.stroke()
  // 弧字走环带正中、字号由带宽推出（textBaseline=middle → 字身半高 ≤ RING/2 才不越环线，
  // 也就永远进不了内圈的中心字区）
  const ringR = r - RING / 2, ringFont = RING * 0.86
  arcText(ctx, 'TUDAODAO · GUIDE', ringR, ringFont, false)
  const d = `${date.getFullYear()}.${String(date.getMonth() + 1).padStart(2, '0')}.${String(date.getDate()).padStart(2, '0')}`
  arcText(ctx, d, ringR, ringFont, true)
  // 中心横线 + 字
  ctx.fillRect(-26, -2, 52, 2.5)
  ctx.font = '700 16px ui-monospace, monospace'
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
  ctx.fillText('纪念', 0, -16)
  ctx.fillText('travel', 0, 18)
  ctx.restore()
  ctx.textAlign = 'left'; ctx.textBaseline = 'alphabetic'
}

// 沿圆弧逐字排版（flip=false 走顶弧，true 走底弧并翻转字向使其正读）。
// 每字占角必须由 measureText 实际字宽换算（弧度 = 弧长/半径）、总张角超 ARC_MAX 自动缩字号：
// 邮戳半径只有几十像素，用固定角步长会轻易绕过 360° 自我重叠、并压穿内圈的中心字。
function arcText(ctx: CanvasRenderingContext2D, text: string, radius: number, fontPx: number, flip: boolean) {
  const chars = [...text]
  if (!chars.length) return
  const TRACK = 0.08                             // 字距系数（相对字号），保油墨疏松感又不虚耗弧长
  let size = fontPx, widths: number[] = [], sweep = 0
  for (;;) {
    ctx.font = `700 ${size}px ui-monospace, monospace`
    widths = chars.map((c) => ctx.measureText(c).width)
    sweep = (widths.reduce((s, w) => s + w, 0) + size * TRACK * (chars.length - 1)) / radius
    if (sweep <= ARC_MAX || size <= 8) break     // 8px 是可读下限，再挤就让它溢出也不缩
    size -= 0.5
  }
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle'
  const dir = flip ? -1 : 1                      // 底弧反向推进，读序才仍是从左到右
  let cursor = -sweep / 2                        // 游标 = 当前字的前沿角，按各自字宽推进（非等分）
  chars.forEach((ch, i) => {
    const a = dir * (cursor + widths[i] / radius / 2)
    ctx.save()
    ctx.rotate(a)
    ctx.translate(0, flip ? radius : -radius)
    if (flip) ctx.rotate(Math.PI)
    ctx.fillText(ch, 0, 0)
    ctx.restore()
    cursor += (widths[i] + size * TRACK) / radius
  })
}

// 列表拼接，超宽则截断加省略号（用于"途经"行）
function ellipsize(ctx: CanvasRenderingContext2D, items: string[], sep: string, maxW: number): string {
  let out = ''
  for (let i = 0; i < items.length; i++) {
    const next = out ? out + sep + items[i] : items[i]
    if (ctx.measureText('途经　' + next + ' …').width > maxW && out) return out + ' …'
    out = next
  }
  return out
}

// 折行排版（仅量行不绘制）——标点优先断行：溢出时回退到行内最后一个标点处断开，
// 避免把「平安」这类词拆到两行；找不到合适标点才逐字断。
const BREAK_AFTER = new Set([...'，。、；！？…：'])
function layoutLines(ctx: CanvasRenderingContext2D, text: string, maxW: number): string[] {
  const lines: string[] = []
  let line = ''
  for (const c of [...text]) {
    if (ctx.measureText(line + c).width > maxW && line) {
      const chars = [...line]
      let cut = -1
      for (let i = chars.length - 1; i > chars.length * 0.5; i--) {
        if (BREAK_AFTER.has(chars[i])) { cut = i; break }
      }
      if (cut >= 0) { lines.push(chars.slice(0, cut + 1).join('')); line = chars.slice(cut + 1).join('') + c }
      else { lines.push(line); line = c }
    } else line += c
  }
  if (line) lines.push(line)
  return lines
}
