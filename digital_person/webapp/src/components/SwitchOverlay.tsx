import { Sparkle } from '@phosphor-icons/react'
import { cn } from '@/lib/utils'

interface Props {
  stageName: string
  preview?: string
  leaving?: boolean   // true → 交叉淡出回直播（App 在 POST ok 后 ~1.5s 触发）
}

/**
 * 形象切换过渡层：热切的几秒里盖住视频，用**新形象的静态立绘** + 模糊氛围底 + 扫光 +
 * 「正在换上『艺名』…」承接切换过程——绝不把旧形象/旧帧当过渡画面。POST ok 后由父组件
 * 置 leaving 交叉淡出回直播。覆盖在视频（含 L1 成片 z-30）之上，故 z-40。
 */
export default function SwitchOverlay({ stageName, preview, leaving }: Props) {
  return (
    <div
      className={cn(
        'absolute inset-0 z-40 flex flex-col items-center justify-center overflow-hidden',
        'transition-opacity duration-[400ms] ease-[var(--ease-out)]',
        leaving ? 'opacity-0' : 'opacity-100',
      )}
      aria-live="polite"
    >
      {/* 模糊氛围底：新形象立绘放大虚化 + 深色压暗 */}
      <div className="absolute inset-0">
        {preview
          ? <img src={preview} alt="" className="size-full scale-125 object-cover blur-2xl" />
          : <div className="size-full bg-gradient-to-br from-primary/40 to-sweet/25" />}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/55 to-black/45 backdrop-blur-[2px]" />
      </div>

      {/* 前景：新形象立绘 + 呼吸光环 + 一道扫光 */}
      <div className="relative">
        <span className="absolute -inset-3 rounded-[1.8rem] bg-primary/40 blur-2xl motion-safe:animate-[halo-breathe_2.4s_var(--ease-out)_infinite]" />
        <div className="relative h-36 w-[116px] overflow-hidden rounded-[1.5rem] shadow-2xl shadow-black/50 ring-1 ring-white/40 motion-safe:animate-[avatar-rise_0.5s_var(--ease-out)_both]">
          {preview
            ? <img src={preview} alt={stageName} className="size-full object-cover object-top" />
            : <div className="size-full bg-gradient-to-br from-primary/50 to-sweet/40" />}
          {/* 扫光 */}
          <span className="pointer-events-none absolute inset-y-0 -left-1/2 w-1/2 skew-x-[-18deg] bg-gradient-to-r from-transparent via-white/45 to-transparent motion-safe:animate-[sweep-x_1.7s_ease-in-out_infinite]" />
        </div>
      </div>

      <p className="relative mt-4 flex items-center gap-1.5 text-[13.5px] font-medium text-white drop-shadow">
        <Sparkle className="size-4 motion-safe:animate-pulse" weight="duotone" />
        正在换上「{stageName}」…
      </p>
    </div>
  )
}
