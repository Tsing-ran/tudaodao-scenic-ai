import { MapPin, ChatCircle, Camera, Medal, Image as ImageIcon, Star, X } from '@phosphor-icons/react'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer'
import { BADGE_ICONS } from '@/lib/icons'
import { badges } from '@/lib/trace'
import type { Trace } from '@/lib/trace'
import { cn } from '@/lib/utils'

interface Props {
  open: boolean; onOpenChange: (o: boolean) => void
  trace: Trace
  onPostcard: () => void
  onRate: (score: number) => void
}

export default function TraceSheet({ open, onOpenChange, trace, onPostcard, onRate }: Props) {
  const bs = badges(trace)
  const earned = bs.filter((b) => b.earned).length

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="mx-auto max-h-[88vh] max-w-[480px]">
        <DrawerHeader className="relative pb-1">
          <DrawerClose aria-label="关闭" className="absolute right-3 top-2 z-10 flex size-8 items-center justify-center rounded-full bg-muted text-muted-foreground transition active:scale-90">
            <X className="size-4" />
          </DrawerClose>
          <DrawerTitle className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-xl bg-sweet/15 text-sweet">
              <Medal className="size-[18px]" weight="duotone" />
            </span>
            我的足迹
          </DrawerTitle>
        </DrawerHeader>
        <div className="overflow-y-auto px-4 pb-[max(20px,env(safe-area-inset-bottom))] pt-1">
          {/* 统计 */}
          <div className="grid grid-cols-3 gap-2.5">
            <Stat icon={<MapPin className="size-4" weight="duotone" />} n={trace.visited.length} label="到访景点" />
            <Stat icon={<ChatCircle className="size-4" weight="duotone" />} n={trace.asks} label="提问" />
            <Stat icon={<Camera className="size-4" weight="duotone" />} n={trace.photos} label="拍照定位" />
          </div>

          {/* 徽章 */}
          <div className="mt-4 mb-1 flex items-center justify-between">
            <span className="text-[13px] font-semibold text-muted-foreground">成就徽章</span>
            <span className="text-[12px] text-muted-foreground">{earned}/{bs.length}</span>
          </div>
          <div className="grid grid-cols-3 gap-2.5">
            {bs.map((b) => {
              const BIcon = BADGE_ICONS[b.id]
              return (
                <div key={b.id} className={cn('flex flex-col items-center gap-1 rounded-2xl border p-3 text-center transition duration-200 ease-[var(--ease-out)]',
                  b.earned ? 'border-sweet/45 bg-sweet/10 shadow-sm' : 'bg-card opacity-45 grayscale')}>
                  <span className={b.earned ? 'text-sweet' : 'text-muted-foreground'}>
                    {BIcon && <BIcon className="size-8" weight="duotone" />}
                  </span>
                  <span className="text-[12.5px] font-medium leading-tight">{b.label}</span>
                  <span className="text-[10.5px] leading-tight text-muted-foreground">{b.desc}</span>
                </div>
              )
            })}
          </div>

          {/* 到访列表 */}
          {trace.visited.length > 0 && (
            <>
              <div className="mt-4 mb-2 text-[13px] font-semibold text-muted-foreground">走过的地方</div>
              <div className="flex flex-wrap gap-1.5">
                {trace.visited.map((v) => (
                  <span key={v} className="inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-[12.5px]">
                    <MapPin className="size-3 text-primary" />{v}
                  </span>
                ))}
              </div>
            </>
          )}

          {/* 满意度评分 */}
          <div className="mt-5 rounded-2xl border bg-gradient-to-br from-sweet/[0.06] to-card p-4">
            {trace.rating > 0 ? (
              <div className="flex items-center justify-center gap-2 text-[14px] font-medium text-foreground/80">
                <span className="flex gap-0.5">
                  {Array.from({ length: 5 }, (_, i) => (
                    <Star key={i} weight={i < trace.rating ? 'fill' : 'regular'} className={cn('size-5', i < trace.rating ? 'text-sweet' : 'text-muted-foreground/30')} />
                  ))}
                </span>
                感谢你的评价！
              </div>
            ) : (
              <>
                <div className="mb-2.5 text-center text-[14px] font-medium">这次导览还满意吗？</div>
                <div className="flex justify-center gap-2">
                  {Array.from({ length: 5 }, (_, i) => (
                    <button
                      key={i}
                      aria-label={`评 ${i + 1} 星`}
                      onClick={() => onRate(i + 1)}
                      className="text-muted-foreground/35 transition duration-200 ease-[var(--ease-out)] hover:scale-110 hover:text-sweet active:scale-95"
                    >
                      <Star className="size-8" />
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>

          {/* 生成旅行明信片 */}
          <button
            onClick={onPostcard}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-primary py-3.5 text-[15px] font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition duration-200 ease-[var(--ease-out)] hover:shadow-xl hover:shadow-primary/30 active:scale-[0.98]"
          >
            <ImageIcon className="size-4" /> 生成旅行明信片
          </button>
        </div>
      </DrawerContent>
    </Drawer>
  )
}

function Stat({ icon, n, label }: { icon: React.ReactNode; n: number; label: string }) {
  return (
    <div className="flex flex-col items-center gap-1 rounded-2xl border bg-card py-3">
      <span className="text-primary">{icon}</span>
      <span className="text-xl font-bold">{n}</span>
      <span className="text-[11px] text-muted-foreground">{label}</span>
    </div>
  )
}
