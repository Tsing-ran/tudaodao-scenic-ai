import { Clock, MapPin, FlowerLotus, Lightning, ChatCircleDots } from '@phosphor-icons/react'
import { EMO_META } from '@/lib/icons'
import { cn } from '@/lib/utils'
import type { Meta } from '@/hooks/useGuide'

// 意图中文名
export function intentLabel(i: string) {
  return ({ qa: '问答', navigation: '指路', recommend: '推荐', empathy: '关怀', chitchat: '闲聊' } as Record<string, string>)[i] || '问答'
}

// 单枚标签胶囊（主色 / 暖色 / 中性三态）
export function Pill({ children, tone }: { children: React.ReactNode; tone?: 'amber' | 'muted' }) {
  return (
    <span className={cn(
      'inline-flex items-center gap-1 rounded-full bg-background/90 px-2.5 py-1 text-[11px] font-medium shadow-sm backdrop-blur',
      tone === 'amber' ? 'text-amber-600' : tone === 'muted' ? 'text-muted-foreground' : 'text-primary',
    )}>
      {children}
    </span>
  )
}

export function EmotionPill({ emotion }: { emotion: string }) {
  const meta = EMO_META[emotion]
  if (!meta) return <Pill tone="amber">{emotion}</Pill>
  return <Pill tone="amber"><meta.Icon className="size-3" weight="duotone" /> {meta.label}</Pill>
}

// 一行 meta 标签（意图/情绪/耗时/缓存/降级/定位/迎宾）。className 由调用方控制外距与排布。
export function MetaRow({ meta, className }: { meta: Meta; className?: string }) {
  const has = meta.intent || meta.emotion || meta.timing || meta.cached || meta.degraded || meta.location || meta.greet
  if (!has) return null
  return (
    <div className={cn('flex flex-wrap items-center gap-1.5', className)}>
      {meta.greet && <Pill><FlowerLotus className="size-3" weight="duotone" /> 主动迎宾</Pill>}
      {meta.cached && <Pill><Lightning className="size-3" weight="duotone" /> 秒回·缓存</Pill>}
      {meta.degraded && <Pill tone="amber"><ChatCircleDots className="size-3" weight="duotone" /> 文字模式·繁忙</Pill>}
      {meta.location && <Pill><MapPin className="size-3" /> {meta.location}</Pill>}
      {meta.intent && <Pill>{intentLabel(meta.intent)}</Pill>}
      {meta.emotion && <EmotionPill emotion={meta.emotion} />}
      {meta.timing && <Pill tone="muted"><Clock className="size-3" /> {meta.timing}s</Pill>}
    </div>
  )
}
