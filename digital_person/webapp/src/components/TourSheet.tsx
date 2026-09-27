import { useEffect, useState } from 'react'
import { MapPin, Clock, CaretRight, SpeakerHigh, Flag, CheckCircle } from '@phosphor-icons/react'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from '@/components/ui/drawer'
import * as api from '@/lib/api'
import type { Route } from '@/lib/api'
import { cn } from '@/lib/utils'

interface Props {
  open: boolean; onOpenChange: (o: boolean) => void
  scenic: string; groupType: string
  visited: string[]
  onAsk: (stationName: string) => void
  onRouteDone: (id: string) => void
}

export default function TourSheet({ open, onOpenChange, scenic, groupType, visited, onAsk, onRouteDone }: Props) {
  const [list, setList] = useState<Route[]>([])
  const [sel, setSel] = useState<Route | null>(null)

  useEffect(() => {
    if (!open) return
    setSel(null)
    // 命中当前同行人画像的路线置顶（「为你推荐」徽章已在，再让它排在第一眼）
    api.routes(scenic)
      .then((rs) => setList([...rs].sort((a, b) => Number(b.group === groupType) - Number(a.group === groupType))))
      .catch(() => setList([]))
  }, [open, scenic, groupType])

  const speak = (name: string) => { onAsk(name); onOpenChange(false) }

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="mx-auto max-h-[88vh] max-w-[480px]">
        <DrawerHeader className="pb-1">
          <DrawerTitle className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <MapPin className="size-[18px]" weight="duotone" />
            </span>
            {sel ? sel.title : '跟我游 · 选条路线'}
          </DrawerTitle>
        </DrawerHeader>

        <div className="overflow-y-auto px-4 pb-[max(20px,env(safe-area-inset-bottom))]">
          {!sel ? (
            <div className="flex flex-col gap-3 pt-2">
              {list.map((r) => {
                const rec = r.group === groupType
                return (
                  <button
                    key={r.id}
                    onClick={() => setSel(r)}
                    className={cn('flex items-center gap-3 rounded-2xl border bg-card p-4 text-left transition duration-200 ease-[var(--ease-out)] hover:border-primary/40 active:scale-[0.99]',
                      rec && 'border-primary/45 bg-primary/[0.03] ring-1 ring-primary/25')}
                  >
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold">{r.title}</span>
                        {rec && <span className="rounded-full bg-sweet px-1.5 py-0.5 text-[10px] font-medium text-sweet-foreground shadow-sm">为你推荐</span>}
                      </div>
                      <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                        <span className="inline-flex items-center gap-1"><Clock className="size-3" />{r.duration}</span>
                        <span className="inline-flex items-center gap-1"><MapPin className="size-3" />{r.stations.length} 站</span>
                        <span className="rounded-full bg-muted px-1.5 py-0.5">{r.tag}</span>
                      </div>
                    </div>
                    <CaretRight className="size-5 shrink-0 text-muted-foreground" />
                  </button>
                )
              })}
              {!list.length && <p className="py-8 text-center text-sm text-muted-foreground">该景区暂未配置路线</p>}
            </div>
          ) : (
            <div className="pt-1">
              <button onClick={() => setSel(null)} className="mb-3 text-[13px] text-primary">‹ 返回路线列表</button>
              <ol className="relative flex flex-col gap-0">
                {sel.stations.map((s, i) => {
                  const done = visited.includes(s.name)
                  const last = i === sel.stations.length - 1
                  return (
                    <li key={s.name} className="relative flex gap-3 pb-4">
                      {/* 连线 */}
                      {!last && <span className="absolute left-[15px] top-8 h-full w-px bg-border" />}
                      <span className={cn('z-10 flex size-8 shrink-0 items-center justify-center rounded-full border-2 text-sm font-semibold',
                        done ? 'border-emerald-500 bg-emerald-500 text-white' : 'border-primary bg-background text-primary')}>
                        {done ? <CheckCircle className="size-4" weight="fill" /> : i + 1}
                      </span>
                      <div className="flex-1 rounded-xl border bg-card p-3">
                        <div className="font-medium">{s.name}</div>
                        {s.hint && <div className="mt-0.5 text-[12px] leading-relaxed text-muted-foreground">{s.hint}</div>}
                        <button
                          onClick={() => speak(s.name)}
                          className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1.5 text-[13px] font-medium text-primary transition duration-200 ease-[var(--ease-out)] hover:bg-primary/15 active:scale-95"
                        >
                          <SpeakerHigh className="size-3.5" /> 听讲解
                        </button>
                      </div>
                    </li>
                  )
                })}
              </ol>
              <button
                onClick={() => { onRouteDone(sel.id); onOpenChange(false) }}
                className="mt-2 flex w-full items-center justify-center gap-2 rounded-2xl bg-primary py-3 text-[15px] font-semibold text-primary-foreground active:scale-[0.98]"
              >
                <Flag className="size-4" /> 完成这条路线
              </button>
            </div>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  )
}
