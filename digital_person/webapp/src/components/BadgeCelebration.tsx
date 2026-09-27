import { useEffect } from 'react'
import { Sparkle } from '@phosphor-icons/react'
import { BADGE_ICONS } from '@/lib/icons'
import type { Badge } from '@/lib/trace'

// 徽章解锁「高光时刻」：居中大卡 + 图标 + 撒花光点，自动 ~2.5s 淡出（也可点击立即收起）。
// 演示英雄镜头（step 9 到达获得勋章）：比藏在足迹抽屉里的静默计算更适合上镜。
export default function BadgeCelebration({ badge, onDone }: { badge: Badge; onDone: () => void }) {
  useEffect(() => {
    const id = window.setTimeout(onDone, 2500)
    return () => window.clearTimeout(id)
  }, [badge.id, onDone])

  const BIcon = BADGE_ICONS[badge.id] || Sparkle
  // 环绕撒花：固定角度 + 交错延迟，纯 CSS 无依赖
  const confetti = Array.from({ length: 10 }, (_, i) => ({ i, angle: (360 / 10) * i, delay: (i % 5) * 60 }))

  return (
    <div
      onClick={onDone}
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/25 px-8 backdrop-blur-[2px] motion-safe:animate-[fade-in_0.2s_var(--ease-out)]"
      role="status"
      aria-live="polite"
    >
      <div className="relative flex flex-col items-center gap-3 rounded-3xl border border-sweet/40 bg-popover/95 px-8 py-7 text-center shadow-2xl shadow-black/30 motion-safe:animate-[badge-pop_0.45s_var(--ease-out)_both]">
        {/* 撒花光点 */}
        {confetti.map(({ i, angle, delay }) => (
          <span
            key={i}
            aria-hidden
            className="pointer-events-none absolute left-1/2 top-1/2 size-2 rounded-full bg-sweet motion-safe:animate-[confetti-burst_1.1s_var(--ease-out)_both]"
            style={{ '--ang': `${angle}deg`, animationDelay: `${delay}ms`, opacity: i % 2 ? 0.9 : 0.6 } as React.CSSProperties}
          />
        ))}
        <div className="relative flex size-20 items-center justify-center">
          <span className="absolute inset-0 rounded-full bg-sweet/20 blur-xl motion-safe:animate-pulse" />
          <span className="relative flex size-16 items-center justify-center rounded-full bg-gradient-to-br from-sweet to-sweet/70 text-sweet-foreground shadow-lg shadow-sweet/40">
            <BIcon className="size-9" weight="duotone" />
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wider text-sweet">
          <Sparkle className="size-3.5" weight="fill" /> 解锁徽章
        </div>
        <div className="text-[19px] font-bold tracking-tight text-foreground">{badge.label}</div>
        <div className="text-[13px] text-muted-foreground">{badge.desc}</div>
      </div>
    </div>
  )
}
