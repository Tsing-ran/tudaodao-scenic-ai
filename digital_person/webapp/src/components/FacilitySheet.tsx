import { useEffect, useMemo, useState } from 'react'
import { NavigationArrow, Lifebuoy, MapPin, Sparkle, X } from '@phosphor-icons/react'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer'
import { FACILITY_ICONS } from '@/lib/icons'
import { facilityRank, facilityHint } from '@/lib/personalize'
import { hasFacilityMap } from '@/lib/facilityGeo'
import type { FacilityTarget } from '@/components/FacilityMapSheet'
import type { Lang, Situation } from '@/lib/i18n'
import * as api from '@/lib/api'
import type { FacilityGroup } from '@/lib/api'

interface Props {
  open: boolean; onOpenChange: (o: boolean) => void
  scenic: string; groupType: string; lang: Lang; sit?: Partial<Situation>
  onAsk: (q: string) => void
  onNavigate?: (t: FacilityTarget) => void   // 打开地图版设施导航（父级承载 FacilityMapSheet）
}

export default function FacilitySheet({ open, onOpenChange, scenic, groupType, lang, sit, onAsk, onNavigate }: Props) {
  const [groups, setGroups] = useState<FacilityGroup[]>([])
  useEffect(() => {
    if (!open) return
    api.facilities(scenic).then(setGroups).catch(() => setGroups([]))
  }, [open, scenic])
  // 按画像 + 自身情况把最相关的设施类别提前（轮椅→无障碍置顶，婴儿车→母婴，长辈→休息/医务）
  const ordered = useMemo(() => {
    const rank = facilityRank(groupType, sit)
    return [...groups].sort((a, b) => rank(a.id) - rank(b.id))
  }, [groups, groupType, sit])
  const hint = facilityHint(groupType, lang, sit)
  const mapReady = hasFacilityMap(scenic) && !!onNavigate
  // 点某个设施点位：有地图坐标的景区（如灵山）→ 打开地图版设施导航，在地图上画出到该设施的路线；
  // 无坐标的景区 → 回退到「XX怎么走」语音指路（走既有问答/指路链路，对全景区可靠）。
  const navTo = (typeId: string, label: string, point: string) => {
    if (mapReady) { onNavigate!({ typeId, label, pointName: point }); onOpenChange(false) }
    else { onAsk(`${point}怎么走`); onOpenChange(false) }
  }

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="mx-auto max-h-[88vh] max-w-[480px]">
        <DrawerHeader className="relative pb-1">
          <DrawerClose aria-label="关闭" className="absolute right-3 top-2 z-10 flex size-8 items-center justify-center rounded-full bg-muted text-muted-foreground transition active:scale-90">
            <X className="size-4" />
          </DrawerClose>
          <DrawerTitle className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <Lifebuoy className="size-[18px]" weight="duotone" />
            </span>
            设施速查
          </DrawerTitle>
        </DrawerHeader>
        <div className="overflow-y-auto px-4 pb-[max(20px,env(safe-area-inset-bottom))] pt-1">
          {hint && groups.length > 0 && (
            <div className="mb-2.5 flex items-center gap-1.5 rounded-xl bg-primary/[0.06] px-3 py-2 text-[12.5px] font-medium text-primary">
              <Sparkle className="size-3.5 shrink-0" weight="duotone" />{hint}
            </div>
          )}
          <div className="grid grid-cols-1 gap-2.5">
            {ordered.map((g) => {
              const FIcon = FACILITY_ICONS[g.id] || MapPin
              return (
              <div key={g.id} className="rounded-2xl border bg-card p-3.5">
                <div className="flex items-center gap-2 text-[14px] font-semibold">
                  <span className="flex size-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <FIcon className="size-[18px]" weight="duotone" />
                  </span>{g.label}
                  <span className="text-xs font-normal text-muted-foreground">· {g.points.length} 处</span>
                  <span className="ml-auto text-[11px] font-normal text-muted-foreground">{mapReady ? '点击看路线' : '点击导航'}</span>
                </div>
                {/* 每个点位可点：有坐标→地图画路线；无坐标→数字人语音指路。整卡不是静态文字了。 */}
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {g.points.map((p) => (
                    <button
                      key={p}
                      onClick={() => navTo(g.id, g.label, p)}
                      className="inline-flex items-center gap-1 rounded-lg bg-muted px-2.5 py-1 text-[12.5px] text-foreground/80 transition duration-200 ease-[var(--ease-out)] hover:bg-primary/10 hover:text-primary active:scale-95"
                    >
                      <NavigationArrow className="size-3 shrink-0 opacity-70" />{p}
                    </button>
                  ))}
                </div>
              </div>
            )})}
            {!groups.length && <p className="py-8 text-center text-sm text-muted-foreground">该景区暂未配置设施信息</p>}
          </div>
          <button
            onClick={() => { onAsk('最近的卫生间怎么走'); onOpenChange(false) }}
            className="mt-3 flex w-full items-center justify-center gap-2 rounded-2xl border border-primary/60 bg-primary/[0.04] py-3 text-[14px] font-medium text-primary transition duration-200 ease-[var(--ease-out)] hover:bg-primary/[0.08] active:scale-[0.98]"
          >
            <NavigationArrow className="size-4" /> 问数字人「离我最近的怎么走」
          </button>
        </div>
      </DrawerContent>
    </Drawer>
  )
}
