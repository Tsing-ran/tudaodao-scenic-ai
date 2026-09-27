# 前端域规范（webapp/）——凡动本目录的窗口都遵守

> 窗口划分与归属见根 CLAUDE.md「多窗口协作协议」：前端**默认归窗口①全栈主力**；
> 窗口③（前端细磨）仅在契约稳定+纯 UI 活时按需启用，启用须在根进度日志登记
> `【前端窗口启用中】`，期间窗口①不碰前端。进度日志只追加不改写，干完一块立刻写。

## 边界

- ✅ 本域：`webapp/`、`miniprogram/`、`talk.html`、`test_mobile.html`、`test_ui.html`
- ❌ 窗口③启用时不碰：`backend/`、`bridge/`、`scripts/`、`docs/`
- ❌ **窗口③不启停任何服务**（服务/GPU 归窗口①独管，GPU 11.6G 必须串行）。
  要联调就 curl 现成端口；端口不通 → 在进度日志留言请窗口①拉起。

## 技术栈与命令

- React 19 + Vite + Tailwind v4 + shadcn/ui（`src/components/ui/`），TypeScript 严格模式。
- **图标 = Phosphor**（`@phosphor-icons/react`，2026-06-13 全局迁移，**禁 emoji 当图标**）：
  语义/内容图标用 `weight="duotone"`（同行人/兴趣/徽章/设施/情绪，注册表在 `src/lib/icons.tsx`），
  功能图标用默认 regular；颜色走 currentColor + 容器 `text-primary`/`text-sweet`。
  lucide-react 仅留给 shadcn ui 原语（select/sonner 内部 import，勿卸载）。
  Canvas（明信片）画不了 SVG 组件 → 徽章用文字胶囊。后端 `/tour/facilities` 的 `emoji`
  字段已弃用，前端按 `id` 查 `FACILITY_ICONS`。
- Node 不在系统 PATH：`export PATH=$HOME/.local/node/bin:$PATH`
- 类型检查：`npx tsc -b --noEmit`；构建：`npm run build`（产物 dist/，桥接和 FAQ 加载器优先读 dist）。
- 改完必须 tsc + build 双过再提交。

## 设计系统（用户审美，盲改会被打回）

- **现代极简风**：纯白底、细黑字、蓝色强调、柔和阴影；微交互克制（active:scale、200ms ease）。
- 设计 token 在 `src/index.css`（OKLCH CSS 变量）；景区主题色由 `GET /scenic/theme` 动态注入，
  **禁止硬编码任何景区名/导游名/主题色**（品牌「智游·导览」铁律，文案用 `{guide}` 占位）。
- **字体（2026-06-15 三端统一）**：英文/数字 = Geist Variable（`@fontsource-variable/geist`），
  中文 = **HarmonyOS Sans SC**（华为鸿蒙，免费商用，自托管 `public/fonts/*.woff2`，已 GB2312 子集化
  ~930KB/档×3 档 400/500/700）。字体栈 = `'Geist Variable','HarmonyOS Sans SC',sans-serif`（Latin 优先），
  `@font-face` 带 `unicode-range`（限 CJK 码位）+ `font-display:swap`。**目的=消除 iOS 苹方/安卓思源/桌面雅黑
  的中文字形差异**，三端同一份字形。woff2 由官方 TTF 经 `pyftsubset`（`uvx fonttools[woff]`）子集化得来；
  字重只打包 400/500/700，`font-semibold`(600) 浏览器自动取 700。改字体须同步重 build（dist/fonts/）。
- 已装 impeccable skill（~/.claude/skills），大改 UI 前可用其 rubric 自检防 AI slop。
- **入场/动效工具**（`index.css`）：`.anim-fade-up`（fade-up 0.65s `both` 填充，stagger 用
  inline `animationDelay`）、`halo-breathe`（呼吸光环）、`caret-blink`（打字机光标）。
  ⚠️ 全局 reduced-motion 块**必须同时清 `animation-delay`**（已加 `0ms !important`）——
  只清 duration 会让 `both` 填充的 stagger 元素卡在透明态。JS 侧动效（如打字机）自行读
  `matchMedia('(prefers-reduced-motion: reduce)')` 降级为静态。

## 关键结构

- `src/App.tsx`：主舞台（FLV/HLS 视频 + 覆盖层，video 全幅不透明——背景等视觉都在流里，前端垫图无效）；
  开场 gate 读 `lingjing.onboarded`。**舞台 = 16:9 模糊填充**（`aspect-video w-full`，临时方案）：Ditto 流为 720×1280
  竖版，裁进横框头偏大，故前景视频 `object-contain` 居中（完整、头不偏大、零裁切）+ 背景 `<canvas ref={bgCanvasRef}>`
  抽帧（rAF ~11fps 把流 cover 画进 384×216）→ CSS `scale-[1.18] blur-2xl` 铺满两侧。**z 层**：前景 video `relative z-10`
  压住 canvas/scrim，故状态徽章/未连接遮罩/meta pills 必须 `z-20`、L1 成片 `z-30`（漏了会遮住连接按钮）。
  ⚠️根治在【需窗口①】横版底板：到位后前景改回 `object-cover` 即满幅无模糊边，可删 canvas 那段。
- `src/components/Onboarding.tsx`：**数字人迎宾式开场**（2026-06-12 重设计）——头像 hero + 呼吸光环、
  `useTypewriter` 打字机问候（内联本文件）、景区横滑实景卡（postcard 缩略图，点选实时换肤 +
  `{guide} 在这里等你` 动态导游名）。设置抽屉有「重看开场」入口（删 onboarded flag）。
- `src/components/`：AvatarSheet（**「形象工坊」**：①实时预览舞台 ②形象库·身份为主轴〔`fit` 命中 `SCENIC_STYLE_HINT` 浮顶〕③换装衣橱〔`SWEET_OUTFIT_IDS` 把 6 套 outfit 归到甜美脸；**未烘 `coming_soon` 形象只"试穿"不 `setAvatarPref`**，守桥接 AVATAR_MAP〕④AI 定制入口 ⑤音色试听〔读 `public/voice_samples/manifest.json` 决定显隐播放键，缺则零按钮零 404〕）、TourSheet、Postcard、GpsSheet 等抽屉组件。契约复用 `dhPresets/dhConfig`，无后端改动。
- `src/lib/api.ts`：全部后端类型与 fetch 封装（`/rag/*` 反代到 RAG :8000）；改接口契约先看 API_DOC.md。
- `miniprogram/`：微信原生小程序（纯自研 WXSS，appid 还是 touristappid 占位）。

## localStorage 键位（前缀 `lingjing.`，动持久化先查这张表防撞键）

| 键 | 值 | 写入方 |
|---|---|---|
| `onboarded` | `'1'` | App.enterApp（「重看开场」删除） |
| `scenic` / `group` / `lang` | id（非法值回落默认） | useGuide persist effect |
| `interests` | JSON string[] | useGuide persist effect |
| `age` / `pace` / `mobility` / `purpose` / `firsttime` | 自身情况标签 5 维（默认 youth/day/normal/relax/first，非法回落默认） | useGuide persist effect |
| `voice` / `avatar` | 音色/形象精调偏好（空=跟随景区默认） | useGuide setter |
| `dark` | 深色模式偏好 | theme.ts |

## 联调地址

本机一律用 localhost（系统代理 clash :12334 会劫持局域网 IP→502）；手机真机用 `hostname -I` 的局域网 IP。
