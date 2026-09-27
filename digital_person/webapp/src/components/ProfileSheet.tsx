import { IdentificationCard } from '@phosphor-icons/react'
import type { Icon as PhIcon } from '@phosphor-icons/react'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from '@/components/ui/drawer'
import { GROUPS, INTERESTS, AGES, PACES, MOBILITIES, PURPOSES, FIRSTTIMES, makeT } from '@/lib/i18n'
import type { Lang } from '@/lib/i18n'
import { AGE_ICONS, PACE_ICONS, MOBILITY_ICONS, PURPOSE_ICONS, FIRSTTIME_ICONS } from '@/lib/icons'
import { cn } from '@/lib/utils'

type Opt = { id: string; label: Record<Lang, string> }

// 可调画像：中途改「同行人 / 自身情况 5 维 / 兴趣」。即改即生效（写偏好），关联的「为你定制」推荐、
// 数字人讲解口吻、设施排序随之重算 —— 与开场向导对等的「随时可改」。
export default function ProfileSheet({
  open, onOpenChange, lang, groupType, setGroupType, interests, setInterests,
  age, setAge, pace, setPace, mobility, setMobility, purpose, setPurpose, firstTime, setFirstTime,
}: {
  open: boolean
  onOpenChange: (o: boolean) => void
  lang: Lang
  groupType: string; setGroupType: (g: string) => void
  interests: string[]; setInterests: (v: string[]) => void
  age: string; setAge: (s: string) => void
  pace: string; setPace: (s: string) => void
  mobility: string; setMobility: (s: string) => void
  purpose: string; setPurpose: (s: string) => void
  firstTime: string; setFirstTime: (s: string) => void
}) {
  const t = makeT(lang)
  const toggle = (id: string) => setInterests(interests.includes(id) ? interests.filter((x) => x !== id) : [...interests, id])
  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="mx-auto max-h-[90vh] max-w-[480px]">
        <DrawerHeader className="pb-1">
          <DrawerTitle className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <IdentificationCard className="size-[18px]" weight="duotone" />
            </span>
            你的画像
          </DrawerTitle>
        </DrawerHeader>
        <div className="space-y-5 overflow-y-auto px-4 pb-[max(20px,env(safe-area-inset-bottom))] pt-2">
          <p className="text-[12.5px] leading-relaxed text-muted-foreground">改完推荐、讲解口吻、设施排序都会按新画像立即更新。</p>

          {/* 同行人（2 列卡片，沿用原样式） */}
          <div>
            <div className="mb-2 text-[13px] font-semibold">{t('ob_who')}</div>
            <div className="grid grid-cols-2 gap-2">
              {GROUPS.map((gp) => (
                <button
                  key={gp.id}
                  onClick={() => setGroupType(gp.id)}
                  className={cn(
                    'rounded-2xl border px-3 py-2.5 text-[14px] font-medium transition duration-200 active:scale-[0.97]',
                    groupType === gp.id ? 'border-primary bg-primary/[0.06] text-primary' : 'hover:bg-accent/40',
                  )}
                >
                  {gp.label[lang]}
                </button>
              ))}
            </div>
          </div>

          {/* 自身情况 5 维（单选 pill 行） */}
          <PillRow title={t('ob_first_q')} options={FIRSTTIMES} icons={FIRSTTIME_ICONS} value={firstTime} onPick={setFirstTime} lang={lang} />
          <PillRow title={t('ob_pace_q')} options={PACES} icons={PACE_ICONS} value={pace} onPick={setPace} lang={lang} />
          <PillRow title={t('ob_mobility_q')} options={MOBILITIES} icons={MOBILITY_ICONS} value={mobility} onPick={setMobility} lang={lang} />
          <PillRow title={t('ob_step4_title')} options={PURPOSES} icons={PURPOSE_ICONS} value={purpose} onPick={setPurpose} lang={lang} />
          <PillRow title={t('ob_age_q')} options={AGES} icons={AGE_ICONS} value={age} onPick={setAge} lang={lang} />

          {/* 兴趣（多选） */}
          <div>
            <div className="mb-2 text-[13px] font-semibold">{t('ob_interest')}</div>
            <div className="flex flex-wrap gap-2">
              {INTERESTS.map((it) => (
                <button
                  key={it.id}
                  onClick={() => toggle(it.id)}
                  className={cn(
                    'rounded-full border px-3.5 py-1.5 text-[13px] font-medium transition duration-200 active:scale-95',
                    interests.includes(it.id) ? 'border-primary bg-primary/[0.06] text-primary' : 'hover:bg-accent/40',
                  )}
                >
                  {it.label[lang]}
                </button>
              ))}
            </div>
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  )
}

// 单选 pill 行（带小标题）：一维自身情况标签
function PillRow({ title, options, icons, value, onPick, lang }: {
  title: string; options: Opt[]; icons: Record<string, PhIcon>
  value: string; onPick: (id: string) => void; lang: Lang
}) {
  return (
    <div>
      <div className="mb-2 text-[13px] font-semibold">{title}</div>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => {
          const I = icons[o.id]
          const on = value === o.id
          return (
            <button
              key={o.id}
              onClick={() => onPick(o.id)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[13px] font-medium transition duration-200 active:scale-95',
                on ? 'border-primary bg-primary/[0.06] text-primary' : 'hover:bg-accent/40',
              )}
            >
              {I && <I className={cn('size-4', !on && 'text-primary')} weight="duotone" />}
              {o.label[lang]}
            </button>
          )
        })}
      </div>
    </div>
  )
}
