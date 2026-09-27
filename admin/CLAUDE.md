# 管理端大屏 · 协作改动说明（给 fuxiao 队友）

> 本目录是你的管理端大屏（Vue3+Vite，backend :6008 托管 dist，公网 :8443/admin）。
> 我方（数字人/RAG/游客端全栈）经你方授权动过少量代码，均**只增不改、已备份**，下面交代清楚。

## 2026-06-18 · 个性化「双面闭环」接入数据大屏（我方改）

**背景**：游客端新上线「为你定制」个性化推荐（画像×兴趣×此刻→带理由的推荐卡）。
为让大屏也能看到个性化洞察，做了双面闭环——游客端产数据，大屏这边展现。

**改了哪**（仅 `frontend/src/views/AdminView.vue`，已备份 `AdminView.vue.bak.reco`）：
1. `loadDashboard()` 的 `Promise.all` 加了一条 `safeFetch(.../analytics/reco-performance...)`，解构出 `reco`。
2. `kpiList` 加了 2 个 KPI：**推荐曝光**、**推荐点击率**（核心指标网格里，自动排版，没动模板/ECharts）。
3. 没动任何现有图表/接口；构建已过、`/admin` 回归 200。

**你可用的新数据端点**（经 `/cloud` 代理到我方 RAG，CORS/契约就绪）：
- `GET /cloud/analytics/profile?scenic_id=&days=` —— 客群画像（同行人/兴趣/语言分布）。
  ⚠️ 之前 interests 一直空，是因为游客端没传；现已修复，画像图会自然有数据了。你已在用此端点（客群画像图）。
- `GET /cloud/analytics/reco-performance?scenic_id=&days=` —— 个性化推荐效果。
  返回 `{impressions, clicks, ctr, top_recommendations{}, by_action{}}`。
  现在只接了 2 个 KPI，**如果你想做更丰富的板块**（如「热门推荐 Top5」柱图、点击率趋势），
  数据都在这个端点里，照你现有 ECharts 面板的写法加即可。

**想回滚**：`cp AdminView.vue.bak.reco AdminView.vue && ./node_modules/.bin/vite build`。

有问题随时找我（我方全栈窗口）。后续我方若再动你的代码，都会在本文件追加说明、并备份。
