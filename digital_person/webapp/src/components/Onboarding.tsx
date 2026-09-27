import { useEffect, useState } from 'react'
import { Sparkle, Check, Globe, CaretLeft, ArrowRight } from '@phosphor-icons/react'
import type { Icon as PhIcon } from '@phosphor-icons/react'
import { cn } from '@/lib/utils'
import {
  GROUP_ICONS, INTEREST_ICONS, AGE_ICONS, PACE_ICONS, MOBILITY_ICONS, PURPOSE_ICONS, FIRSTTIME_ICONS,
} from '@/lib/icons'
import {
  GROUPS, INTERESTS, LANGS, AGES, PACES, MOBILITIES, PURPOSES, FIRSTTIMES, makeT,
} from '@/lib/i18n'
import type { Lang } from '@/lib/i18n'
import { SCENICS } from '@/hooks/useGuide'

interface Props {
  lang: Lang; setLang: (l: Lang) => void
  scenic: string; setScenic: (s: string) => void
  groupType: string; setGroupType: (g: string) => void
  interests: string[]; setInterests: (fn: (prev: string[]) => string[]) => void
  // 自身情况标签（多步引导新增 5 维，默认值已在 useGuide 预置 → 跳过任意步都得合法画像）
  age: string; setAge: (s: string) => void
  pace: string; setPace: (s: string) => void
  mobility: string; setMobility: (s: string) => void
  purpose: string; setPurpose: (s: string) => void
  firstTime: string; setFirstTime: (s: string) => void
  guideName: string
  avatarPref: string
  onEnter: () => void
}

// 打字机问候：切语言自动重打；prefers-reduced-motion 下直接呈现全文
const prefersReduced = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches
function useTypewriter(text: string, speed = 65) {
  const [n, setN] = useState(() => (prefersReduced() ? text.length : 0))
  useEffect(() => {
    if (prefersReduced()) { setN(text.length); return }
    setN(0)
    const id = window.setInterval(() => {
      setN((p) => {
        if (p >= text.length) { window.clearInterval(id); return p }
        return p + 1
      })
    }, speed)
    return () => window.clearInterval(id)
  }, [text, speed])
  return { typed: text.slice(0, n), done: n >= text.length }
}

const FALLBACK_AVATAR = '/avatars/female_sweet.jpg'
type Opt = { id: string; label: Record<Lang, string> }
const scenicPostcardSrc = (id: string) => `/postcard/${id}.jpg${id === 'lingshan' ? '?v=20260702' : ''}`

const STEP_META: { title: string; sub: string }[] = [
  { title: 'ob_step1_title', sub: 'ob_step1_sub' },
  { title: 'ob_step2_title', sub: 'ob_step2_sub' },
  { title: 'ob_step3_title', sub: 'ob_step3_sub' },
  { title: 'ob_step4_title', sub: 'ob_step4_sub' },
  { title: 'ob_step5_title', sub: 'ob_step5_sub' },
]

// 多步引导式开场（社交 App 感）：① 景区 → ② 同伴·初访 → ③ 节奏·出行 → ④ 心情·年龄 → ⑤ 兴趣。
// 单选「点选即跳」（reduced-motion 立即），组合步用「下一步」；每步可「跳过」（全维度已预设默认）。
export default function Onboarding({
  lang, setLang, scenic, setScenic, groupType, setGroupType, interests, setInterests,
  age, setAge, pace, setPace, mobility, setMobility, purpose, setPurpose, firstTime, setFirstTime,
  guideName, avatarPref, onEnter,
}: Props) {
  const t = makeT(lang)
  const [step, setStep] = useState(0)            // 0=intro，1..5=内容步
  const [advancing, setAdvancing] = useState(false)
  const greeting = t('ob_greet')
  const { typed, done } = useTypewriter(greeting)
  const avatarSrc = avatarPref ? `/avatars/${avatarPref}.jpg` : FALLBACK_AVATAR

  const back = () => setStep((s) => Math.max(s - 1, 0))
  const advance = () => setStep((s) => Math.min(s + 1, 5))
  // 单选自动跳：选完轻顿一下再进下一步（让"已选中"被看见），reduced-motion 立即；防双跳
  const autoAdvance = () => {
    if (advancing) return
    setAdvancing(true)
    const go = () => { setAdvancing(false); advance() }
    if (prefersReduced()) go(); else window.setTimeout(go, 220)
  }
  const toggleInterest = (id: string) =>
    setInterests((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))

  // ── Intro：数字人迎宾 hero + 打字机 + 开始/跳过 ──
  if (step === 0) {
    return (
      <div className="mx-auto flex min-h-[100dvh] w-full max-w-[480px] flex-col bg-gradient-to-b from-primary/[0.08] via-background to-background">
        <div className="anim-fade-up flex justify-end px-4 pt-[max(12px,env(safe-area-inset-top))]">
          <div className="flex items-center gap-1 rounded-full border bg-card/80 p-1 shadow-sm backdrop-blur">
            <Globe className="ml-1.5 size-3.5 text-muted-foreground" />
            {LANGS.map((l) => (
              <button
                key={l.id}
                onClick={() => setLang(l.id)}
                className={cn('rounded-full px-2.5 py-1 text-xs font-medium transition',
                  lang === l.id ? 'bg-primary text-primary-foreground' : 'text-muted-foreground')}
              >
                {l.label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-1 flex-col items-center justify-center gap-6 px-6 pb-4">
          <div className="anim-fade-up flex items-center gap-2.5" style={{ animationDelay: '40ms' }}>
            <img src="/logo.png" alt="途叨叨" width={28} height={28} className="h-7 w-7 shrink-0" />
            <span className="text-[15px] font-semibold tracking-tight">途叨叨</span>
          </div>

          <div className="anim-fade-up relative" style={{ animationDelay: '120ms' }}>
            <span
              aria-hidden
              className="absolute -inset-3 rounded-[2.4rem] bg-primary/25 blur-2xl motion-safe:animate-[halo-breathe_3.2s_var(--ease-out)_infinite]"
            />
            <img
              src={avatarSrc}
              alt=""
              width={360}
              height={640}
              fetchPriority="high"
              onError={(e) => { if (e.currentTarget.src !== location.origin + FALLBACK_AVATAR) e.currentTarget.src = FALLBACK_AVATAR }}
              className="relative h-[210px] w-[162px] rounded-[1.9rem] border object-cover object-top shadow-lg shadow-primary/20 ring-1 ring-primary/25"
            />
            <span className="absolute bottom-2 right-2 size-3 rounded-full bg-emerald-500 ring-2 ring-background" />
          </div>

          <div className="anim-fade-up min-h-[84px] text-center" style={{ animationDelay: '220ms' }}>
            <h1 aria-label={greeting} className="text-balance text-[22px] font-bold tracking-tight">
              {typed}
              {!done && (
                <span
                  aria-hidden
                  className="ml-0.5 inline-block h-[1.05em] w-[2px] translate-y-[3px] bg-primary motion-safe:animate-[caret-blink_1s_steps(1)_infinite]"
                />
              )}
            </h1>
            <p className="mt-2 px-4 text-[13.5px] leading-relaxed text-muted-foreground">{t('ob_greet_sub')}</p>
          </div>
        </div>

        <div className="sticky bottom-0 border-t bg-background/85 px-5 pb-[max(16px,env(safe-area-inset-bottom))] pt-3 backdrop-blur-xl">
          <div className="anim-fade-up" style={{ animationDelay: '320ms' }}>
            <button
              onClick={() => setStep(1)}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-primary py-3.5 text-[15px] font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition duration-200 ease-[var(--ease-out)] hover:shadow-xl hover:shadow-primary/30 active:scale-[0.98]"
            >
              <Sparkle className="size-4" weight="duotone" /> {t('ob_start_btn')}
            </button>
            <button onClick={onEnter} className="mt-2 w-full text-center text-[13px] text-muted-foreground transition active:scale-95">
              {t('ob_skip')}
            </button>
          </div>
        </div>
      </div>
    )
  }

  // ── 内容步（1..5）：返回 · 进度点 · 跳过 头部 + 标题 + 步骤主体 ──
  const meta = STEP_META[step - 1]
  return (
    <div className="mx-auto flex min-h-[100dvh] w-full max-w-[480px] flex-col bg-gradient-to-b from-primary/[0.08] via-background to-background">
      <div className="flex items-center justify-between gap-2 px-3 pt-[max(12px,env(safe-area-inset-top))] pb-1">
        <button
          onClick={back}
          aria-label="back"
          className="flex size-9 items-center justify-center rounded-full text-muted-foreground transition active:scale-90 hover:text-foreground"
        >
          <CaretLeft className="size-5" />
        </button>
        <ProgressDots total={5} current={step} />
        <button
          onClick={onEnter}
          className="rounded-full px-3 py-1.5 text-[13px] font-medium text-muted-foreground transition active:scale-95 hover:text-foreground"
        >
          {t('ob_skip_short')}
        </button>
      </div>

      <div key={step} className="flex flex-1 flex-col gap-5 overflow-y-auto px-5 pb-4 pt-3">
        <div className="anim-fade-up flex flex-col gap-1.5">
          <h1 className="text-balance text-[22px] font-bold leading-snug tracking-tight">{t(meta.title)}</h1>
          <p className="text-[13.5px] leading-relaxed text-muted-foreground">{t(meta.sub)}</p>
        </div>

        {/* ① 景区（横滑实景卡，点选即跳） */}
        {step === 1 && (
          <div className="anim-fade-up flex flex-col gap-3" style={{ animationDelay: '70ms' }}>
            <div className="-mx-5 flex snap-x gap-3 overflow-x-auto px-5 pb-1 [scrollbar-width:none]">
              {SCENICS.map((s) => {
                const on = scenic === s.id
                return (
                  <button
                    key={s.id}
                    onClick={() => { setScenic(s.id); autoAdvance() }}
                    className={cn(
                      'relative h-[128px] w-[150px] shrink-0 snap-start overflow-hidden rounded-3xl border transition duration-200 ease-[var(--ease-out)] active:scale-[0.97]',
                      on ? 'ring-2 ring-primary' : 'opacity-90 hover:opacity-100',
                    )}
                  >
                    <img
                      src={scenicPostcardSrc(s.id)}
                      alt={s.name}
                      width={150}
                      height={128}
                      loading="lazy"
                      decoding="async"
                      className="absolute inset-0 size-full object-cover"
                    />
                    <span className="absolute inset-x-0 bottom-0 h-14 bg-gradient-to-t from-black/60 to-transparent" />
                    <span className="absolute bottom-2.5 left-3 text-[14px] font-semibold text-white">{s.name}</span>
                    {on && (
                      <span className="absolute right-2 top-2 flex size-5 items-center justify-center rounded-full bg-primary text-primary-foreground shadow">
                        <Check className="size-3.5" />
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
            <p className="text-[12.5px] font-medium text-primary">{t('ob_guide_wait', { guide: guideName })}</p>
          </div>
        )}

        {/* ② 同伴（点选即跳）+ 第一次来（pill） */}
        {step === 2 && (
          <div className="anim-fade-up flex flex-col gap-5" style={{ animationDelay: '70ms' }}>
            <PillGroup q={t('ob_first_q')} options={FIRSTTIMES} icons={FIRSTTIME_ICONS} value={firstTime} onPick={setFirstTime} lang={lang} />
            <div className="grid grid-cols-2 gap-2.5">
              {GROUPS.map((gp) => (
                <OptionCard
                  key={gp.id}
                  icon={GROUP_ICONS[gp.id]}
                  label={gp.label[lang]}
                  on={groupType === gp.id}
                  onClick={() => { setGroupType(gp.id); autoAdvance() }}
                />
              ))}
            </div>
          </div>
        )}

        {/* ③ 节奏 + 出行方式（组合步，下一步） */}
        {step === 3 && (
          <div className="anim-fade-up flex flex-col gap-5" style={{ animationDelay: '70ms' }}>
            <CardGroup q={t('ob_pace_q')} options={PACES} icons={PACE_ICONS} value={pace} onPick={setPace} lang={lang} cols={3} />
            <CardGroup q={t('ob_mobility_q')} options={MOBILITIES} icons={MOBILITY_ICONS} value={mobility} onPick={setMobility} lang={lang} cols={2} />
          </div>
        )}

        {/* ④ 心情/目的（点选即跳）+ 年龄（pill） */}
        {step === 4 && (
          <div className="anim-fade-up flex flex-col gap-5" style={{ animationDelay: '70ms' }}>
            <PillGroup q={t('ob_age_q')} options={AGES} icons={AGE_ICONS} value={age} onPick={setAge} lang={lang} />
            <div className="grid grid-cols-2 gap-2.5">
              {PURPOSES.map((p) => (
                <OptionCard
                  key={p.id}
                  icon={PURPOSE_ICONS[p.id]}
                  label={p.label[lang]}
                  on={purpose === p.id}
                  onClick={() => { setPurpose(p.id); autoAdvance() }}
                />
              ))}
            </div>
          </div>
        )}

        {/* ⑤ 兴趣（多选） */}
        {step === 5 && (
          <div className="anim-fade-up flex flex-wrap gap-2" style={{ animationDelay: '70ms' }}>
            {INTERESTS.map((it) => {
              const on = interests.includes(it.id)
              const IIcon = INTEREST_ICONS[it.id]
              return (
                <button
                  key={it.id}
                  onClick={() => toggleInterest(it.id)}
                  className={cn(
                    'inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-[13.5px] font-medium transition duration-200 ease-[var(--ease-out)] active:scale-95',
                    on ? 'border-primary bg-primary text-primary-foreground shadow-sm shadow-primary/25' : 'bg-card text-foreground hover:border-primary/30',
                  )}
                >
                  {IIcon && <IIcon className={cn('size-4', !on && 'text-primary')} weight="duotone" />}
                  {it.label[lang]}
                  {on && <Check className="size-3.5" />}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* 底部行动区：仅组合步③=下一步、末步⑤=进入导览；点选即跳的步①②④无底栏，更利落 */}
      {(step === 3 || step === 5) && (
        <div className="sticky bottom-0 border-t bg-background/85 px-5 pb-[max(16px,env(safe-area-inset-bottom))] pt-3 backdrop-blur-xl">
          {step === 5 ? (
            <button
              onClick={onEnter}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-primary py-3.5 text-[15px] font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition duration-200 ease-[var(--ease-out)] hover:shadow-xl hover:shadow-primary/30 active:scale-[0.98]"
            >
              <Sparkle className="size-4" weight="duotone" /> {t('ob_enter')}
            </button>
          ) : (
            <button
              onClick={advance}
              className="flex w-full items-center justify-center gap-2 rounded-2xl bg-primary py-3.5 text-[15px] font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition duration-200 ease-[var(--ease-out)] hover:shadow-xl hover:shadow-primary/30 active:scale-[0.98]"
            >
              {t('ob_next')} <ArrowRight className="size-4" />
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// 进度点：当前步加宽高亮，已过步半亮，未到步灰
function ProgressDots({ total, current }: { total: number; current: number }) {
  return (
    <div className="flex items-center gap-1.5">
      {Array.from({ length: total }).map((_, i) => (
        <span
          key={i}
          className={cn(
            'h-1.5 rounded-full transition-all duration-300 ease-[var(--ease-out)]',
            i + 1 === current ? 'w-5 bg-primary' : i + 1 < current ? 'w-1.5 bg-primary/50' : 'w-1.5 bg-muted',
          )}
        />
      ))}
    </div>
  )
}

// 单选卡片：横排（默认）/ 竖排（compact，用于 3 列窄卡）
function OptionCard({ icon: Icon, label, on, onClick, compact }: {
  icon?: PhIcon; label: string; on: boolean; onClick: () => void; compact?: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex border transition duration-200 ease-[var(--ease-out)] hover:border-primary/30 active:scale-[0.98]',
        compact ? 'flex-col items-center gap-1.5 rounded-2xl px-2 py-3 text-center' : 'items-center gap-2.5 rounded-2xl p-3 text-left',
        on ? 'border-primary bg-primary/5 ring-1 ring-primary' : 'bg-card',
      )}
    >
      <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
        {Icon && <Icon className="size-[19px]" weight="duotone" />}
      </span>
      <span className={cn('font-medium', compact ? 'text-[12.5px]' : 'text-[13.5px]')}>{label}</span>
      {!compact && on && <Check className="ml-auto size-4 text-primary" />}
    </button>
  )
}

// 单选卡片组（带小标题）：组合步用，无自动跳
function CardGroup({ q, options, icons, value, onPick, lang, cols }: {
  q: string; options: Opt[]; icons: Record<string, PhIcon>
  value: string; onPick: (id: string) => void; lang: Lang; cols: number
}) {
  return (
    <div className="flex flex-col gap-2.5">
      <h2 className="text-[13px] font-semibold text-muted-foreground">{q}</h2>
      <div className={cn('grid gap-2.5', cols === 3 ? 'grid-cols-3' : 'grid-cols-2')}>
        {options.map((o) => (
          <OptionCard key={o.id} icon={icons[o.id]} label={o.label[lang]} on={value === o.id} onClick={() => onPick(o.id)} compact={cols === 3} />
        ))}
      </div>
    </div>
  )
}

// 单选 pill 组（带小标题）：年龄 / 第一次来等"轻量补充维度"，不抢主选择的焦点
function PillGroup({ q, options, icons, value, onPick, lang }: {
  q: string; options: Opt[]; icons: Record<string, PhIcon>
  value: string; onPick: (id: string) => void; lang: Lang
}) {
  return (
    <div className="flex flex-col gap-2">
      <h2 className="text-[13px] font-semibold text-muted-foreground">{q}</h2>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => {
          const I = icons[o.id]
          const on = value === o.id
          return (
            <button
              key={o.id}
              onClick={() => onPick(o.id)}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full border px-3.5 py-2 text-[13px] font-medium transition duration-200 ease-[var(--ease-out)] active:scale-95',
                on ? 'border-primary bg-primary text-primary-foreground shadow-sm shadow-primary/25' : 'bg-card text-foreground hover:border-primary/30',
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
