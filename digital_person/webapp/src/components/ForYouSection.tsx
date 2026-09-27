import { Sparkle, MaskHappy, Camera, ForkKnife, PersonSimpleWalk, FlowerLotus, Armchair, CaretRight, SlidersHorizontal } from '@phosphor-icons/react'
import type { Icon } from '@phosphor-icons/react'
import type { RecoCard } from '@/lib/api'
import { Skeleton } from '@/components/ui/skeleton'

// 推荐卡 icon 关键词 → Phosphor 图标
const ICONS: Record<string, Icon> = {
  theater: MaskHappy, photo: Camera, food: ForkKnife, walk: PersonSimpleWalk, temple: FlowerLotus, rest: Armchair, star: Sparkle,
}

// 「为你定制」个性化推荐区：画像×兴趣×此刻 → 带「为什么推荐你」理由 + 依据 chip 的推荐卡。
// 这是把后台隐形的个性化变成游客「看得见、懂我」的高光；点卡 → 问导游/开路线/开设施。
export default function ForYouSection({ cards, basis, loading, onCard, onEditProfile, disabled }: {
  cards: RecoCard[]
  basis: string[]
  loading: boolean
  onCard: (card: RecoCard) => void
  onEditProfile?: () => void
  disabled?: boolean   // 语音录音中禁用点选，避免与 VAD 结束后的提问重叠（双重 ask）
}) {
  if (!loading && cards.length === 0) return null
  return (
    <section className="anim-fade-up">
      <div className="mb-2 flex items-center gap-2 px-0.5">
        <Sparkle className="size-[18px] text-primary" weight="duotone" />
        <span className="text-[15px] font-semibold tracking-tight">为你定制</span>
        {/* 可点画像 chip：显示当前依据（亲子·历史），点开调整 → 推荐重算 */}
        {onEditProfile && (
          <button
            onClick={onEditProfile}
            className="ml-auto inline-flex max-w-[62%] items-center gap-1 rounded-full border px-2.5 py-1 text-[11px] font-medium text-muted-foreground transition duration-200 hover:border-primary/30 hover:text-primary active:scale-95"
          >
            <span className="truncate">{basis.length > 0 ? basis.slice(0, 3).join(' · ') : '设置画像'}</span>
            <SlidersHorizontal className="size-3 shrink-0" />
          </button>
        )}
      </div>
      <div className="flex flex-col gap-2">
        {loading && cards.length === 0
          ? [0, 1].map((i) => <Skeleton key={i} className="h-[68px] rounded-2xl" />)
          : cards.map((c, i) => {
            const Ico = ICONS[c.icon] || Sparkle
            return (
              <button
                key={`${c.title}-${i}`}
                onClick={() => onCard(c)}
                disabled={disabled}
                className="group flex items-center gap-3 rounded-2xl border bg-card px-3 py-2.5 text-left shadow-sm transition duration-200 ease-[var(--ease-out)] hover:border-primary/30 hover:bg-accent/30 active:scale-[0.98] disabled:opacity-50 disabled:active:scale-100"
              >
                <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary/15">
                  <Ico className="size-[20px]" weight="duotone" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-[14.5px] font-semibold">{c.title}</span>
                  <span className="mt-0.5 block text-[12.5px] leading-snug text-muted-foreground line-clamp-2">{c.reason}</span>
                  {c.basis.length > 0 && (
                    <span className="mt-1 flex flex-wrap gap-1">
                      {c.basis.slice(0, 3).map((b) => (
                        <span key={b} className="rounded-full bg-primary/[0.07] px-1.5 py-0.5 text-[10px] font-medium text-primary">{b}</span>
                      ))}
                    </span>
                  )}
                </span>
                <CaretRight className="size-4 shrink-0 text-muted-foreground/50 transition group-hover:translate-x-0.5 group-hover:text-primary" />
              </button>
            )
          })}
      </div>
    </section>
  )
}
