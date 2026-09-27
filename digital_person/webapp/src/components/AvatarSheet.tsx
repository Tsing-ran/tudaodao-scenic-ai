import { useEffect, useMemo, useRef, useState } from 'react'
import {
  UserCircle, SpeakerHigh, ArrowCounterClockwise, Clock, Mountains,
  MagicWand, TShirt, Play, Pause, CaretRight, CheckCircle, Sparkle,
} from '@phosphor-icons/react'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerClose } from '@/components/ui/drawer'
import { X } from '@phosphor-icons/react'
import * as api from '@/lib/api'
import type { AvatarPreset, VoicePreset, BackgroundPreset, DhConfig } from '@/lib/api'
import { EMO_META } from '@/lib/icons'
import { isLipVetted } from '@/lib/avatarWhitelist'
import { cn } from '@/lib/utils'

interface Props {
  open: boolean; onOpenChange: (o: boolean) => void
  scenic: string
  voiceId: string; setVoiceId: (v: string) => void
  avatarPref: string; setAvatarPref: (a: string) => void
  // 切换过渡：通知父组件在主舞台盖过渡层（新形象立绘），POST 结束再淡出回直播
  onSwitchStart?: (p: AvatarPreset) => void
  onSwitchDone?: (ok: boolean) => void
  // 直播音量渐变（App 在抽屉打开时已压到 0 给本地样音让路）。本组件里凡是让数字人真开口的动作
  // 都得自己抬回来，凡是播本地样音的动作都得先压下去——两者必须成对，否则不是没声就是双声道打架。
  rampVolume: (target: number, ms?: number) => void
}

type GenderFilter = 'all' | 'female' | 'male'
type StyleTab = '推荐' | '现代' | '古风' | '民族'
const STYLE_TABS: StyleTab[] = ['推荐', '现代', '古风', '民族']

// face16 甜美脸的换装变体——后端 presets 暂无 identity 分组字段，前端按约定把这批 id 归入
// 甜美脸的「衣橱」（移出形象库网格）。后端日后加 base/identity 字段可平滑替换此常量（已留【需窗口①】）。
const SWEET_BASE_ID = 'female_sweet'
const SWEET_OUTFIT_IDS = ['outfit_qipao', 'outfit_hanfu', 'outfit_blazer', 'outfit_ethnic', 'outfit_vest', 'outfit_coat']
const SWEET_FAMILY = new Set([SWEET_BASE_ID, ...SWEET_OUTFIT_IDS])

// 景区风格倾向（启发式：给「为本景区推荐」浮顶/徽章用，零后端依赖）
const SCENIC_STYLE_HINT: Record<string, StyleTab> = {
  lingshan: '古风', nihuawan: '古风', gugong: '古风', xihu: '古风', huangshan: '现代',
}
// 舞台底部「会随对话切换表情」提示用的三态（呼应 RAG [情绪:X] → Ditto 表情条件）
const STAGE_EMOS: (keyof typeof EMO_META)[] = ['neutral', 'happy', 'concerned']

export default function AvatarSheet({ open, onOpenChange, scenic, voiceId, setVoiceId, avatarPref, setAvatarPref, onSwitchStart, onSwitchDone, rampVolume }: Props) {
  const [avatars, setAvatars] = useState<AvatarPreset[]>([])
  const [voices, setVoices] = useState<VoicePreset[]>([])
  const [backgrounds, setBackgrounds] = useState<BackgroundPreset[]>([])
  const [cfg, setCfg] = useState<DhConfig | null>(null)
  const [styleTab, setStyleTab] = useState<StyleTab>('推荐')
  const [gender, setGender] = useState<GenderFilter>('all')
  const [focusId, setFocusId] = useState('')      // 舞台聚焦的形象（默认=当前生效，点卡/试穿即变）
  const [aiOpen, setAiOpen] = useState(false)     // AI 定制面板展开
  const [playing, setPlaying] = useState('')      // 正在试听的音色 id
  const [switching, setSwitching] = useState('')  // 正在热切的形象 id（直播换形象中）
  const [liveAvatarId, setLiveAvatarId] = useState('')
  const [notice, setNotice] = useState<{ tone: 'ok' | 'warn'; text: string } | null>(null)
  const [sampleIds, setSampleIds] = useState<Set<string>>(new Set())  // 已就位的样音（manifest 列出，控制播放键显隐）
  const audioRef = useRef<HTMLAudioElement | null>(null)
  // AI 定制：描述 → 万相人景一体生成 → 即时入库可驱动
  const [genPrompt, setGenPrompt] = useState('')
  const [genGender, setGenGender] = useState<'female' | 'male'>('female')
  const [genBusy, setGenBusy] = useState(false)
  const [genErr, setGenErr] = useState('')
  // 景区身份语境（名 + 类型标签，来自 /scenic/theme）→ 工坊抬头「为〈故宫·博物展陈〉配置专属数字人」
  const [scenicMeta, setScenicMeta] = useState<{ name: string; typeLabel: string }>({ name: '', typeLabel: '' })

  // 当前生效：游客精调优先，否则管理端景区默认
  const activeAvatar = avatarPref || cfg?.avatar_id || ''
  // 唇形体检门（与 kiosk 同规则）：未过体检的形象不可切换（防上镜唇形坍缩）；
  // 当前生效 / 景区默认放行（已在用，不破坏），其余未体检者置灰只可预览。
  const lipLocked = (a: AvatarPreset) => !isLipVetted(a.id) && a.id !== cfg?.avatar_id && a.id !== activeAvatar
  const activeVoice = voiceId || cfg?.voice_id || ''
  const customized = Boolean(avatarPref || voiceId)
  // 本景区专属身份（后端身份库 dh_<scenic>，scenic 字段绑定）= 浮顶 + 「本景区专属」徽章的真值来源
  const boundAvatar = useMemo(() => avatars.find((a) => a.scenic === scenic && !a.coming_soon), [avatars, scenic])
  const recoStyle = boundAvatar?.style ?? SCENIC_STYLE_HINT[scenic]

  useEffect(() => {
    if (!open) return
    // 游客端按景区过滤（生产者/消费者分离）：灵山模式只见与灵山有关的已发布形象
    api.dhPresets(scenic, 'visitor')
      .then((p) => { setAvatars(p.avatars.filter((a) => !a.legacy)); setVoices(p.voices); setBackgrounds(p.backgrounds ?? []) })
      .catch(() => {})
    api.dhConfig(scenic).then(setCfg).catch(() => {})
    api.getTheme(scenic)
      .then((t) => setScenicMeta({ name: (t.name || '').split('·')[0], typeLabel: t.type_label ?? '' }))
      .catch(() => {})
  }, [open, scenic])

  // 开抽屉 / 生效形象变化 → 舞台聚焦回到当前生效形象（试穿不改 activeAvatar，故不会被打断）
  useEffect(() => { if (open) setFocusId(activeAvatar) }, [open, activeAvatar])

  // 样音清单（窗口①异步交付）：读 manifest 决定哪些音色显示播放键。manifest 缺失/为空 → 无播放键，
  // 界面干净不留死按钮、零 404 噪音（沿用项目 faq/manifest.json 约定）。窗口①补样音时更新此清单即生效。
  useEffect(() => {
    if (!open) return
    let alive = true
    fetch('/voice_samples/manifest.json')
      .then((r) => (r.ok ? r.json() : []))
      .then((ids: string[]) => { if (alive) setSampleIds(new Set(Array.isArray(ids) ? ids : [])) })
      .catch(() => {})
    return () => { alive = false }
  }, [open])

  // 形象库网格只放「独立身份」（甜美换装移交衣橱）；按风格 tab + 性别筛，命中本景区风格者浮顶
  const identities = useMemo(
    () => avatars.filter((a) => !SWEET_OUTFIT_IDS.includes(a.id)),
    [avatars],
  )
  const shown = useMemo(() => {
    const list = identities.filter((a) =>
      (styleTab === '推荐' ? a.recommended : a.style === styleTab) &&
      (gender === 'all' || a.gender === gender),
    )
    // 本景区专属身份浮到最顶，其次风格命中本景区者——精确而非笼统
    const rank = (a: AvatarPreset) => (a.id === boundAvatar?.id ? 2 : a.style === recoStyle ? 1 : 0)
    return [...list].sort((a, b) => rank(b) - rank(a))
  }, [identities, styleTab, gender, recoStyle, boundAvatar])

  // 甜美脸衣橱：base + 6 套换装（按 SWEET_OUTFIT_IDS 顺序）
  const sweetWardrobe = useMemo(() => {
    const byId = new Map(avatars.map((a) => [a.id, a]))
    return [SWEET_BASE_ID, ...SWEET_OUTFIT_IDS].map((id) => byId.get(id)).filter(Boolean) as AvatarPreset[]
  }, [avatars])

  const focus = useMemo(() => avatars.find((a) => a.id === focusId), [avatars, focusId])
  const focusIsSweet = SWEET_FAMILY.has(focusId)
  const bg = backgrounds.find((b) => b.id === (cfg?.background_id || '')) || null
  // 展示名优先艺名（文艺平实），回落形象原名
  const dispName = (a?: AvatarPreset | null) => a?.stage_name || a?.name || ''
  const showNotice = (tone: 'ok' | 'warn', text: string) => {
    setNotice({ tone, text })
    window.setTimeout(() => {
      setNotice((cur) => (cur?.text === text ? null : cur))
    }, 3200)
  }

  // 热切直播形象并把选中态落到 nextPref（恢复默认时 nextPref=''）。
  // liveSetAvatar 内部吞掉异常、恒 resolve 成 {ok:false}，所以成败只能看 ok 字段——挂 .catch 是够不到的死分支。
  // 失败必须回滚 nextPref：avatarPref 全链路只被本组件的热切消费，connect 时并不会补切，
  // 留着一个切不上去的偏好等于给用户一句永远不会兑现的「下次生效」。
  // 回滚后 focusId 由 activeAvatar 的 effect 自动跟回，无需在此手动设。
  const switchLive = (a: AvatarPreset, nextPref: string, okText: string) => {
    const prev = avatarPref
    setAvatarPref(nextPref)
    setSwitching(a.id)
    onSwitchStart?.(a)   // 主舞台盖过渡层（新形象立绘），承接热切的几秒
    api.liveSetAvatar(a.id, scenic)
      .then((r) => {
        if (r.ok) {
          setLiveAvatarId(a.id)
          showNotice('ok', okText)
        } else {
          setAvatarPref(prev)
          setLiveAvatarId('')
          showNotice('warn', '换不上，数字人可能还没连上，仍是原来的形象')
        }
        onSwitchDone?.(r.ok)
      })
      .finally(() => setSwitching((s) => (s === a.id ? '' : s)))
  }

  // 提交一个形象：未烘（coming_soon）/ 唇形未过体检只更新舞台做「试穿」；已烘 → 落 avatarPref +
  // **热拔插**立即换上直播形象（不重连，~1s）。
  const pick = (a: AvatarPreset) => {
    setFocusId(a.id)
    if (a.coming_soon) {
      showNotice('warn', '该形象正在烘焙中，当前仅支持预览')
      return
    }
    if (lipLocked(a)) {
      showNotice('warn', '该形象唇形待体检，暂不可切换（仅预览）')
      return
    }
    switchLive(a, a.id, `已换上「${dispName(a)}」`)
  }
  // 清本地偏好只是「不再覆盖景区默认」，直播里那张脸还是刚换的那个——必须真把直播切回景区默认，
  // 否则提示说「已恢复」而画面纹丝不动。默认形象不在已发布列表里时（拿不到 preset）只能退回清偏好。
  const reset = () => {
    setVoiceId('')
    setPlaying('')
    audioRef.current?.pause()
    const def = cfg?.avatar_id ? avatars.find((a) => a.id === cfg.avatar_id) : undefined
    if (!def || !avatarPref || avatarPref === cfg?.avatar_id) {
      setAvatarPref('')
      setLiveAvatarId('')
      showNotice('ok', '已恢复景区默认形象与声音')
      return
    }
    switchLive(def, '', `已恢复景区默认 · 「${dispName(def)}」`)
  }
  const chooseVoice = (v: VoicePreset) => {
    setVoiceId(v.id)
    showNotice('ok', `已选择「${v.name}」，下一句讲解使用该声音`)
    // 立即用新音色让数字人开口一句 → 换声「所听即所得」（step 4 更强的确认镜头）。
    // 未连接时 liveSay 静默失败，不影响。
    audioRef.current?.pause(); setPlaying('')   // 样音与这句确认二选一，不叠着响
    api.liveSay('你好呀，我现在换成这个声音为你讲解，喜欢吗？', scenic, 'happy', v.id)
    // 抽屉打开时直播音被压到了 0，而这句确认要 2-3.5s 才到——不在这里抬回来就是「试听有声、选中无声」。
    rampVolume(1, 200)
  }

  // AI 定制：生成 → 新形象加入库 + 舞台预览。**不热切上身**：新底板尚未过 lipmatrix 开口体检，
  // 未体检底图驱动会嘴部坍缩，白名单是唯一的闸——这里绕过去就等于把风险直接推上镜头。
  const handleGenerate = async () => {
    if (genBusy) return
    setGenBusy(true); setGenErr('')
    const r = await api.generateAvatar({
      prompt: genPrompt.trim(), scenic_id: scenic, gender: genGender,
      style: recoStyle && recoStyle !== '推荐' ? recoStyle : '现代',
    })
    setGenBusy(false)
    if (!r.ok || !r.avatar) { setGenErr(r.detail || '生成失败，请稍后重试'); return }
    setAvatars((prev) => [r.avatar!, ...prev])
    setGenPrompt('')
    setFocusId(r.avatar.id)   // 只上舞台预览
    showNotice('ok', `「${dispName(r.avatar)}」已加入形象库 · 通过唇形体检后即可上身`)
  }

  const toggleSample = (id: string) => {
    const el = audioRef.current
    if (!el) return
    if (playing === id) { el.pause(); setPlaying(''); return }
    rampVolume(0, 150)   // 与 chooseVoice 的抬回成对：样音期间压住直播音，否则两路声音叠着响
    el.src = `/voice_samples/${id}.mp3`
    el.play().then(() => setPlaying(id)).catch(() => {
      setSampleIds((p) => { const n = new Set(p); n.delete(id); return n }); setPlaying('')
    })
  }

  return (
    <Drawer open={open} onOpenChange={onOpenChange}>
      <DrawerContent className="mx-auto max-h-[92vh] max-w-[480px]">
        <DrawerHeader className="relative pb-1">
          <DrawerClose aria-label="关闭" className="absolute right-3 top-2 z-10 flex size-8 items-center justify-center rounded-full bg-muted text-muted-foreground transition active:scale-90">
            <X className="size-4" />
          </DrawerClose>
          <DrawerTitle className="flex items-center gap-2.5 pr-9">
            <span className="flex size-8 items-center justify-center rounded-xl bg-primary/10 text-primary">
              <UserCircle className="size-[18px]" weight="duotone" />
            </span>
            形象工坊
            {customized && (
              <button onClick={reset} className="ml-auto inline-flex items-center gap-1 rounded-full bg-muted px-2.5 py-1 text-[12px] font-medium text-muted-foreground active:scale-95">
                <ArrowCounterClockwise className="size-3" /> 恢复景区默认
              </button>
            )}
          </DrawerTitle>
          {scenicMeta.typeLabel && (
            <p className="mt-1 flex items-center gap-1.5 text-[12px] text-muted-foreground">
              <span className="font-medium text-foreground">{scenicMeta.name}</span>
              <span className="rounded bg-primary/10 px-1.5 py-px text-[11px] font-medium text-primary">{scenicMeta.typeLabel}</span>
              <span>· 为该景区配置专属数字人</span>
            </p>
          )}
        </DrawerHeader>

        <div className="overflow-y-auto px-4 pb-[max(20px,env(safe-area-inset-bottom))] pt-1">
          {notice && (
            <div className={cn(
              'mb-2 rounded-xl px-3 py-2 text-[12.5px] font-medium',
              notice.tone === 'ok' ? 'bg-primary/[0.08] text-primary' : 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
            )}>
              {notice.text}
            </div>
          )}

          {/* —— A. 实时预览舞台 —— */}
          <div className="relative overflow-hidden rounded-3xl border bg-card">
            {/* 背景层：景区场景预览（轻虚化 + 压暗）；缺图回落主色柔光 */}
            <div className="absolute inset-0">
              {bg?.preview
                ? <img src={bg.preview} alt="" className="size-full scale-110 object-cover blur-[2px]" />
                : <div className="size-full bg-gradient-to-br from-primary/25 to-primary/5" />}
              <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-black/25 to-black/10" />
            </div>
            {/* 前景：聚焦形象立绘 + 呼吸光环 */}
            <div className="relative flex items-end gap-3.5 px-4 pb-3.5 pt-6">
              <div className="relative shrink-0">
                <div className="absolute -inset-2 rounded-[1.6rem] bg-primary/30 blur-2xl motion-safe:animate-[halo-breathe_3.6s_var(--ease-out)_infinite]" />
                {focus?.preview && (
                  <img
                    src={focus.preview} alt={focus.name}
                    className="relative h-32 w-[104px] rounded-[1.4rem] object-cover object-top shadow-lg shadow-black/30 ring-1 ring-white/35"
                  />
                )}
              </div>
              <div className="min-w-0 flex-1 pb-0.5 text-white">
                <div className="flex items-center gap-1.5">
                  <span className="truncate text-[17px] font-semibold tracking-tight drop-shadow">{focus ? dispName(focus) : '选择你的向导'}</span>
                  {focus?.age && <span className="shrink-0 rounded bg-white/20 px-1.5 text-[10px] backdrop-blur-sm">{focus.age}</span>}
                </div>
                {focus && <div className="mt-0.5 truncate text-[12.5px] text-white/85 drop-shadow">{focus.name}{focus.persona ? ` · ${focus.persona}` : ''}</div>}
                {/* 音色 + 表情条 */}
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-2 py-0.5 text-[11px] backdrop-blur-sm">
                    <SpeakerHigh className="size-3" weight="duotone" />
                    {voices.find((v) => v.id === activeVoice)?.name || '默认音色'}
                  </span>
                  <span className="inline-flex items-center gap-1 rounded-full bg-white/15 px-2 py-0.5 text-[11px] backdrop-blur-sm">
                    {STAGE_EMOS.map((e) => { const M = EMO_META[e]; const I = M.Icon; return <I key={e} className="size-3" weight="duotone" /> })}
                    随对话切换表情
                  </span>
                </div>
              </div>
              {/* 右上徽章：本景区专属（绑定身份）优先，否则景区默认 */}
              <div className="absolute right-3 top-3 flex flex-col items-end gap-1">
                {focus && focus.id === boundAvatar?.id
                  ? <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-medium text-primary-foreground shadow">本景区专属</span>
                  : focus && focus.id === cfg?.avatar_id && (
                      <span className="rounded-full bg-white/85 px-2 py-0.5 text-[10px] font-medium text-foreground shadow">景区默认</span>
                    )}
              </div>
            </div>
          </div>
          {/* 舞台状态语 */}
          {focus?.coming_soon
            ? <p className="mt-2 flex items-center gap-1.5 rounded-xl bg-amber-500/10 px-3 py-2 text-[12.5px] text-amber-700 dark:text-amber-400">
                <Clock className="size-3.5 shrink-0" /> 试穿预览 · 此造型即将上线，正在烘焙中
              </p>
            : switching && switching === focus?.id
              ? <p className="mt-2 flex items-center gap-1.5 rounded-xl bg-primary/[0.07] px-3 py-2 text-[12.5px] text-primary">
                  <Sparkle className="size-3.5 shrink-0 motion-safe:animate-pulse" weight="duotone" /> 正在为你换上「{dispName(focus)}」…
                </p>
              : avatarPref && focus?.id === avatarPref
                ? <p className="mt-2 flex items-center gap-1.5 rounded-xl bg-primary/[0.07] px-3 py-2 text-[12.5px] text-primary">
                    <CheckCircle className="size-3.5 shrink-0" weight="duotone" />
                    {/* 偏好存在 localStorage 里、connect 时并不会自动补切，故重进页面只能说「再点一次」，不能许诺自动生效 */}
                    {liveAvatarId === focus.id ? '已换上 · 直播画面已切换为此形象' : '已选择 · 再点一次可为直播换上'}
                  </p>
                : null}

          {/* —— B. 形象库（身份为主轴）—— */}
          <div className="mb-2 mt-5 text-[13px] font-semibold text-muted-foreground">形象 · 身份</div>
          <div className="flex items-center gap-1 rounded-full bg-muted p-1">
            {STYLE_TABS.map((s) => (
              <button key={s} onClick={() => setStyleTab(s)}
                className={cn('flex-1 rounded-full py-1.5 text-[12.5px] font-medium transition duration-200 ease-[var(--ease-out)]',
                  styleTab === s ? 'bg-card text-foreground shadow-sm' : 'text-muted-foreground')}>
                {s}
              </button>
            ))}
          </div>
          <div className="mb-2.5 mt-2 flex gap-1.5">
            {([['all', '全部'], ['female', '女'], ['male', '男']] as [GenderFilter, string][]).map(([id, label]) => (
              <button key={id} onClick={() => setGender(id)}
                className={cn('rounded-full border px-3 py-1 text-[12px] font-medium transition duration-200 ease-[var(--ease-out)] active:scale-95',
                  gender === id ? 'border-primary bg-primary text-primary-foreground' : 'bg-card')}>
                {label}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            {shown.map((a) => {
              const active = a.id === activeAvatar
              const focused = a.id === focusId
              const isDefault = a.id === cfg?.avatar_id
              const isBound = a.id === boundAvatar?.id   // 本景区专属身份（精确绑定）
              const locked = !a.coming_soon && lipLocked(a)   // 唇形待体检：置灰只可预览
              return (
                <button
                  key={a.id}
                  onClick={() => pick(a)}
                  className={cn('group relative overflow-hidden rounded-2xl border text-left transition duration-200 ease-[var(--ease-out)] active:scale-[0.98]',
                    active ? 'border-primary ring-2 ring-primary' : focused ? 'border-primary/60 ring-1 ring-primary/40' : 'bg-card hover:border-primary/35')}
                >
                  <div className="relative aspect-[4/5] w-full overflow-hidden bg-secondary">
                    {a.preview && (
                      <img src={a.preview} alt={a.name} loading="lazy"
                        className={cn('size-full object-cover object-top', (a.coming_soon || locked) && 'grayscale-[0.4]')} />
                    )}
                    {a.persona && (
                      <span className="absolute bottom-1.5 left-1.5 rounded-full bg-black/55 px-2 py-0.5 text-[10.5px] font-medium text-white backdrop-blur-sm">{a.persona}</span>
                    )}
                    {isBound && <span className="absolute left-1.5 top-1.5 rounded-full bg-primary px-1.5 py-0.5 text-[9.5px] font-medium text-primary-foreground shadow-sm">本景区专属</span>}
                    {!isBound && isDefault && !a.coming_soon && <span className="absolute left-1.5 top-1.5 rounded-full bg-background/90 px-1.5 py-0.5 text-[9.5px] font-medium text-foreground shadow-sm backdrop-blur">景区默认</span>}
                    {a.coming_soon && (
                      <span className="absolute left-1.5 top-1.5 inline-flex items-center gap-0.5 rounded-full bg-background/90 px-1.5 py-0.5 text-[9.5px] font-medium text-muted-foreground shadow-sm backdrop-blur">
                        <Clock className="size-2.5" /> 即将上线
                      </span>
                    )}
                    {locked && !isBound && !isDefault && (
                      <span className="absolute left-1.5 top-1.5 inline-flex items-center gap-0.5 rounded-full bg-background/90 px-1.5 py-0.5 text-[9.5px] font-medium text-muted-foreground shadow-sm backdrop-blur">
                        <Clock className="size-2.5" /> 唇形待体检
                      </span>
                    )}
                  </div>
                  <div className="px-2.5 py-2">
                    <div className="flex items-center gap-1.5">
                      <span className="truncate text-[13px] font-semibold">{dispName(a)}</span>
                      {a.age && <span className="shrink-0 rounded bg-muted px-1 text-[10px] text-muted-foreground">{a.age}</span>}
                    </div>
                    <div className="mt-1 truncate text-[10.5px] text-muted-foreground">{a.name}{a.fit ? ` · ${a.fit}` : ''}</div>
                  </div>
                </button>
              )
            })}
            {!shown.length && <p className="col-span-2 py-6 text-center text-[13px] text-muted-foreground">该分类下暂无形象</p>}
          </div>

          {/* —— C. 换装衣橱（聚焦甜美脸时出现，坐实「形象可配置服装」）—— */}
          {focusIsSweet && sweetWardrobe.length > 1 && (
            <>
              <div className="mb-1 mt-5 flex items-center gap-1.5 text-[13px] font-semibold text-muted-foreground">
                <TShirt className="size-4" weight="duotone" /> 换装衣橱
              </div>
              <p className="mb-2 text-[11.5px] text-muted-foreground">同一位向导，多套服装 · 一键切换造型</p>
              <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                {sweetWardrobe.map((a) => {
                  const focused = a.id === focusId
                  const locked = !a.coming_soon && lipLocked(a)
                  return (
                    <button key={a.id} onClick={() => pick(a)}
                      className={cn('group relative w-16 shrink-0 snap-start overflow-hidden rounded-xl border transition duration-200 ease-[var(--ease-out)] active:scale-95',
                        focused ? 'border-primary ring-2 ring-primary' : 'bg-card hover:border-primary/40')}>
                      <div className="relative aspect-[3/4] overflow-hidden bg-secondary">
                        {a.preview && <img src={a.preview} alt={a.outfit || a.name} loading="lazy" className={cn('size-full object-cover object-top', (a.coming_soon || locked) && 'grayscale-[0.4]')} />}
                        {(a.coming_soon || locked) && <span className="absolute right-1 top-1 inline-flex items-center justify-center rounded-full bg-background/90 p-0.5 text-muted-foreground shadow-sm backdrop-blur"><Clock className="size-2.5" /></span>}
                      </div>
                      <div className="truncate px-1 py-1 text-center text-[10.5px] font-medium">{a.outfit || a.name}</div>
                    </button>
                  )
                })}
              </div>
            </>
          )}

          {/* —— D. AI 定制形象入口（自研亮点）—— */}
          <button onClick={() => setAiOpen((v) => !v)}
            className="mt-5 flex w-full items-center gap-3 rounded-2xl border border-primary/30 bg-primary/[0.04] p-3.5 text-left transition duration-200 ease-[var(--ease-out)] hover:bg-primary/[0.07] active:scale-[0.99]">
            <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary/12 text-primary">
              <MagicWand className="size-5" weight="duotone" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-[14px] font-semibold">生成你的专属向导</span>
              <span className="block truncate text-[12px] text-muted-foreground">一句话描述 · AI 当场生成「人景一体」形象，加入你的形象库</span>
            </span>
            <CaretRight className={cn('size-4 shrink-0 text-muted-foreground transition-transform duration-200', aiOpen && 'rotate-90')} />
          </button>
          {aiOpen && (
            <div className="mt-2 rounded-2xl border bg-card p-3.5">
              <p className="mb-2.5 flex items-start gap-1.5 text-[12.5px] leading-relaxed text-muted-foreground">
                <Sparkle className="mt-0.5 size-3.5 shrink-0 text-primary" weight="duotone" />
                <span>自研流程：<span className="text-foreground">描述向导形象 → 万相文生图「人景一体」生成 → 落盘可驱动底板 → 唇形体检</span>，生成后即刻加入形象库、上方舞台可预览。</span>
              </p>
              {/* 性别 */}
              <div className="mb-2 flex gap-1.5">
                {(['female', 'male'] as const).map((gd) => (
                  <button key={gd} onClick={() => setGenGender(gd)} disabled={genBusy}
                    className={cn('flex-1 rounded-lg border py-1.5 text-[12.5px] transition active:scale-[0.99] disabled:opacity-50',
                      genGender === gd ? 'border-primary bg-primary/[0.06] text-primary' : 'text-muted-foreground')}>
                    {gd === 'female' ? '女向导' : '男向导'}
                  </button>
                ))}
              </div>
              <textarea value={genPrompt} onChange={(e) => setGenPrompt(e.target.value)} disabled={genBusy}
                rows={2} maxLength={60}
                placeholder="如：身着米色针织衫、温柔亲切的年轻女导游"
                className="w-full resize-none rounded-lg border bg-background px-2.5 py-2 text-[16px] outline-none transition focus:border-primary/50 disabled:opacity-50" />
              <button onClick={handleGenerate} disabled={genBusy}
                className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-2.5 text-[13.5px] font-semibold text-primary-foreground transition active:scale-[0.99] disabled:opacity-60">
                {genBusy
                  ? <><span className="size-3.5 animate-spin rounded-full border-2 border-primary-foreground/40 border-t-primary-foreground" /> 生成中 · 约 30 秒…</>
                  : <><MagicWand className="size-4" weight="duotone" /> 生成并加入形象库</>}
              </button>
              {genErr && <p className="mt-1.5 text-[11.5px] text-destructive">{genErr}</p>}
              <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground">新向导会带着「唇形待体检」标记进入形象库：先在舞台预览，体检通过后即可切换上身——这道体检是为了保证它开口说话时的口型自然。同一句描述会生成一位全新的向导。</p>
            </div>
          )}

          {/* —— 场景背景（按景区自动，只读展示）—— */}
          {bg?.id && (
            <>
              <div className="mb-2 mt-5 flex items-center gap-1.5 text-[13px] font-semibold text-muted-foreground">
                <Mountains className="size-4" weight="duotone" /> 场景背景
              </div>
              <div className="flex items-center gap-3 rounded-xl border bg-card px-3 py-2.5">
                {bg.preview && <img src={bg.preview} alt={bg.name} loading="lazy" className="h-12 w-9 shrink-0 rounded-lg object-cover" />}
                <span className="text-[14px] font-medium">{bg.name}</span>
                <span className="ml-auto shrink-0 rounded-full bg-muted px-2 py-0.5 text-[10.5px] text-muted-foreground">随景区自动</span>
              </div>
            </>
          )}

          {/* —— E. 音色试听 —— */}
          <div className="mb-2 mt-5 flex items-center gap-1.5 text-[13px] font-semibold text-muted-foreground">
            <SpeakerHigh className="size-4" weight="duotone" /> 声音
            <span className="font-normal">· 点选即刻生效</span>
          </div>
          {(['female', 'male'] as const).map((gd) => {
            const list = voices.filter((v) => v.gender === gd)
            if (!list.length) return null
            return (
              <div key={gd} className="mb-2.5">
                <div className="mb-1.5 text-[11.5px] text-muted-foreground">{gd === 'female' ? '女声' : '男声'}</div>
                <div className="flex flex-col gap-1.5">
                  {list.map((v) => {
                    const active = v.id === activeVoice
                    const isDefault = v.id === cfg?.voice_id
                    const canPlay = sampleIds.has(v.id)
                    return (
                      <div key={v.id}
                        className={cn('flex items-center gap-2.5 rounded-xl border px-3 py-2.5 transition duration-200 ease-[var(--ease-out)]',
                          active ? 'border-primary bg-primary/[0.05] ring-1 ring-primary/30' : 'bg-card')}>
                        {canPlay && (
                          <button onClick={() => toggleSample(v.id)} aria-label={playing === v.id ? '暂停试听' : '试听'}
                            className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary transition active:scale-90">
                            {playing === v.id ? <Pause className="size-3.5" weight="fill" /> : <Play className="size-3.5" weight="fill" />}
                          </button>
                        )}
                        <button onClick={() => chooseVoice(v)} className="flex min-w-0 flex-1 items-center gap-2.5 text-left active:scale-[0.99]">
                          <span className={cn('size-2 shrink-0 rounded-full', active ? 'bg-primary' : 'bg-muted-foreground/25')} />
                          <span className="shrink-0 text-[14px] font-medium">{v.name}</span>
                          <span className="truncate text-[12px] text-muted-foreground">{v.tone}</span>
                          {isDefault && <span className="ml-auto shrink-0 rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">景区默认</span>}
                        </button>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
        <audio ref={audioRef} className="hidden" onEnded={() => setPlaying('')} onError={() => setPlaying('')} />
      </DrawerContent>
    </Drawer>
  )
}
