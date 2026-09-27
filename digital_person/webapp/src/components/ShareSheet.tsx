import { useCallback, useEffect, useState } from 'react'
import {
  ShareNetwork, Copy, Check, ArrowClockwise, CircleNotch, QrCode, UsersThree,
} from '@phosphor-icons/react'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from '@/components/ui/drawer'
import { createHandoff, handoffQrUrl } from '@/lib/api'
import type { HandoffMsg } from '@/lib/api'
import type { Msg } from '@/hooks/useGuide'
import type { Situation } from '@/lib/i18n'

// 「邀请同伴 / 把导览带到另一台手机」：把本机对话+画像（含自身情况标签）打成短时接力码，
// 同伴扫码即接着逛（家人同游 / 换机续逛）。复用后端 /handoff，与大屏→手机同一机制。
export default function ShareSheet({
  open, onOpenChange, scenic, scenicName, groupType, lang, interests, voiceId, avatarPref, situation, messages,
}: {
  open: boolean; onOpenChange: (o: boolean) => void
  scenic: string; scenicName: string; groupType: string; lang: string
  interests: string[]; voiceId?: string; avatarPref?: string; situation?: Partial<Situation>; messages: Msg[]
}) {
  const [state, setState] = useState<'loading' | 'ready' | 'expired' | 'error'>('loading')
  const [token, setToken] = useState('')
  const [left, setLeft] = useState(0)
  const [copied, setCopied] = useState(false)
  const [msgCount, setMsgCount] = useState(0)

  const gen = useCallback(async () => {
    setState('loading'); setCopied(false)
    const hist: HandoffMsg[] = messages
      .filter((m) => !m.thinking && (m.text || '').trim())
      .slice(-40)
      .map((m) => ({ role: m.role, text: m.text, emotion: m.meta?.emotion, intent: m.meta?.intent }))
    const r = await createHandoff({ scenic, groupType, lang, interests, voiceId, avatarPref, situation, messages: hist, source: 'phone' })
    if (r.ok && r.token) {
      setToken(r.token); setLeft(r.expiresIn || 300); setMsgCount(r.msgCount ?? hist.length); setState('ready')
    } else setState('error')
  }, [scenic, groupType, lang, interests, voiceId, avatarPref, situation, messages])

  // 打开即生成（每次打开都拿一张新鲜的短时码）
  useEffect(() => { if (open) gen() }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  // 倒计时 → 归零即过期态（守公共扫码隐私 + 提示重新生成）
  useEffect(() => {
    if (state !== 'ready') return
    if (left <= 0) { setState('expired'); return }
    const id = setTimeout(() => setLeft((s) => s - 1), 1000)
    return () => clearTimeout(id)
  }, [state, left])

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`${location.origin}/?h=${token}`)
      setCopied(true); setTimeout(() => setCopied(false), 1800)
    } catch { /* 剪贴板不可用（非 HTTPS）→ 忽略，二维码仍可扫 */ }
  }
  const mm = Math.floor(left / 60)
  const ss = String(left % 60).padStart(2, '0')

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="mx-auto max-h-[92vh] max-w-[480px]">
        <DrawerHeader className="pb-1">
          <DrawerTitle className="flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <ShareNetwork className="size-[18px]" weight="duotone" />
            </span>
            邀请同伴一起逛
          </DrawerTitle>
        </DrawerHeader>
        <div className="px-5 pb-[max(24px,env(safe-area-inset-bottom))] pt-2">
          <p className="mb-4 flex items-start gap-2 text-[13.5px] leading-relaxed text-muted-foreground">
            <UsersThree className="mt-0.5 size-4 shrink-0 text-primary" weight="duotone" />
            <span>让同伴用手机扫一扫，立刻接着你的对话和偏好，一起逛<span className="font-medium text-foreground">{scenicName}</span>，TA 无需重新选择景区。</span>
          </p>

          {/* 二维码卡片 */}
          <div className="relative mx-auto flex aspect-square w-full max-w-[252px] items-center justify-center rounded-3xl border bg-card p-4 shadow-sm">
            {state === 'ready' ? (
              <img src={handoffQrUrl(token)} alt="接力二维码" className="size-full rounded-2xl object-contain" />
            ) : state === 'loading' ? (
              <div className="flex flex-col items-center gap-2 text-muted-foreground">
                <CircleNotch className="size-7 animate-spin" />
                <span className="text-[13px]">正在生成…</span>
              </div>
            ) : (
              <button onClick={gen} className="flex flex-col items-center gap-2 px-6 text-center text-muted-foreground transition active:scale-95">
                <ArrowClockwise className="size-7" />
                <span className="text-[13px] font-medium">
                  {state === 'expired' ? '二维码已过期，点此重新生成' : '生成失败，点此重试'}
                </span>
              </button>
            )}
          </div>

          {state === 'ready' && (
            <>
              <div className="mt-4 flex items-center justify-center gap-1.5 text-[12px] text-muted-foreground">
                <QrCode className="size-3.5 shrink-0" />
                <span>{msgCount > 0 ? `含 ${msgCount} 条对话 · ` : ''}景区·同行人·兴趣已打包 · {mm}:{ss} 后失效</span>
              </div>
              <button
                onClick={copy}
                className="mx-auto mt-4 flex items-center gap-2 rounded-full border bg-card px-4 py-2.5 text-[13.5px] font-medium shadow-sm transition duration-200 ease-[var(--ease-out)] hover:border-primary/30 active:scale-95"
              >
                {copied
                  ? (<><Check className="size-4 text-emerald-600" /> 已复制链接</>)
                  : (<><Copy className="size-4" /> 复制邀请链接</>)}
              </button>
            </>
          )}
        </div>
      </DrawerContent>
    </Drawer>
  )
}
