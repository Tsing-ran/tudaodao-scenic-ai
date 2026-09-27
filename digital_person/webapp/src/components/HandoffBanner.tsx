import { Devices, WarningCircle, X } from '@phosphor-icons/react'
import { cn } from '@/lib/utils'

// 接力提示条（滑入头部下方）：扫码带走成功 / 二维码过期 两种语气。
// 视觉与主屏一体（主色微底 + duotone 图标），可手动关、外部定时自动关。
export default function HandoffBanner({ title, detail, tone = 'ok', onDismiss }: {
  title: string; detail: string; tone?: 'ok' | 'warn'; onDismiss: () => void
}) {
  const warn = tone === 'warn'
  return (
    <div className="px-4 pt-3" role="status" aria-live="polite">
      <div className={cn(
        'anim-fade-up flex items-center gap-3 rounded-2xl border px-3.5 py-2.5 shadow-sm',
        warn
          ? 'border-amber-500/25 bg-amber-500/[0.08]'
          : 'border-primary/20 bg-gradient-to-r from-primary/[0.09] to-sweet/[0.09]',
      )}>
        <span className={cn(
          'flex size-9 shrink-0 items-center justify-center rounded-xl',
          warn ? 'bg-amber-500/15 text-amber-600' : 'bg-primary/12 text-primary',
        )}>
          {warn ? <WarningCircle className="size-[18px]" weight="duotone" /> : <Devices className="size-[18px]" weight="duotone" />}
        </span>
        <div className="min-w-0 flex-1 leading-tight">
          <div className="text-[13.5px] font-semibold text-foreground">{title}</div>
          <div className="truncate text-[12px] text-muted-foreground">{detail}</div>
        </div>
        <button
          aria-label="dismiss"
          onClick={onDismiss}
          className="flex size-7 shrink-0 items-center justify-center rounded-full text-muted-foreground transition duration-200 ease-[var(--ease-out)] hover:bg-muted active:scale-90"
        >
          <X className="size-4" />
        </button>
      </div>
    </div>
  )
}
