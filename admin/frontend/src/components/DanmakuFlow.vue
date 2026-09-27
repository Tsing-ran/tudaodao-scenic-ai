<template>
  <div ref="wrap" class="dmk" :class="variant === 'dark' ? 'dmk-dark' : 'dmk-light'"
       :style="{ height: lanes * laneH + 'px' }">
    <span v-for="p in pills" :key="p.id" class="dmk-pill" :class="'emo-' + p.tone"
          :style="{ top: p.lane * laneH + 2 + 'px', animationDuration: p.dur + 'ms', '--dmk-dist': p.dist + 'px' }"
          :title="p.title" @animationend="done(p.id)">
      <component :is="ICONS[p.intent] || ICONS.qa" :size="14" class="dmk-ico" aria-hidden="true" />
      <i class="dmk-txt">{{ p.text }}</i>
    </span>
  </div>
</template>

<script setup>
// 实时弹幕流「游客正在问」：/analytics/danmaku 轮询 + 题库兜底，纯 CSS transform 动画零逐帧计算。
// 轨道调度：每轨记录 busyUntil（前一条尾部完全入场的时刻），保证同轨永不追尾。
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { IconMessageCircle, IconMapPin, IconRoute, IconHeartHandshake, IconCamera } from '@tabler/icons-vue'

const props = defineProps({
  scenicId: { type: String, default: 'lingshan' },
  lanes:    { type: Number, default: 3 },
  variant:  { type: String, default: 'dark' },   // dark=大屏暗玻璃 / light=管理端浅色
  speed:    { type: Number, default: 90 },       // px/s
})

const ICONS = {
  qa: IconMessageCircle, navigation: IconMapPin, recommend: IconRoute,
  empathy: IconHeartHandshake, photo: IconCamera,
}
const TONE = { happy: 'pos', excited: 'pos', neutral: 'neu', curious: 'neu', empathetic: 'emp', apologetic: 'emp' }
const laneH = 33

const wrap = ref(null)
const pills = ref([])
let pool = []            // 全量素材（队列耗尽后洗牌循环，弹幕带永不空场）
let queue = []
let lastTs = null
let busyUntil = []
let pillSeq = 0
let tickTimer = null
let pollTimer = null
let nextEmitAt = 0

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

async function fetchItems(initial) {
  try {
    const p = new URLSearchParams({ scenic_id: props.scenicId, limit: initial ? '60' : '30' })
    if (!initial && lastTs) p.set('since', lastTs)
    const r = await fetch('/cloud/analytics/danmaku?' + p)
    const d = await r.json()
    const items = d.items || []
    for (const it of items) if (it.ts && (!lastTs || it.ts > lastTs)) lastTs = it.ts
    if (initial) { pool = items; queue = shuffle([...pool]) }
    else if (items.length) { queue.unshift(...items); pool.push(...items) }
    if (pool.length > 200) pool = pool.slice(-200)
  } catch { /* 静默降级：断网时靠现有 pool 循环 */ }
}

function tick() {
  const now = performance.now()
  if (now < nextEmitAt || document.hidden) return
  if (!queue.length) { if (pool.length) queue = shuffle([...pool]); else return }
  const w = wrap.value ? wrap.value.clientWidth : 0
  if (!w) return
  let lane = -1
  for (let i = 0; i < props.lanes; i++) if ((busyUntil[i] || 0) <= now) { lane = i; break }
  if (lane < 0) return
  const item = queue.shift()
  const pw = 50 + item.text.length * 14.5          // 估算胶囊宽：图标+内边距+字宽
  busyUntil[lane] = now + ((pw + 40) / props.speed) * 1000
  pills.value.push({
    id: ++pillSeq, lane,
    dur: Math.round(((w + pw) / props.speed) * 1000),
    dist: -Math.round(w + pw + 8),
    text: item.text, intent: item.intent, tone: TONE[item.emotion] || 'neu',
    title: item.ts ? `${item.text}（${item.ts.slice(5, 16)}）` : item.text,
  })
  if (pills.value.length > props.lanes * 8) pills.value.splice(0, pills.value.length - props.lanes * 8)
  nextEmitAt = now + 800 + Math.random() * 1500    // 节流投放：0.8~2.3s 一条
}

function done(id) {
  const i = pills.value.findIndex(p => p.id === id)
  if (i >= 0) pills.value.splice(i, 1)
}

onMounted(async () => {
  busyUntil = Array(props.lanes).fill(0)
  await fetchItems(true)
  tickTimer = setInterval(tick, 400)
  pollTimer = setInterval(() => fetchItems(false), 20000)
})
onBeforeUnmount(() => { clearInterval(tickTimer); clearInterval(pollTimer) })
</script>

<style>
/* 非 scoped（.dmk 前缀隔离）：需要 .admin-dark 祖先选择器命中，scoped 会拦掉 */
.dmk {
  position: relative; overflow: hidden; min-width: 0;
  -webkit-mask-image: linear-gradient(90deg, transparent 0, #000 22px, #000 calc(100% - 22px), transparent 100%);
  mask-image: linear-gradient(90deg, transparent 0, #000 22px, #000 calc(100% - 22px), transparent 100%);
}
.dmk-pill {
  position: absolute; left: 100%;
  display: inline-flex; align-items: center; gap: 6px;
  height: 28px; padding: 0 12px 0 10px; border-radius: 999px;
  white-space: nowrap; font-size: 13.5px;
  animation: dmk-run linear forwards; will-change: transform;
}
.dmk-pill:hover { animation-play-state: paused; cursor: default; z-index: 3; }
.dmk-txt { font-style: normal; }
.dmk-ico { flex-shrink: 0; }
@keyframes dmk-run { to { transform: translateX(var(--dmk-dist)); } }

/* 暗玻璃（大屏投放模式） */
.dmk-dark .dmk-pill {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.10);
  color: rgba(235, 240, 255, 0.92);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
}
.dmk-dark .emo-pos .dmk-ico { color: #2DD4BF; }
.dmk-dark .emo-neu .dmk-ico { color: #FBBF24; }
.dmk-dark .emo-emp .dmk-ico { color: #C084FC; }

/* 浅色（管理端顶栏迷你条，azure 系） */
.dmk-light .dmk-pill {
  background: #FFFFFF;
  border: 1px solid #E5EFFD;
  color: #4B5563;
  box-shadow: 0 1px 3px rgba(23, 43, 77, 0.06);
}
.dmk-light .emo-pos .dmk-ico { color: #0FA98D; }
.dmk-light .emo-neu .dmk-ico { color: #D97706; }
.dmk-light .emo-emp .dmk-ico { color: #9333EA; }

/* 管理端深色主题下的迷你条 */
.admin-dark .dmk-light .dmk-pill {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 255, 0.10);
  color: #B6BECF;
  box-shadow: none;
}

@media (prefers-reduced-motion: reduce) {
  .dmk { display: none; }
}
</style>
