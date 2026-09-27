import { useEffect, useState } from 'react'
import { Sun, CloudRain, Cloud, Users, Lightbulb, HeartStraight } from '@phosphor-icons/react'
import * as api from '@/lib/api'
import type { TodayResp } from '@/lib/api'
import { careReminder } from '@/lib/personalize'
import type { Lang, Situation } from '@/lib/i18n'

function weatherIcon(w: string) {
  if (w.includes('雨')) return <CloudRain className="size-4 text-blue-500" weight="duotone" />
  if (w.includes('云') || w.includes('阴')) return <Cloud className="size-4 text-slate-400" weight="duotone" />
  return <Sun className="size-4 text-amber-500" weight="duotone" />
}

export default function TodayCard({ scenic, groupType, interests, lang, sit, label }: {
  scenic: string; groupType: string; interests: string[]; lang: Lang; sit?: Partial<Situation>
  label: { today: string; tip: string }
}) {
  const [d, setD] = useState<TodayResp | null>(null)
  useEffect(() => {
    let alive = true
    api.today(scenic).then((r) => { if (alive) setD(r) }).catch(() => {})
    return () => { alive = false }
  }, [scenic])

  // 主动贴心提醒：画像 × 自身情况 × 此刻时段（与天气 tip 互补，是"给你"的关怀，永远可显）
  const care = careReminder(groupType, interests, lang, undefined, sit)
  if (!d || (!d.weather && !d.tip)) return null
  return (
    <div className="rounded-2xl border bg-gradient-to-br from-primary/[0.07] via-card to-sweet/[0.05] p-3.5">
      <div className="flex items-center gap-3 text-[13px] font-medium">
        <span className="font-semibold text-foreground/80">{label.today}</span>
        {d.weather && <span className="inline-flex items-center gap-1">{weatherIcon(d.weather)}{d.weather}</span>}
        {d.period && <span className="text-muted-foreground">· {d.period}</span>}
        {d.crowd && (
          <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-background px-2 py-0.5 text-xs text-muted-foreground shadow-sm">
            <Users className="size-3" />{d.crowd}
          </span>
        )}
      </div>
      {d.tip && (
        <div className="mt-2 flex items-start gap-1.5 text-[13px] leading-relaxed text-foreground/80">
          <Lightbulb className="mt-0.5 size-3.5 shrink-0 text-amber-500" weight="duotone" />
          <span>{d.tip}</span>
        </div>
      )}
      {care && (
        <div className="mt-1.5 flex items-start gap-1.5 border-t border-border/60 pt-2 text-[13px] leading-relaxed text-primary/90">
          <HeartStraight className="mt-0.5 size-3.5 shrink-0 text-primary" weight="duotone" />
          <span>{care}</span>
        </div>
      )}
    </div>
  )
}
