import { useEffect, useState } from 'react'
import { Globe, TextAa, Sun, Moon, CircleHalf, UserCircle, CaretRight, ArrowCounterClockwise, NavigationArrow, HandWaving, Eraser, Warning, CheckCircle, X } from '@phosphor-icons/react'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer'
import { LANGS, makeT } from '@/lib/i18n'
import type { Lang } from '@/lib/i18n'
import type { DarkMode } from '@/lib/theme'
import { cn } from '@/lib/utils'

// 复位入口的文案就地维护：makeT 对未知 key 会原样吐出 key 名，而本条目又只此一处用到，
// 不值得为它扩 i18n 全局字典；四语齐全，避免切语言时本行成为唯一的中文孤岛。
const RESET_T: Record<Lang, { title: string; sub: string; warn: string; cancel: string; ok: string; done: string }> = {
  zh: {
    title: '重置足迹与勋章',
    sub: '清空到访记录与已获得的勋章，重新开始收集',
    warn: '到访记录和已获得的勋章会被清空，你的明信片也会随之变空。此操作无法撤销。',
    cancel: '取消', ok: '确认重置', done: '已重置',
  },
  en: {
    title: 'Reset trail & badges',
    sub: 'Clear visited places and earned badges, start collecting again',
    warn: 'Your visited places and earned badges will be cleared, and your postcard will be emptied too. This cannot be undone.',
    cancel: 'Cancel', ok: 'Reset', done: 'Reset done',
  },
  ja: {
    title: '足跡とバッジをリセット',
    sub: '訪問記録と獲得バッジを消して、集め直す',
    warn: '訪問記録と獲得したバッジが消去され、絵はがきも空になります。この操作は取り消せません。',
    cancel: 'キャンセル', ok: 'リセット', done: 'リセットしました',
  },
  ko: {
    title: '발자취·배지 초기화',
    sub: '방문 기록과 획득한 배지를 지우고 다시 모으기',
    warn: '방문 기록과 획득한 배지가 지워지고, 엽서도 비워집니다. 이 작업은 되돌릴 수 없습니다.',
    cancel: '취소', ok: '초기화', done: '초기화됨',
  },
}

interface Props {
  open: boolean; onOpenChange: (o: boolean) => void
  lang: Lang; setLang: (l: Lang) => void
  elder: boolean; setElder: (e: boolean) => void
  autoNarrate: boolean; setAutoNarrate: (v: boolean) => void
  dark: DarkMode; setDark: (m: DarkMode) => void
  onOpenAvatar: () => void
  onReplay: () => void
  onEndTour: () => void
  onResetTrace: () => void
}

export default function SettingsSheet({ open, onOpenChange, lang, setLang, elder, setElder, autoNarrate, setAutoNarrate, dark, setDark, onOpenAvatar, onReplay, onEndTour, onResetTrace }: Props) {
  const t = makeT(lang)
  const rt = RESET_T[lang] ?? RESET_T.zh
  const [confirming, setConfirming] = useState(false)
  const [resetDone, setResetDone] = useState(false)
  // 抽屉每次关闭都解除「已按下待确认」态：否则下次打开时确认按钮已就位，一次误触即清空足迹。
  useEffect(() => { if (!open) { setConfirming(false); setResetDone(false) } }, [open])
  // 复位是纯本地操作、界面上无任何别处可见的变化（且全局未挂 Toaster）→ 行内回执一次，
  // 否则点完像没反应，用户会重复点。
  useEffect(() => {
    if (!resetDone) return
    const id = setTimeout(() => setResetDone(false), 2400)
    return () => clearTimeout(id)
  }, [resetDone])
  const MODES: { id: DarkMode; label: string; icon: React.ReactNode }[] = [
    { id: 'light', label: t('mode_light'), icon: <Sun className="size-4" weight="duotone" /> },
    { id: 'dark', label: t('mode_dark'), icon: <Moon className="size-4" weight="duotone" /> },
    { id: 'system', label: t('mode_system'), icon: <CircleHalf className="size-4" weight="duotone" /> },
  ]
  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="mx-auto max-w-[480px]">
        <DrawerHeader className="relative">
          <DrawerClose aria-label="关闭" className="absolute right-3 top-3 z-10 flex size-8 items-center justify-center rounded-full bg-muted text-muted-foreground transition active:scale-90">
            <X className="size-4" />
          </DrawerClose>
          <DrawerTitle>{t('set_title')}</DrawerTitle>
        </DrawerHeader>
        <div className="flex flex-col gap-5 px-4 pb-[max(20px,env(safe-area-inset-bottom))]">
          {/* 数字人形象（管理端默认 + 游客精调） */}
          <button
            onClick={() => { onOpenChange(false); onOpenAvatar() }}
            className="flex items-center gap-3 rounded-xl border bg-card p-3.5 text-left transition duration-200 ease-[var(--ease-out)] hover:border-primary/30 active:scale-[0.99]"
          >
            <UserCircle className="size-5 text-primary" weight="duotone" />
            <span className="flex-1">
              <span className="block text-sm font-medium">{t('set_avatar')}</span>
              <span className="block text-[12px] text-muted-foreground">{t('set_avatar_sub')}</span>
            </span>
            <CaretRight className="size-4 text-muted-foreground" />
          </button>

          {/* 重看开场（重新选景区与偏好） */}
          <button
            onClick={() => { onOpenChange(false); onReplay() }}
            className="flex items-center gap-3 rounded-xl border bg-card p-3.5 text-left transition duration-200 ease-[var(--ease-out)] hover:border-primary/30 active:scale-[0.99]"
          >
            <ArrowCounterClockwise className="size-5 text-primary" weight="duotone" />
            <span className="flex-1">
              <span className="block text-sm font-medium">{t('ob_replay')}</span>
              <span className="block text-[12px] text-muted-foreground">{t('ob_replay_sub')}</span>
            </span>
            <CaretRight className="size-4 text-muted-foreground" />
          </button>

          {/* 语言 */}
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center gap-2 text-[13px] font-semibold text-muted-foreground">
              <Globe className="size-4" /> {t('set_lang')}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {LANGS.map((l) => (
                <button
                  key={l.id}
                  onClick={() => setLang(l.id)}
                  className={cn('rounded-xl border px-4 py-3 text-sm font-medium transition duration-200 ease-[var(--ease-out)] active:scale-[0.98]',
                    lang === l.id ? 'border-primary bg-primary text-primary-foreground shadow-sm shadow-primary/25' : 'bg-card hover:border-primary/30')}
                >
                  {l.label}
                </button>
              ))}
            </div>
          </div>

          {/* 外观（深色模式） */}
          <div className="flex flex-col gap-2.5">
            <div className="flex items-center gap-2 text-[13px] font-semibold text-muted-foreground">
              <CircleHalf className="size-4" /> {t('set_appearance')}
            </div>
            <div className="grid grid-cols-3 gap-2">
              {MODES.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setDark(m.id)}
                  className={cn('flex flex-col items-center gap-1.5 rounded-xl border py-3 text-[13px] font-medium transition duration-200 ease-[var(--ease-out)] active:scale-[0.97]',
                    dark === m.id ? 'border-primary bg-primary text-primary-foreground shadow-sm shadow-primary/25' : 'bg-card hover:border-primary/30')}
                >
                  {m.icon}{m.label}
                </button>
              ))}
            </div>
          </div>

          {/* 适老模式 */}
          <button
            onClick={() => setElder(!elder)}
            className="flex items-center gap-3 rounded-xl border bg-card p-3.5 text-left active:scale-[0.99]"
          >
            <TextAa className="size-5 text-primary" weight="duotone" />
            <span className="flex-1 text-sm font-medium">{t('set_elder')}</span>
            <span className={cn('relative h-6 w-11 shrink-0 rounded-full transition duration-200 ease-[var(--ease-out)]', elder ? 'bg-primary' : 'bg-muted')}>
              <span className={cn('absolute top-0.5 size-5 rounded-full bg-white shadow transition-all duration-200 ease-[var(--ease-out)]', elder ? 'left-[22px]' : 'left-0.5')} />
            </span>
          </button>

          {/* 走到景点自动讲解（地理围栏主动开讲） */}
          <button
            onClick={() => setAutoNarrate(!autoNarrate)}
            className="flex items-center gap-3 rounded-xl border bg-card p-3.5 text-left active:scale-[0.99]"
          >
            <NavigationArrow className="size-5 shrink-0 text-primary" weight="duotone" />
            <span className="flex-1">
              <span className="block text-sm font-medium">{t('set_autonarrate')}</span>
              <span className="block text-[12px] leading-snug text-muted-foreground">{t('set_autonarrate_sub')}</span>
            </span>
            <span className={cn('relative h-6 w-11 shrink-0 rounded-full transition duration-200 ease-[var(--ease-out)]', autoNarrate ? 'bg-primary' : 'bg-muted')}>
              <span className={cn('absolute top-0.5 size-5 rounded-full bg-white shadow transition-all duration-200 ease-[var(--ease-out)]', autoNarrate ? 'left-[22px]' : 'left-0.5')} />
            </span>
          </button>

          {/* 结束导览：温暖收尾 = 数字人个性化道别 + 弹出电子明信片 */}
          <button
            onClick={() => { onOpenChange(false); onEndTour() }}
            className="flex items-center gap-3 rounded-xl border border-primary/30 bg-primary/[0.04] p-3.5 text-left transition duration-200 ease-[var(--ease-out)] hover:bg-primary/[0.07] active:scale-[0.99]"
          >
            <HandWaving className="size-5 shrink-0 text-primary" weight="duotone" />
            <span className="flex-1">
              <span className="block text-sm font-medium">{t('end_tour')}</span>
              <span className="block text-[12px] leading-snug text-muted-foreground">{t('end_tour_sub')}</span>
            </span>
            <CaretRight className="size-4 text-muted-foreground" />
          </button>

          {/* 重置足迹与勋章：破坏性且不可撤销（明信片直接读 trace 渲染）→ 必须是语义明确的独立入口 +
              二次确认。刻意不并进「重看开场」：那个入口的既定语义是「只重选偏好、保留足迹」。 */}
          <div className={cn('rounded-xl border p-3.5 transition duration-200 ease-[var(--ease-out)]',
            confirming ? 'border-destructive/40 bg-destructive/[0.07]' : 'border-destructive/25 bg-destructive/[0.03]')}>
            {resetDone ? (
              <div className="flex items-center gap-3">
                <CheckCircle className="size-5 shrink-0 text-emerald-600" weight="fill" />
                <span className="text-sm font-medium text-emerald-600">{rt.done}</span>
              </div>
            ) : confirming ? (
              <>
                <div className="flex items-start gap-3">
                  <Warning className="mt-0.5 size-5 shrink-0 text-destructive" weight="duotone" />
                  <p className="flex-1 text-[13px] leading-snug text-foreground">{rt.warn}</p>
                </div>
                <div className="mt-2.5 flex justify-end gap-2">
                  <button
                    onClick={() => setConfirming(false)}
                    className="rounded-full border px-3.5 py-1.5 text-[12px] font-medium text-muted-foreground transition duration-200 ease-[var(--ease-out)] active:scale-95"
                  >
                    {rt.cancel}
                  </button>
                  <button
                    onClick={() => { setConfirming(false); setResetDone(true); onResetTrace() }}
                    className="rounded-full bg-destructive/10 px-4 py-1.5 text-[12px] font-semibold text-destructive transition duration-200 ease-[var(--ease-out)] hover:bg-destructive/20 active:scale-95 dark:bg-destructive/20 dark:hover:bg-destructive/30"
                  >
                    {rt.ok}
                  </button>
                </div>
              </>
            ) : (
              <button
                onClick={() => setConfirming(true)}
                className="flex w-full items-center gap-3 text-left transition duration-200 ease-[var(--ease-out)] active:scale-[0.99]"
              >
                <Eraser className="size-5 shrink-0 text-destructive" weight="duotone" />
                <span className="flex-1">
                  <span className="block text-sm font-medium text-destructive">{rt.title}</span>
                  <span className="block text-[12px] leading-snug text-muted-foreground">{rt.sub}</span>
                </span>
                <CaretRight className="size-4 text-muted-foreground" />
              </button>
            )}
          </div>
        </div>
      </DrawerContent>
    </Drawer>
  )
}
