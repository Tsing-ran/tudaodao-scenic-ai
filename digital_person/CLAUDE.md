# 景区导览服务AI数字人 — 项目工作档案

## 赛事信息

- **赛事**：第十五届中国软件杯大赛（A组）
- **赛题**：景区导览服务AI数字人
- **出题企业**：锐捷网络（苏州）有限公司
- **答疑QQ群**：1093135039
- **示范景区**：灵山胜境（无锡）+ 拈花湾禅意小镇

---

## 团队与分工

| 成员 | 职责（2026-06-13 更新） |
|---|---|
| **本用户（我）** | 主体全栈：RAG/LLM + 数字人引擎 + 游客端手机网页/**APK** + **管理端手机 web** + 交付材料 |
| **队友** | 游客端**大屏 web**（景区立屏）+ 管理端**数据大屏 web**（我方提供接口联调：analytics 11 条 + dashboard.html 可交接）；另有队友 TTS 服务（CosyVoice :8001，曾接入） |

**Claude Code 角色**：技术导师 + 协作编程伙伴（随时在线）；窗口①兼 PM 事务（用户=产品 Owner/需求源；新想法走窗口① plan mode 评审；每次开工可问"今天最值得做什么"）

---

## 多窗口协作协议（2026-06-12 定稿：常态 2 窗，冲刺最多 3 窗）

> 划分依据：①GPU 11.6G 任务必须串行 → 后端+数字人引擎不可拆窗；②RAG↔桥接↔LiveTalking
> 联调是一条链，拆窗要人肉传话；③文档与代码零文件冲突且是当前最大剩余工作量 → 唯一无摩擦并行；
> ④瓶颈是用户的审查/决策带宽（盲评、口径、取舍都需人定），并行对话 2-3 个为上限。

> **作品总纲 = `docs/作品蓝图与冲刺路线.md`**（2026-06-13 头脑风暴定稿）：定位「游客扫码遇见金牌导游；
> 景区点击拥有数字员工」双面叙事；三幕演示视频结构；端侧环境感知引擎；2-3 周冲刺路线。各窗口优先级以它为准。

| 窗口 | 状态 | 地盘 | 当前优先（详见作品蓝图） |
|---|---|---|---|
| **① 全栈主力** | 常开 | `backend/ bridge/ scripts/ tests/ deploy/` + `~/Desktop/LiveTalking` 引擎改造；**唯一服务/GPU 管理者**；前端（`webapp/ miniprogram/`）**默认也归它** | W1: emotion→Ditto 表情条件、扫码即聊公网部署（ECS+HTTPS+FAQ 引导气泡）；W2: context snapshot 感知协议、家庭同游（同 session 二维码）、FAQ 真片（GPU）、APK（Capacitor 套壳）、tour/theme 补至 8 景区；W3: 真机 <5s 实测+压测 |
| **② 文档交付** | 常开 | `docs/` + PPT/演示视频脚本（**代码只读**） | W1: **三幕分镜脚本+台词最高优先**（逐镜头核对功能可录性，缺口反馈窗口①）+ 设计文档剩余章节；W3: 文档定稿→PPT→录制剪辑（≤7min） |
| **③ 前端细磨** | 按需（W2 启用） | `webapp/ miniprogram/ talk.html` + 管理端手机 web | W2: **管理端手机 web**（知识库管理/数字人配置/轻量洞察——「景区店长的口袋工作台」，重型大屏归队友）、罗盘指向性指路 overlay、地理围栏主动开讲+天气×位置便利。启用登记 `【前端窗口启用中】`，期间窗口①不碰前端；关闭删行 |

**铁律**：
1. 本「当前进度」日志 = 窗口间公告板，**只追加不改写别人条目**，干完一块立刻写；
2. 跨窗口需求写 `- [ ] 【需XX窗口】…` 留言，或由用户人肉粘贴一句话交接；
3. 服务（RAG :8000 / 桥接 :9000 / LiveTalking / SRS / ComfyUI）启停**只归窗口①**，GPU 任务必须串行；
4. 小步 commit 当通信，开工先 `git status + git log -5` 同步；
5. **想并行先派子 agent，不是开新窗**（同窗口内后台跑生成/下载/测试，协调成本为零）；
   开新窗只留给需要独立长期上下文的工作。大重构/实验用 `git worktree` 隔离。

各目录的域规范（**谁动该目录谁遵守，与窗口身份无关**）：`webapp/CLAUDE.md`、`backend/CLAUDE.md`、`docs/CLAUDE.md`。

---

## 系统核心设计原则

> 系统不绑定灵山景区，而是**插拔式知识库架构**：  
> 导入任意景区的知识库后，问答准确率须同样满足 ≥90% 的硬性指标。
>
> **品牌定位**：产品 = 通用智能景区管理方案，游客端品牌「**途叨叨**」（早期「智游·导览」已弃）。
> **UI 不得硬编码任何具体景区/导游名**——数字人**去人名化**，统一「<景区简称>AI智能导览数字人」（不再用慧昭/婉清等拟人名）；
> 景区名、导游名、主题色、路线、设施全部按 scenic_id 从后端动态取（`/scenic/theme` 带 `guide_name`，文案用 `{guide}` 占位）。详见 [[generic-product-positioning]]。

---

## 硬性指标（评审红线）

> ⚠️ 注意区分指标性质（按赛题原文精确措辞，勿拔高）：
> - **唯一带明确数值+测评方式的硬红线 = 准确率**："事实性问答的准确率**不低于90%**，由评审专家基于标准测试集评测"。
> - **延迟是"合理范围"的体验性要求，非定值红线**：赛题原文"系统稳定，**交互响应延迟应控制在合理范围内（如语音问答延迟<5秒）**，保证用户体验流畅"——归属**稳定性/流畅体验**维度（与"系统不应崩溃或长时间无响应"并列），"<5秒"是**举例（"如"）非评定值**，且主语是"交互响应延迟"泛指、非仅语音。我们把"语音问答<5秒"当**自定工程目标**对标即可，端到端度量口径（用户说完→数字人开口）亦为我方自定义。

- 问答准确率 **≥ 90%**（硬红线·专家基于标准测试集评测）
- 语音问答延迟 **< 5 秒**（赛题示例的"合理响应范围"，自定工程目标，非硬性定值）
- 口型同步 + 表情自然度（专家评估演示视频）
- 必须使用 **≥ 1 个多模态大模型**

---

## 技术架构概览

```
游客交互端
  语音输入 (faster-whisper) ─┐
  文本输入                   ├──► FastAPI 后端 ──► RAG 问答引擎 ──► LLM (qwen-plus/flash)
  数字人渲染窗口 (Ditto)    ◄─┘        │              │
  TTS 输出 (Qwen-TTS)                  │         ChromaDB (知识库)
                                       ▼
                              管理后台 / 数据大屏 (Vue)
                    知识库管理 | 数字人配置 | 情感分析 | 数据大屏
```

---

## 我的职责范围（LLM 负责人）

```
知识库工程
  ├── 文档解析 → 分块 → 向量化 → ChromaDB 存储
  ├── 检索策略（稠密检索 + 关键词混合）
  └── 多景区命名空间/collection 隔离设计

RAG 问答引擎
  ├── 检索-增强-生成全链路
  ├── 幻觉控制（召回为空时的兜底策略）
  └── 准确率保证工程

Prompt Engineering
  ├── 数字人导游人格设定
  ├── 个性化路线推荐逻辑
  └── 景区切换时 Prompt 自动适配

对外接口（给队友用）
  POST /chat       { session_id, message, scenic_id } → { reply, emotion }
  POST /kb/upload  上传文档，触发重新入库
  GET  /kb/list    查询当前知识库状态
```

---

## 技术选型（已确认）

| 模块 | 选型 | 说明 |
|---|---|---|
| **文本 LLM** | `qwen-plus`（事实问答）/ `qwen-flash`（路线·推荐·闲聊等生成性意图） | 按意图选模型：qa 守准确率、生成性意图提速。⚠️ `-latest` 滚动版 403，用稳定版 |
| **多模态 LLM** | `qwen3-vl-plus`（DashScope） | 满足赛题多模态硬性要求；视觉定位两段式图文问答 |
| **向量嵌入** | `BAAI/bge-m3`（本地，4080运行） | 中英双语，检索质量高，无API费用 |
| **重排序** | `BAAI/bge-reranker-v2-m3`（本地） | 提升召回精度，是90%准确率的关键 |
| **向量数据库** | ChromaDB（本地） | 多 collection 实现景区命名空间隔离 |
| **稀疏检索** | rank_bm25 | 与稠密检索混合，覆盖关键词精确匹配 |
| **语音识别** | **qwen3-asr-flash 云端优先** + faster-whisper small 本地兜底（2026-07-18 起） | 口音普通话/方言识别大模型，景区专名上下文偏置，0.63s/句；云端失败自动落回本地 whisper（0 显存 CPU），断网可用 |
| **语音合成** | **Qwen-TTS**（百炼，云端实时 0 显存） | 音色自然；CosyVoice2 曾接入、已退役 |
| **数字人驱动** | **LiveTalking + Ditto**（本地4080） | 全脸驱动 25.5fps/首帧 719ms/2.7G，`/human` 文字驱动接 RAG；MuseTalk 已退役 |
| **后端框架** | FastAPI（Python） | 用户已有基础 |
| **前端框架** | 游客端 React + Tailwind + shadcn；管理/大屏 Vue + Element Plus + ECharts | 队友大屏用 ECharts |
| **数据库** | SQLite（会话/分析） + ChromaDB（向量） | 初赛阶段足够 |

## 硬件配置（已确认）

- 设备：ROG 幻16
- GPU：RTX 4080 Laptop，11.6GB 显存
- 驱动：580.159.03，CUDA 13.0
- 本地可运行：BGE-M3、BGE-Reranker、faster-whisper（CPU）、LiveTalking+Ditto（仅 2.7G，TTS 走云端 Qwen-TTS 0 显存）

---

## 数据资产

| 文件 | 内容 | 用途 |
|---|---|---|
| `示范景区公开资料包/灵山胜境：历史、文化、景点特色与个性化游览指南.docx` | 历史、文化、6条路线、贴士 | RAG 主文档 |
| `示范景区公开资料包/灵山胜境 景点结构化数据集.docx` | 灵山+拈花湾景点结构化表（ID/位置/文化内涵/游玩亮点） | 精准问答知识 |
| `示范景区公开资料包/景点景区旅游数据行为分析数据.xlsx` | 游客行为数据（年龄/满意度/花费等） | 数据大屏 + 情感分析 |

---

## 开发路线（4周）

### Week 1：RAG 基础 + 灵山数据跑通
- 学习：向量嵌入、余弦相似度、RAG三步原理
- 实践：LangChain 把灵山文档入库，能回答一个问题

### Week 2：准确率工程 + Prompt 打磨
- 学习：RAG 出错的原因，分块策略，检索召回率
- 实践：手工构建 20 道测试题，准确率提到 90%+

### Week 3：景区泛化 + 管理接口
- 学习：多租户知识库设计
- 实践：能切换到另一个景区知识库，接口不变

### Week 4：联调 + 压测 + 演示视频
- 与队友全链路联调
- 优化延迟目标：整体 < 3 秒

---

## 初赛提交清单

- [ ] 产品源代码或可执行文件
- [ ] 部署和使用手册
- [ ] 总体设计文档
- [ ] 方案介绍 PPT（需求分析、方案设计、核心技术、创新点、演示、测试数据、团队介绍）
- [ ] 演示视频（≤7分钟，.avi/.mp4/.wmv）

---

## 本地开发环境

- **虚拟环境**：`.venv`（Python 3.11.11，Miniconda 来源）
- **激活**：`source /home/jiale/Desktop/Digital_Person/.venv/bin/activate`
- **安装依赖**：`~/.local/bin/uv pip install -r requirements.txt --index-url https://pypi.tuna.tsinghua.edu.cn/simple`
- **注意**：FlagEmbedding 须锁定 `==1.2.11` + `transformers==4.44.2`，高版本有 API 不兼容问题

## 公网部署（AutoDL 单网关）

- 入口：`ssh autodl`（免密，公钥 `digital_person`）；项目在 `/root/autodl-tmp/Digital_Person`。
- 服务由 supervisord 守护，6 个程序：`rag`/`bridge`/`livetalking_main`/`livetalking_portrait`/`srs`/`relay_hz`。
  - 重启 CPU 服务：`/root/miniconda3/bin/supervisorctl -c /root/autodl-tmp/supervisord.conf restart rag bridge`
  - **GPU 的 `livetalking_*` 必须串行、不可随意重启**；杀进程前先 `ps -o cmd= -p <PID>` 验明身份（用户会并行跑 SAM3 训练）。
  - 全栈拉起 `/root/autodl-tmp/dp_up.sh`，体检 `/root/autodl-tmp/preflight.sh`。
- 公网网关 `https://<实例token>.seetacloud.com:8443`（**token 开机/克隆会轮换，从 AutoDL 控制台取当前 URL**）。
- 详见 `docs/部署手册.md` §3 与记忆 [[deployment-strategy-autodl]]。⚠️ 阿里云 ECS `116.62.136.211` 已弃用（2026-06-14），不再使用/引用。

---

## 赛题需求对照（对标评审标准）

### 基本功能需求

| 赛题要求 | 实现状态 | 说明 |
|---|---|---|
| 语音输入 | ✅ | 自研 ASR `POST /asr`（qwen3-asr 云端口音增强 0.63s/句 + faster-whisper 本地兜底 + 景区专名偏置） |
| 文本输入 | ✅ | `POST /chat`（同步 + SSE 流式） |
| 数字人语音/表情/口型同步回答 | ✅ | Ditto 全脸驱动 + Qwen-TTS，桥接 `/live/ask*`、情绪→表情条件 |
| 智能问答（历史/文化/景点特色） | ✅ | RAG，准确率 97.1%（105 题，8 景区） |
| 个性化路线推荐 | ✅ | recommend 意图 + `/recommend` 带依据卡 |
| 知识库管理（上传/更新/维护） | ✅ | `/kb/upload`、`/kb/list`、`/kb/{id}`、`/kb/faq`、`/kb/text` |
| **数字人形象管理**（外观/声音配置） | ✅ | `GET/PUT /digital-human/config`、`/presets`、`/generate`、`/live/avatar` 热切 |
| 游客感受度报告 | ✅ | `POST /analytics/report`（LLM 生成） |
| 数据大屏概览 | ✅ | `/analytics/dashboard`、`bi/*`、`topic-intents`、`sentiment-trend`、`crowd` |

### 非功能性需求

| 赛题要求 | 实现状态 | 实测数据 |
|---|---|---|
| ≥1个多模态大模型 | ✅ | qwen3-vl-plus（`POST /chat/image` 视觉定位两段式） |
| 问答准确率 ≥ 90% | ✅ | 97.1%（105 题，8 景区；硬红线） |
| 语音问答延迟 < 5秒 | ✅ | 端到端 ~4.7s（自定工程目标，非硬红线） |
| 系统不崩溃/长时无响应 | ✅ | supervisor 守护 + 推流双向自愈 |
| (可选) GPS/位置感知 | ✅ | 端侧环境感知（地理围栏/罗盘/天气×位置） |

---

## 当前进度

- [x] **租空 AutoDL 二次复刻验证交付包 + 抓修 CRLF 致命 bug（2026-07-19，Windows 机，全新 4090D 实例，未碰生产机）**：用户租新机验证 `05015650源码.zip` 能否 100% 复刻。严格按 README 三条命令跑（评委视角，零内部知识）。**抓到会让评委 GPU 部署失败的真 bug**：`ops/` 4 个文件是 Windows CRLF 换行符（`setup_gpu.sh`＝致命/`relay_hz.sh`/`lipmatrix.sh`/`srs_dp.conf`）→ Linux bash 把行尾 `\r` 当命令内容 → `set -o pipefail\r` 非法/`source env.sh\r` 找不到/函数定义语法错 → deploy.sh 判「数字人引擎安装未完成」退出（逻辑后端不受影响，因 deploy.sh 本体是 LF；但 GPU 全栈必挂）。根因＝`core.autocrlf=true` 且无 `.gitattributes`。修：4 文件转 LF + 新增 `.gitattributes`（`*.sh *.bash *.conf text eol=lf`）+ 重打包三 zip（从 zip 读回确认 0 CRLF）。**修复后端到端全绿**：`unzip`→中文名完好、`bash deploy.sh`→✅含数字人、两路推流 active、桥接健康、**RAG 准确率 20/20=100%**、云端 ASR「灵山大佛有多高？」经 `/rag/asr` 转写正确+engine=cloud+1.13s、三端页面全 200。详见 [[delivery-bundle-and-secrets]]。

- [x] **HTTPS 证书续期保障（2026-07-19，Windows 机，仅 ECS）**：8443 证书 07-18 起已换成 **Let's Encrypt 正式 IP 证书**（`shortlived` 档 6 天有效期，必须自动续；评委浏览器不再弹自签警告）。核查=acme.sh 配置健全（webroot HTTP-01 走 80 口→装 `/etc/nginx/ssl/` →`nginx -s reload`，Bark 通知级别 2 续期成败都推）；**强制续期一次实证全链路无人值守可用**（新证书已上线，有效期至 07-25，ARI 排程 07-22 续）。加固：acme cron 每日 1 次→3 次（3:31/11:31/19:31，短命证书多留重试窗口）；tudaodao-monitor 加每小时兜底核查，证书剩余 <48h 推 timeSensitive 告警（附手动续期命令），已验证解析正确（159.0h）。

- [x] **Bark 访问通知误报修复 + 通知附 IP 归属地（2026-07-19，Windows 机，只改 ECS 监控脚本，零项目代码/服务变更）**：用户报「没人访问却几分钟一条通知」。取证=9h 收 16 个"访客"全是伪装 Mozilla UA 的扫描器（腾讯云/AWS/阿里云机房 IP 只 GET / 就走；杭州华数拨测每小时打 /+logo.png 轮换假 Chrome 版本号；beyke3d.cn 盗链镜像站定时拉我们 assets）——v1 只靠 UA 过滤挡不住。monitor.py v2 三层过滤：①行为确认（页面 GET 后 15s 内同 IP 拉 /assets/ 或 /rag/ /live/ /api/ 才算真人）②盗链 referer 过滤 ③ip-api.com 查 hosting/proxy=机房 IP 静默（免费中文接口，12h 缓存，查询失败放行）；通知 body 改「IP · 设备(微信/iPhone/安卓/电脑) · 省市 · 运营商」；启动自检正常时不再推送。三个吵闹 IP 逐一验证判定正确 + 模拟真人访问（手机流量 IP GET /+asset）收到带归属地推送。日常核对：`ssh hz-ecs tail /var/log/tudaodao-monitor.log`（通知/丢弃/静默各有一行记录）。

- [x] **语音输入去 VAD 自动断句，改纯手动「说完了」（2026-07-18，Windows 机，纯前端 build→服务器 dist，零服务重启；commit 3fd3531）**：用户判「自动断句会误判」拍板移除。`useGuide.ts` VAD 循环只保留电平柱/计时/recording 状态展示，删 SILENCE_HOLD/MIN_SPEECH 自动 stopVoice；安全上限 12s→30s（防忘停：说过话转写、没说过话丢弃）。UI 零改（「说完了/取消」双按钮本就在）。tsc+build 过，部署=tar 覆盖 `webapp/dist`（入口 `index-LkLyUTDj.js`，备份 `dist.bak_novad`，bridge 免重启）。**评委路径 E2E 复验 9/9×2**（四川话/京腔走公网网关）：同一份带静音垫的音频，旧版报「VAD 自动断句」、新版稳等「手动说完了」→ 转写上屏正确、engine=cloud、真答正确、零 pageerror = 改动生效且无回归。交付包 useGuide.ts+dist 已同步（覆盖后补回 1 处清洗词），两个 05015650 zip 已重打。

- [x] **游客端语音识别口音增强：云端 qwen3-asr 优先 + whisper 兜底（2026-07-18，Windows 机，仅重启 rag 未碰 GPU；commit e9a8375）**：用户要求「不标准普通话/各种口音都要像微信语音转文字一样准」。新增 `backend/asr/cloud_asr.py` = DashScope **qwen3-asr-flash**（ASR 大模型，口音普通话/方言/多语种原生覆盖；SCENIC_HOTWORDS+通用问询词作**上下文偏置**，容量远超 whisper hotwords 参数；enable_itn 数字归一化；线程池 4.5s 超时保护）；`transcriber.transcribe` 变统一入口 `ASR_PROVIDER=auto/cloud/local` 三档，auto=云端失败**静默落回本地 whisper**（断网可用、游客侧永不失败）；`/asr` 端点改 `run_in_threadpool`（旧代码 async def 里同步转写 1.1s 会阻塞事件循环拖慢并发问答，顺手治了）。**口音对比**（Qwen-TTS 口音音色 Cherry/Dylan京腔/Jada吴语/Sunny四川话合成 16 句灵山专名提问，服务器实跑）：**云端 14/16 vs 本地 5/16**；京腔/川普云端全对而本地翻成"九龙拐鱼集结/反攻怎么找追戒"；吴语 2 句差异里 1 句实为忠实转写方言词"小囡"（真方言，超出口音普通话范畴）；**云端平均 0.63s 比本地 ~1.6s 更快**，<5s 预算反而更宽；webm/opus 手机录音格式云端直收免转码。E2E：restart rag 后经桥接 `/rag/asr` 传 webm→`engine=cloud` 0.93s 转写正确；云端模型名故意配错→`engine=local` 兜底路径验证通过。测试沉淀 `tests/test_asr_accents.py`（云端≥12/16 门槛，本地仅对照）。API_DOC §1.8 已录（/asr 历史上竟从未入文档，一并补）；**作品源码交付包已同步 5 文件**（违禁痕迹词扫描 0 命中）+ 两个提交 zip 已重打（05015650作品 86.1M / 源码 81.6M）。坑：qwen-tts 基础版无方言音色（Dylan/Jada/Sunny 须 `qwen-tts-latest`）；TTS 限流需 6s 退避重试。**评委路径 E2E 已补**（同日）：Playwright 完整 chromium + iPhone UA 走**公网网关 https://114.55.178.51:8443/**（与二维码一致），getUserMedia 替身喂四川话/京腔口音音频→真 MediaRecorder→VAD 自动断句→真 /asr→**转写上屏逐字正确（含儿化"小孩儿"）、engine=cloud、数字人真答**（"九龙灌浴每天有四场。平日的演出时间是上午10点…"/"从景区入口进入后，沿着菩提大道…"），两口径 9/9、零 pageerror；iOS m4a/aac 格式经 /rag/asr 验证 engine=cloud 转写正确。答案断言用「答案才有的特征正则+剔除问题回显」防自证（第一版关键词命中回显=假阳性，已修）。**待办**：真人带口音真机抽验（TTS 口音音色为替身；真实麦克风硬件+iOS 权限流仍未覆盖）。

- [x] **手机端语音输入可终止/可核对 + 拍照回显（2026-07-15，Windows 机，未碰 GPU、未重启任何服务；webapp build→bridge dist，commit 9dc85bf，源码包已同步）**：用户报三症状，逐个改在成因上。**①「点了麦克风停不下来」**：`toggleVoice` 在录音态调的是 `stopVoice(false)`=**丢弃**，用户再点录音就没了，只能干等 VAD 或 12s 上限；而 VAD 要 500ms 静音才断句 → **景区嘈杂环境根本等不到 = 实际零出口**。修=拆 `finishVoice`(转写发送)/`cancelVoice`(丢弃)，录音条给「说完了」「取消」两个明确出口，recognizing 期间点击忽略防重入。**②「不知道被听成了什么」**：转写只当参数喂 `ask()`，**屏幕从不显示** → ASR 认错专有名词用户无从察觉（**实测真踩到：「九龙灌浴」→「九龙关于」**，热词没兜住关键专名，正是必须回显的理由）。修=新增 `heard` 状态 + 舞台「你说」徽章，**回答期间仍留在屏可持续核对**（旧版 location 与 question 是三元取一 → location 恒胜、问题永不显示，一并改成两者都渲染）；`Msg` 加 `voice` 标记 → 对话记录内语音提问带麦克风图标；录音条另给计时器 + **真实电平柱**（直接读 VAD 已算的 rms，不额外开分析器）。**③「拍了照看不到自己发的照片」**：`photo()` 只推一条「拍了一张照片」文字。修=`URL.createObjectURL` 存进 `Msg.image` → 舞台缩略图 + 对话记录内联，`photoUrlsRef` 卸载时统一 revoke 不泄漏 blob。**另修一个测试中暴露的真 bug**：mpegts `enableWorker` 下 worker 是 `blob:`、**没有可解析的 base URL** → 相对地址 `'/stream.flv'` 在 worker 内抛 `Failed to parse URL` → 改 `new URL('/stream.flv', location.href).href` 传绝对地址。**实测 19/19**（服务器真 chromium + iPhone 14 口径）：真 MediaRecorder→webm/opus→真 `/asr` 全链路，转写「灵山大佛有多高」正确、数字人作答「灵山大佛通高88米（」、照片缩略图 44x44 指向 `blob:`、计时器 00:03→00:05 真走动、电平柱 4 种波形、全程零 pageerror。**测试口径诚实交代**：本机 chromium **不支持 `--use-fake-device-for-media-capture`**（三种参数组合均 `NotFoundError`）→ 只把**设备层**换成 getUserMedia 替身喂真 TTS 人声（Web Audio→MediaStreamDestination），其上录音/VAD/编码/识别/应答**全是真的**；循环人声无静音间隔恰好复现嘈杂景区=VAD 不自动断句 → 证明「说完了」是唯一出口。**测试自身的两个假阳性已修**（后人注意）：`text=你说` 会误命中我自己的 banner「正在识别**你说**的话…」→ 改 `get_by_text("你说", exact=True)`+`following-sibling::span[1]`；计时器用全页正则 `\d{2}:\d{2}` 会命中别处的「开放时间 20:00」→ 改读录音条本体。部署=**仅静态替换 dist**（入口 `index-aQBARzYo.js`，备份 `dist.bak_voicephoto`），bridge 直接从磁盘服 `/` 免重启。**⚠️期间 rag/bridge 于 23:39:02 被外部 kill 重启（非我所为）**：supervisor 记为 `exited: ... not expected`（≠supervisorctl restart 的 `waiting for ... to stop`）、`oom_kill 0` 非 OOM、post-receive 钩子明写不重启且末次 pull 在 14:24、无 cron、uvicorn 无 `--reload` → 唯一交互会话是 AutoDL 网页控制台 `root pts/0`（18:19 起），判为窗口①手动重启（按协议本就归它）；`livetalking_main/portrait` 全程未动（uptime 2 天）、GPU 6506MiB 未变、流 200 正常，数字人服务零中断。**待办**：真机手测语音（headless 假麦无法覆盖真实麦克风硬件与 iOS Safari 权限流）。

- [ ] **【进行中·2026-07-15 收工存档】源码包容器化：部署手册 34 节 → 几条命令（Windows 机，全程只写文件，未 ssh/未起服务/未碰 GPU）**：目标=对标获奖作品「装 docker → unzip → docker compose up -d」的简洁度。**已完成并静态验证**：`作品源码/docker-compose.yml`（7 服务：档位 A 的 rag/admin_api/bridge 三容器共用一个镜像只换 command，对外只开 6006；档位 B 的 srs/trt-build/livetalking_main/portrait 挂 `--profile gpu`）、`docker/Dockerfile.app`、`docker/Dockerfile.gpu`、`docker/trt_build.sh`、`.dockerignore`。**代码改动（唯一一处，已 py_compile + 语义验证）**：管理端 5 个文件写死 `http://127.0.0.1:6006/rag`（`admin/backend/main.py:42`、`routers/{admin_chat,digital_human,knowledge,scenic}_router.py:8/31`）→ 容器内 127.0.0.1 指向管理端自己而非桥接层，**多容器下 /admin 整个后端代理必挂**；改为 `os.environ.get("ADMIN_RAG_BASE", <原值>)`，**默认值不变 → 原生 ops/*.sh 路径行为零变化**。**关键取证（都写进了文件注释，勿再踩）**：①`bridge/server.py:1440` 的 `_BUNDLE_ROOT` 往上三级找同级目录 → 容器内必须保持 `/app` = 源码包根的目录结构，不能只拷 digital_person/；②`backend/core/config.py:28` 的 `deploy_mode` 默认是 **local**、`.env.example` 也写 local → 必须显式 `DEPLOY_MODE=cloud`（compose 的 environment 优先级高于 env_file，已实测）；③`config.py:58` + `db/database.py:18` → `vector_store_dir.parent` 一个变量驱动 **5 个写路径**（向量库/conversations.db/custom_avatars/backgrounds/staging），故设 `VECTOR_STORE_DIR=/app/data/vector_store` 把它们收进单个命名卷 `dp_data`，**并把预构建向量库 COPY 到 /app/data/vector_store 让卷首次创建时自动灌入**（本机用 Python 3.14+pydantic_settings 2.14.2 实跑 6 条断言全 PASS 验证了这套 env 绑定与优先级）；④`analytics_bi.py:14` 的 `_PKG` 是 `__file__` 推导、**无环境变量可改** → 16MB 赛题 xlsx 必须落在 `/app/digital_person/示范景区公开资料包/`，**源码包原有的 digital_person/Dockerfile 没拷它 → BI 接口本来就是坏的**，新镜像已修并在构建期预热 `behavior_data.pkl`（治「首次请求 24s／并发挤爆线程池」老坑）；⑤`admin/frontend/dist` 只有 `dist/admin/index.html`、**没有 dist/index.html**（桥接层 `_find_entry` 已兼容）；⑥Python 选 **3.11-slim 不是 3.12**（与已验证的 venv 3.11.11 + 原 Dockerfile 一致；requirements 多处只写下限，换版本会改变依赖解析）。**静态验证已全绿**（yaml.safe_load 解析 + 31 条 schema 自检 + 4 条 bind mount 宿主机路径存在 + 25 条 Dockerfile COPY 源存在 + 3 条 healthcheck 端点与真实路由逐一对齐 `/health`=main.py:91 / admin main.py:22 / `/live/health`=server.py:1412）。**明天继续（剩余）**：①`作品源码/deploy.sh` 一键部署脚本（查 docker→查 .env→up→等健康检查→打印访问地址）；②`docker/README.md`（镜像构成/各 service 作用/常见问题/未验证风险清单）；③给用户的交付报告（含档位 A 最终命令序列）。**档位 B 已知未验证风险（明天写进 README，勿当成能跑）**：TensorRT 8.6.1 的 pip 装法最不确定；LiveTalking 的 requirements.txt 无法预览可能与 torch cu124 冲突；**两份 README 记载的 LiveTalking 基线 commit 打架**（`livetalking_engine/README.md:7`=bf54b577 vs `engine/README.md:33`=8ce6879，已采信后者=生产机取证）；`livetalking_engine/` 镜像**缺 3 个生产在用的改动**（`base_asr.py` 的 timeout 0.002 治待机 0.88x／`tts/ttsbackend.py`／`base_avatar.py` 的 enable_transition），只存在于**不可整包应用**的 LiveTalking.patch 里，Dockerfile.gpu 目前用 sed 补 base_asr 并在失败时只告警。档位 B 失败一律回退已验证的 `ops/build_trt_ada.sh && ops/dp_up.sh`。**未动**：`部署手册.docx`（用户在编辑）、`README.md`、`ops/` 下任何脚本。

- [x] **手机游客端：终止播报按钮 + 徽章穿透 header 修复 + 11 步录屏链路加固（2026-07-15，Windows 机，未碰 GPU/未重启服务；webapp build→bridge dist，commit ab6a194）**：用户两项需求 + 按 11 步录屏脚本全流程体检。**ultracode 两段 workflow**：①审计 6 组并行只读（步1-3/步4形象音色/步5-7输入/步8-9路线GPS/步10-11设施告别/全局层叠）→ 25 条发现 → **每条派对抗验证 agent 逐条驳**（32 agent/3.55M token）→ **确认 20 条、驳回 5 条**；②修复 6 agent 按文件分工并行（App/useGuide/api/trace/icons 主线程自己改，组件各归一 agent，零冲突）。**需求①终止播报**：原「打断」按钮只在 `busy||captionStreaming` 时渲染 → 字幕按 CPS_SPEAK=5.0 推进且提前 START_DELAY 1.5s 起步、桥接按 SPEAK_CPS=4.5 喂句(server.py:226) → **字幕总比嘴早收尾 gap=(P-1.5)+L×(1/4.5-1/5.0)≈0.5+0.0222L 秒**（120字≈3.2s、200字≈4.9s）；**拍照路径更极端**：photo() 从不置 captionStreaming、busy 在 liveSay 发出同刻被 finally 置 false，而嘴要说 20-30s → **整段零打断入口**。修=接桥接已有真信号 `GET /live/now-playing`（~800ms 轮询、纯内存查表零下游调用零 GPU）→ `g.speaking`；首句送驱动时**乐观点亮**（补 busy→轮询之间 ~800ms 空档，实测 t=1s 会闪一下）；**L1 缓存成片播放期间**（busy/caption/speaking 全 false 但画面里人在说）由 `!!g.clipUrl` 兜住；interrupt 加 2.5s 抑制窗防在途旧轮询把按钮点回来。按钮文案「打断」→「终止播报」。**需求②徽章穿透**：根因=舞台卡(App.tsx:314) `relative` 的 z-index:auto **不产生层叠上下文** → 卡内 5 个 absolute 子元素（video z-10/L1成片 z-30/SwitchOverlay z-40/状态徽章 z-20/未连接遮罩 z-20）全升到根层叠上下文，与 sticky header(z-20) 同级、**DOM 靠后者胜出**；修=卡加 **`isolate`**（卡本就 overflow-hidden、无子元素需溢出 → 只改绘制归属不改布局），一处同时治徽章遮挡/成片盖 header/过渡层盖 header/遮罩抢 header 点击 4 症状（**不能改用抬高 header 到 z-30**：仍输 SwitchOverlay 的 z-40，且对 footer 无效）。**顺带修 18 条**：拍照不清字幕致旧答案错配、拍照无 askSeqRef 守卫致「已打断后又开口」、ASR/ask 失败只写 messages（主屏根本不渲染 messages）→ 屏幕零反馈改上字幕、**「重看开场」永久黑屏**（只翻 flag 不复位直播态 → video 卸载后 status 仍 connected → 「开始」按钮被 `status!=='connected'` 挡住不渲染、playerRef 指向已脱离 DOM 的旧播放器 → 只能刷新页面；新增 `disconnect()`）、**新增「第一个足迹」徽章**（到访 1 个景点；原最低档「探索者」要 3 个，而「初次见面」「摄影达人」在步骤 3/7 已解锁 → 脚本第 9 步点一次「我已到达」什么都不弹）、设置加**「重置足迹与勋章」独立入口**（彩排后 localStorage 累计致庆祝卡不再弹；**刻意不挂到「重看开场」**——验证 agent 指出那会让真实游客中途点它就丢全部足迹并毁掉明信片内容）、设施地图「从我的位置出发」两分支都翻车（失败写地图级 err 把画好的路线整个换成「地图暂时不可用」且 origin 未变→effect 不重跑→错误层常驻必须关抽屉重开；成功不校验是否在景区内→录制机不在灵山画出跨省路线「步行约 300000 米」）→ 拆 geoErr + 3km 范围闸门、跟我游路线进度每次打开无条件清空且不读 trace.visited→与足迹抽屉自相矛盾、音色「选中即试听」被抽屉压音压成全静音（试听有声/选中无声）、AI 生成形象必然不在唇形白名单却直接 pick()→改诚实文案（**不绕白名单**，未过 lipmatrix 的底板上身会嘴部坍缩）、形象热切失败回滚是死代码（liveSetAvatar 恒 resolve 从不 reject）、「恢复景区默认」只清偏好不切直播、**「下次连接生效」是空承诺**（实证 connect 全链路从不应用 avatarPref）、明信片邮戳弧字半径/字号失配致绕圈自我重叠压中心字 + 仍印已弃品牌 ZHIYOU→改 measureText 按实宽算弧度+自动缩字号+TUDAODAO、geo.ts 定位失败文案硬编「下方模拟位置」（多抽屉复用但该控件不在每页）→改 UI 中立由各页自己追加。**对抗验证驳回 5 条未改（重要，防后人重蹈）**：farewell 无需硬清（`/live/say` 的 `SayIn.interrupt` 默认 True → `/human {interrupt:true}` 与 `/interrupt_talk` **调用同一个 flush_talk()**，且 flush+入队在同一请求内原子完成）；trace 跨会话累计是成就语义非 bug 且建议修法会毁数据；设施质心兜底已有「设施为参考位置」标注（FacilityMapSheet:71/174）；形象连点竞态被 beginSwitch/endSwitch 首行的 clearTimeout 覆盖（且时序推导反了：gap 越小越安全）；one-arrival-no-badge 被判「设计如此」（GpsSheet 一屏渲 4 张 POI 卡各带按钮、点 3 下即 explorer）——但**脚本白纸黑字要求「点一次得一枚」，用户拍板加 footprint 档**。**实测（Playwright iPhone 14 口径 / 公网网关 / 服务器完整 chromium）**：①**层叠 A/B 铁证**——构造重叠(徽章 t24-b50 落在 header t0-b61 内)后命中测试：修后最上层=`DIV.text-[11px] text-muted-foreground`(header 子元素)=PASS，**对照组把 isolate 摘成 auto 立刻复现原 bug**(最上层=`SPAN.inline-flex…rounded-full`=徽章本体) → 证明测试有效且修复真实；②**终止播报**——50 个 speaking 采样**零缺席**、speaking 起于 1.5s→按钮在→点击→后端 speaking=false/按钮消失/拍照可用/输入可用/音量恢复 1/再问「梵宫在哪里」数字人重新开口「灵山梵宫在灵山胜境西侧，香水海之畔。」；③**第 9 步勋章**——手动选点(灵山胜境门楼)→「我已到达」→庆祝卡 0.00s 弹出「解锁徽章/第一个足迹/到访 1 个景点」+足迹面板入账；④**第 10 步设施导航三口径全绿**（景区内/北京(1000km 外，走范围闸门无荒谬距离)/定位被拒，地图均未被错误层换掉）；⑤文字问答真答「灵山大佛通高88米（佛体79米+莲花…」；⑥全程**零 pageerror**。部署：本机 build→tar over ssh→`/root/autodl-tmp/Digital_Person/webapp/dist`（bridge 直接从磁盘服 `/`，index.html no-cache 免重启），入口 `index-Do93QBq9.js`，旧版备份 `dist.bak_stopbtn`。**坑**：Windows 无 rsync→tar|ssh；Bash 工具命令行含中文仍必挂(exit 127)→提交信息走 `git commit -F`、检索走 Grep 工具。**待办**：⑦步骤 6 语音输入与步骤 7 拍照输入需真机手测（headless 假麦/假摄像头无法真跑 ASR/VL，代码路径已审计+修复但未端到端实录）。

- [x] **大屏两连修：路线序号↔站名对齐 + 形象切换旧形象残留（2026-07-14，Windows 机，未碰 GPU；纯 kiosk 前端 build→ECS）**：用户复报（附截图）①「切换路线」进度条**序号圆点与站名仍未对齐**；②大屏**数字人切换形象后过渡界面播完仍残留 ~2s 旧形象再闪现新形象**，要求过渡后直接新形象、零残留。**①对齐根因**（`TourRoutePanel.vue` `.bak_align`）：`.pr-dot-wrap` 是 flex 行、圆点在左 + `.pr-line` flex:1 撑满右侧 → 圆点贴每格**左缘**，而 `.pr-name` 在整格**居中** → 名字整体偏右于圆点。修=`.pr-dot-wrap` 加 `justify-content:center` 让圆点居中；`.pr-line` 改**绝对定位**（`left:50% right:-50% top:50% translateY`，z-index:0 压圆点下）从本格圆点中心画到下一格圆点中心。Playwright 实测（1080×1920，4 站）dot 中心 x − name 中心 x **dx=0/0/0/0，max|dx|=0** 像素级对齐、零 pageerror。**②残留根因**（`DigitalHumanStage.vue`+`session.js` `.bak_switchflush`）：播放器有 ~2s stash 缓冲+liveSync 延迟 → 热切 POST ok 后过渡层在 1.2s 就淡出，而**播放器仍在放缓冲里的旧形象帧** ~2s 才排空 → 旧形象残留后新形象闪现。修=过渡层不再定时淡出：`endAvatarSwitch(ok)` 置 `committed:true`（兜底 6s）→ 主舞台 watch 到后**等 2s（引擎换脸+新首帧推流窗口）→ 重建 mpegts 播放器**（新实例从直播边缘起播、无旧形象缓冲帧）→ 待新流首帧解码(MEDIA_INFO)+350ms 才 `finishAvatarSwitch()` 交叉淡出；过渡层 z-index:6 全程盖住重建（不闪黑）；音频图键于 `<video>` 元素不受重建影响。部署：`/root/visitor_web` build-only --base=/kiosk/（入口 `index-D-VjdWPv.js`）→ rsync ECS `/var/www/kiosk`。①已线上实测；②逻辑修复+构建零错误，真机热切观感建议录制前抽验（需 portrait 流在跑）。

- [x] **管理端消费分析 + 数据大屏加消费数据（2026-07-14，Windows 机，未碰 GPU；rag 重启+admin 前端 build，数据源=赛题行为数据 xlsx 灵山真实 236 条）**：官方讲解要求做「管理端消费分析→营销决策」，且数据集必须基于《景点景区旅游数据行为分析数据》（筛灵山）。**后端（git，`backend/api/analytics_bi.py`）**：①`real_only` 口径——新 `_xlsx_only()` 只读赛题 xlsx（不掺合成补量），overview/spending/demographics 加 `real_only` 参数（默认 False 保大屏既有口径；消费分析端点默认 True），overview 附 `source` 溯源字段。②5 个新端点（默认 real_only 真实口径，规则化确定性、可溯源到真实数字）：`/bi/spend-tiers`（客单价低<600/中600-1200/高1200+ 分层：人数占比·营收占比·各层画像）、`/bi/spend-drivers`（停留时长 4 桶 + 同行规模 4 桶 × 客单价，撑"延长停留/家庭套票"决策）、`/bi/satisfaction-value`（满意度×消费四象限以中位数为轴 + 散点 150 点，定位高消费低满意风险区）、`/bi/spend-trend`（按月/周 客流·客单价·营收趋势）、`/bi/marketing-advice`（洞察→建议→预期：主力消费类目/停留杠杆/高价值客群/满意度风险，全部数字来自真实样本）。**关键性能修复=pickle 缓存**：`pd.read_excel` 16.7MB/140k 行 openpyxl 要 ~24s，且 `lru_cache` 对并发首调不加锁 → 一打十几个并发大屏请求各跑一次 24s GIL 绑定读、挤爆线程池（重启后端点恒 hang >120s，误判服务挂）；`_read_xlsx_raw()` 改优先读派生 `behavior_data.pkl`（<0.02s、首请求即热，旧于 xlsx 时自动重建），xlsx 仍是真源、pkl gitignore 不入库。修后端点 0.59s 冷启。commit aee9e41（含 5874f26 端点），已 push+rag 重启，实测 6 端点全返真数（灵山 236 条：客单价 ¥927.2/总营收 ¥21.9万/高消费客群 27% 人数→**54% 营收**/满意度中位数 3.0）。**管理端前端（`AdminView.vue` 非 git，`.bak_consumption` 备份，server build 上线）**：①新增侧栏「经营分析」组 →「消费分析」独立页（套报告页 `.rpt-*` 范式 + 独立 `_consEc` ECharts 管理器 + flush:'post' watcher + 明暗主题同步）：**数据来源徽章**「《景点景区旅游数据行为分析数据》· 灵山胜境 236 条真实样本」+ KPI 条（客单价/样本总营收/高价值客群营收占比/真实样本量）+ 消费与客流趋势(折线+柱)+消费结构环+客单价分层营收贡献对比条+消费驱动因子(停留/同行×客单价)+满意度×消费四象限散点+**营销决策建议卡**（洞察→建议→预期，「采纳」复制到运营计划）。②**数据大屏底部决策带**从 3 格→4 格加「客单价分层·营收贡献」面板（`ecTiers`：人数占比 vs 营收占比水平对比条，副标题「高消费 27% 人数 → 54% 营收」= 演示杀手洞察）。Playwright 实测（bridge 直连+API 登录 cc_avb）：登录 200、消费分析页 5 图全渲染+KPI 真数(¥927/¥21.9万/54%/236)+徽章文案精确+3 建议卡、大屏 4 格全渲染+分层面板+meta 正确、零 JS pageerror（仅 1 条历史无害资源 404）；公网网关服新构建入口 chunk 确认。**③接上运营 AI 代理（`admin_chat_router.py`:6008，`.bak_consumption`，restart admin_api）**：`_READ_TOOLS` 加 5 个消费工具（get_spend_tiers/spend_drivers/satisfaction_value/spend_trend/marketing_advice，走 real_only 真实口径）+ 描述/状态提示 + SYSTEM_AGENT 补消费分析→营销决策指引；前端 AI 助手加快捷问「高价值客群是谁？给几条营销建议」chip。SSE 实测：问消费问题→代理真调 spend-tiers/spend-drivers/marketing-advice 三工具→答复引真数「客单价≥¥1200 的 27% 游客(均 38 岁)贡献 54% 营收、满意度仅 2.7 分=高消费低满意风险群」+3 条可执行营销建议；UI chip 点击→代理流式响应、零 pageerror。详见 [[admin-panel-upgrade]]。

- [ ] **录屏前两游客端全面体检+批量修复（2026-07-14，Windows 机，动了 bridge/未碰 GPU 流）**：用户备录演示视频，要求测两游客端（大屏 kiosk Vue `/root/visitor_web`→ECS `/var/www/kiosk`；手机端 React `webapp`→bridge 服 `/`）发现并修所有影响"丝滑/功能/美观/不出错"的问题，并给了 11 步录屏脚本。**先备份**：两非-git 前端 tar 到网盘 `/root/autodl-fs/prerecord_backup_20260714_191041/`（admin 24M+kiosk 12M）；服务器 kiosk `src.bak_prerecord`、mobile `dist.bak_prerecord`、ECS `kiosk.bak_prerecord`、云栖预览 `.bak_thumbunify`。**审计**=ultracode 7 agent 只读拆解两前端+后端契约+11 步脚本 → 54 findings→22 排序修复清单（synth agent）。**已修并线上验证（Playwright DOM 文本匹配，tofu-proof；零 pageerror 两端）**：①后端新增 `POST /live/interrupt {sessionid,screen}`（bridge git commit ac28454：清 sid 播报队列+bump 会话代号让在跑 ask/say 循环自停+`/interrupt_talk` 硬清引擎+释放渲染槽，纯 CPU 不碰 GPU；网关实测 `{ok:true}`）。②**大屏 kiosk**（13 项，agent 改本地 mirror→tar 推服务器→`npm run build-only -- --base=/kiosk/`→rsync 到 ECS，入口 `index-soN_a6ii.js`）：用户点功能面板改 `liveSay(interrupt:true)` 立即打断（治"点了没反应"）；设施卡点击画路线+开口（navigateTo）；地图 `stageSize` contain→cover **填满容器 fillW/H=1.00**；推荐路线序号↔站名居中对齐；POI 点击"从这里出发"手动选当前位置（补 GPS 删除后的空缺）；删 SmartDashboard `未定位` GPS 徽章；数字人左栏白底→**深色渐变**杀四周死白 letterbox（+ foot 收窄 + 保留形象条不自动收起 + 边缘辉光）；**形象唇形白名单** `config/avatarWhitelist.js`（dh_lingshan/dh_gugong/F1/F2/M1/云栖 custom_201715）→未体检形象置灰"体检中"不可选（实测 9 个锁定）；勋章多解锁改队列逐个弹；快追问打断旧轮不再静默丢；字幕 SEG_MAX 42→30+line-clamp 4+迎宾分段；**结束导览**按钮（HeaderBar，个性化告别语 `{guide}/{scenic}` 去人名化→4.2s 后 resetSession 回欢迎页）。③**手机端 mobile**（agent 本地 build clean→rsync dist，入口 `index-BcuP9rtY.js`）：**打断按钮**（busy 时显示，`videoRef.volume` rAF 400ms 淡出=语音渐弱→POST /live/interrupt→恢复音量不影响下一条）+ 麦/相机解锁允许答题中插话（bargeIn）；**勋章庆祝**（`BadgeCelebration` 居中卡+confetti，`commitTrace` diff 前后徽章，`我已到达`按钮 GpsSheet/RouteMapSheet 补 recordVisit/recordRouteDone）；设施速查每条可点=`onAsk("X怎么走")`+"点击导航"提示（agent 判 amap 缺真坐标→走口播导航不假造坐标；**可选升级为画线导航待用户定**）；抽屉补关闭 X；音色切换即时试听确认；**结束这次导览**（SettingsSheet→告别语+弹电子明信片）；形象唇形白名单（AvatarSheet `唇形待体检`）。④**形象画幅统一**：实测根因=11 内置预览 480×270(16:9)+female_sweet 360×640(9:16)+custom 另一套 → 白名单收敛到一致集 + **云栖预览 ffmpeg 从 9:16 底板裁 16:9 头肩照**（`custom_avatars/custom_20260713_201715.jpg`，RAG 直服无需重启）与其余 4 个 16:9 一致。⑤审计发现手机 facility/subtitle 那个 agent 返回占位垃圾→已由 mobile 实施 agent 亲审：字幕无超前/无遮挡/长文分段均已正确（START_DELAY 1500ms 防超前、char-reveal 钳制已交付文本），未动以免回归。**部署拓扑（关键，已核实）**：`/`(手机)+`/admin`→ECS nginx→隧道 16006→AutoDL bridge 服 dist；`/kiosk/`→**ECS 静态 `/var/www/kiosk`**（非隧道，AutoDL 能直 ssh ECS→rsync）；`/live//rag//stream*`→隧道/SRS。**排障坑**：`npm run build -- --base=` 经 run-p 不透传给 vite（首建 base 错成 `/`→kiosk 白屏），改 `npm run build-only -- --base=/kiosk/` 修正；Bash 工具命令行含中文变量必炸(exit127)→中文入脚本文件跑；bridge 服务器实听 6006 非 9000（隧道 16006→6006），本地 curl :9000 空、走网关才对。⑥**GPU 体检已完成（2026-07-14，用户授权在场，GPU 无 SAM3、未重启流、仅热切）**：lipmatrix 逐个体检未验证形象，双流（9:16 竖版 kiosk + 16:9 main 手机）各录 test 全脸网格逐帧判开口——**F4_qipao/F5_ethnic/F6_mature/M3_youth/M4_business 两流均开口清晰无坍缩→扩进白名单**（白名单 6→11）；F3_youth/M2_scholar/custom_20260713_183121(知欢) 几乎不张口→仍锁；female_sweet 唇 OK 但预览 9:16 破画幅→不放。默认已复位（portrait=云栖/main=dh_lingshan）。两端白名单已改+重构建重部署（kiosk `index-Dvwyqsm_.js`→ECS、mobile `index-CADuQz67.js`→bridge），实测 kiosk 锁定形象 9→4、零 pageerror。⑧**手机设施画线导航已做**（用户选：升级为地图画线，子 agent 建 `webapp/src/lib/facilityGeo.ts`+`components/FacilityMapSheet.tsx`：真 POI 坐标+5 个假设地标锚点标"设施为参考位置"、路径贴景区步道、GPS 重路由、失败降级口播；仅灵山有坐标故只灵山出图、他景区回退口播）。**待办**：⑦真机首次录制前建议手动走一遍"说话中点功能→打断→再问"确认丝滑（代码已就位+端到端契约已验，未逐帧实录）。审计计划见 workflow `prerecord-audit`。

- [x] **数据大屏细节二修：客群画像遮挡 + 实时客流压力条名不符（2026-07-14，Windows 机，未碰 GPU；纯 admin 前端 build，`.bak_dshfix2`）**：用户复报（附实机截图）两处——①**客群画像被消费结构卡片遮挡**：根因=全屏大屏 `.tab-dashboard-screen`（flex 列，dsh-hd 56 + 弹幕带 + dsh-body flex:1 + dsh-strip 定高）在矮视口/高缩放下 dsh-body 被压，左栏 3 面板（核心指标+功能使用率+**客群画像**）与右栏末面板（**时段热度**）溢出到底部数据带下方被压住。修=`dsh-pf min-height 152→116`、`dsh-strip height clamp(248,33vh,323)→clamp(196,26vh,264)`、`dsh-ec-md/sm/lg min-height 110→92`+`dsh-ec-main 120→104`（min-height 只在压缩时生效，正常 height:100% 撑满，故调低不伤常规分辨率、只给矮视口让出收缩空间）。②**实时客流压力「景区数字≠柱状数量」**：根因=y 轴 category `axisLabel` 默认 `interval:'auto'`，面板一窄 ECharts **自动隐藏**部分类目名（显 3 名却渲 6 条）；且右端浮动等级文字（繁忙/较多）悬在图中乱。修 ecSpots=`axisLabel interval:0`（**强制每条都显名**，杜绝名少条多）+ `.filter(s=>s&&s.name)`（空名点位不进图）+ 右端标签由等级文字改**拥挤指数数字**（与柱一一对应，等级仍由颜色区分、tooltip 附文字）+ `barCategoryGap 70%→34%`/`barMaxWidth 12→16`/`grid top-bottom 10→2`（柱加粗填满、去底部大片留白）+ `axisLabel width 60→78`（名不截断）。Playwright 实测（完整 chromium+API 登录）1600×900 与 1920×1080 双口径：客群画像/时段热度面板底距底部数据带顶 **overlap_px=-12（负=不再重叠，留 12px 网格间隙）**、11 图全渲染、实时客流 6 条=6 名各带数字（134/63/60/36/36/24）柱体充满、1080 下客群画像环+底部图例齐全、零 pageerror（仅 1 条无害资源 404，历史既有）。已 build 上线（公网 /admin 由 bridge 服 dist）。⚠️注：1600×900 极矮口径下客群画像环偏小、底部图例被裁（overlap 已消，属高度取舍；1080 完好）。**排障教训：本机 PowerShell 工具会整体卡死（连纯本地命令都超时）→ 误判为服务器/网络故障；实为 PS host 卡住，切 Bash 工具 ssh 立即恢复；服务器 515G 内存始终健康、未过载。**

- [x] **数据大屏布局修复 + 文字报告 markdown 渲染优化（2026-07-14，Windows 机，未碰 GPU；纯 admin 前端 build）**：用户报大屏多处挤压。**布局修复**（AdminView.vue `.bak_dshfix`）：①`dsh-body` 三栏 `300/1fr/330` → `344/1fr/376`（左右加宽、中栏"近7日趋势+情感分布"卡牌相应收窄，正合用户"中心卡牌可减小"）②`时段热度` f-xs 0.72→0.95 + ecHours grid `bottom22→28,containLabel` + axisLabel `margin10,hideOverlap`（横轴 6/10/14/18/22时刻度恢复可见）③`实时客流压力` ecSpots `barCategoryGap 55%→70%`+grid top/bottom 4→10+yAxis margin12（条与文字上下不再挤）④`客群画像` f-xl 1.275→1.35 且**弃用外圈引导线标签**（窄栏里引导线把环挤变形/文字被裁）→改 label:false + 底部滚动图例（同情感分布 donut 口径），高亮态才显名+占比。**文字报告 markdown 优化**（`mdToHtml` 共用于报告 .rpt-doc + AI 气泡 .ai-md）：分级标题(#→h3/##→h4/###→h5)、**有序列表用 `<ol>`**（原全渲成无序 bullet）、斜体 `*x*`→em、引用 `>`→blockquote、行内 code；**去 LLM 把整篇用 ```markdown 围栏包裹的壳**（strip 首尾 fence + 忽略残留 ``` 行，根治报告顶/底出现"```markdown"字面）；.rpt-doc/.ai-md 补 h3/h5/ol/em/blockquote/code/li::marker 样式。Playwright 1920×1080 实测：大屏 12 面板 11 图全渲染、时段热度横轴可见、客流条距合理、客群画像不变形、中心收窄、零 pageerror；报告实测 h3×1/ol×4/ul×3/li×15/bold×7、无围栏残留、零 pageerror。已 build 上线（公网 /admin 由 bridge 服 dist）。

- [x] **管理端注册界面丰富：管理人员信息步骤（2026-07-14，Windows 机，未碰 GPU；admin_api 重启+前端build）**：用户要求注册采集更丰富信息（含管理人员所在景区等）。原注册=2步向导（账号→选景区）→ 扩为**3步向导**，中插「管理人员信息」步：真实姓名(必填)/联系电话(必填,11位手机校验)/电子邮箱(选填,格式校验)/所属部门(必填,下拉:运营管理部/游客服务部/市场营销部/信息技术部/安全保卫部/综合办公室/其他)/岗位职务(选填)；第3步景区标题改「管理人员所在景区」。进度条 33/66/100，`nextStep2` 前端校验 + 后端 `auth_router.py` 服务端二次校验（防绕过）。**后端**（`/root/digital-human/backend/routers/auth_router.py` :6008 非git，`.bak_reg`）：`AuthBody` 加 real_name/phone/email/department/position；register 存全字段+created_at；新 `_public()` 让 register/login/me 统一返回画像字段（供管理端展示）；旧格式用户兼容。**前端**（AdminLoginView.vue + stores/auth.js，`.bak_reg`）：register 传 profile 对象；新增 5 图标(PhIdentificationCard/PhPhone/PhEnvelopeSimple/PhBriefcase/PhUserGear)+下拉自绘箭头样式。实测：后端 curl 全字段 200 存盘正确、缺字段/坏手机号→400；Playwright 3步向导全绿（字段齐/空校验报错/选部门/选景区/**完成注册自动登录跳 /admin/**，零 pageerror），UI 截图美观。测试账号已清理。

- [x] **应急广播页：现场预览真直播化 + 功能充实（2026-07-14，Windows 机，未碰 GPU；纯 admin 前端 build，零后端改）**：用户复报「应急广播现场预览没显示数字人在播报」+ 要求「设计其他功能、页面很充实」。**修根因**：原「现场预览」是静态 PhUserCircle 占位图 → 改为 mpegts.js 拉**真直播 FLV**（`BC_FLV={portrait:PORTRAIT_FLV,main:'/stream.flv'}`，立屏/手机端可切），muted **只读监看不驱动数字人、不影响游客端流畅性**；用**独立** player(`bcFlvPlayer`)+video ref(`bcPreviewVideoEl`) 防与形象页 flvPlayer 打架；叠 LIVE 徽章 + 播报中徽章 + 字幕层（所见即 kiosk 所得，实测预览渲染出灵山数字人+红色警示字幕）。**充实化**：①顶部状态条 4 卡（立屏/手机端在线=`probeStream` 拉 FLV 响应头判活即 abort 零副作用每6s、当前播报=now-playing 每2s、会话广播数）②广播级别紧急/重要/常规（联动 style+emotion+dur）③模板按「安全应急(红)/运营通知(蓝)」分组 8 条(+医疗求助/失物招领/温馨提示)④预计播报时长(≈字数/4.2)⑤**定时循环播报**(前端计时,仅本页开启期间生效,离页自停)⑥历史加级别徽章+重发按钮。生命周期：activeTab watch 进/离 broadcast 起停预览+轮询+循环；onMounted/onUnmounted 对称清理。备份 `.bak_bcpreview`，build 上线（公网 /admin 由 bridge 服 dist，实测经 ECS 网关已生效）。bc_smoke 全绿(LIVE 徽章=真连流铁证/8 模板/3 级别/切屏/循环)、admin_smoke 零回归(FAQ pill 12/上传弹窗/体检/代理全在)。详见 [[admin-panel-upgrade]]。

- [x] **管理端十项功能升级：真实现非空壳（2026-07-14，Windows 机，未碰 GPU；rag/bridge/admin_api 重启+前端build+kiosk部署）**：用户列 10 项管理端改造，制定计划(`~/.claude/plans/structured-gliding-bumblebee.md`)后执行，全部实现并 Playwright 实测通过。**关键发现=FAQ/文本列表恒空的真 bug**：admin 代理返回 `{code:0,data:{items:[]}}` 而前端 `loadFaq/loadText` 把 `res.data.data` 当数组 `.map`（静默失败）→ 改读 `res.data.data.items`（F2「修复」根因，实测修后 12 条 FAQ 正常渲染）。**F1** 上传改「上传文档」按钮→弹窗→选文件→开始上传（el-upload auto-upload=false 批量）。**F2** 新 `backend/rag/faq_priority.py`（git）：pipeline.answer/answer_stream 检索前插高阈值近似命中（归一化相等/强包含/Jaccard≥0.85）→ 命中即以人工答案作答、不进检索不改 qa 缓存键；kb_manage 写操作 invalidate；覆盖 /chat 与 /live/ask；**test_faq_priority 10/10 + test_accuracy lingshan 20/20 零回归**；FAQ 条目加「最高优先级」pill。**F3** 文本段落补搜索框+彩标（编辑/删除本已有）。**F4** `kb_selftest` 每题增 duration_ms/source/score/kw_type + 响应 by_type/avg_duration_ms/failed，前端出准确率环形仪表+题型通过率条+单题耗时/来源 chip（实测响应含全部新字段）。**F5** 应急广播从大屏头部按钮移到侧栏「日常运营」独立页（模板快选/目标屏/语气/**上屏字幕开关+样式+时长**/实时预览/历史）；bridge 新增 `POST/GET /live/subtitle`+`POST /live/broadcast`（API_DOC 6.5）；kiosk 新 `useEmergencySubtitle`+`EmergencyBanner.vue`（顶部横幅 alert红/info蓝，轮询 /live/subtitle，实测 banner_visible+文案正确）。**F6** `admin_chat_router.py`(:6008) 重写为 DashScope function-calling 运营代理：只读工具实时取 analytics（替代死快照）+ SSE `data:{status}` 工具进度 + **建议动作走「抽取pass」**（qwen 只叙述不调 propose 工具→改用 qwen-flash 从答复抽取 broadcast/faqs）→ SSE `data:{action}` → 前端动作卡（去播报预填/加入知识库），全挂降级静态快照（实测：真调 get_crowd/knowledge_gaps + 抽出广播草稿与 3 条 FAQ 建议）。**F7** 分类彩标 `CAT_COLORS`+`catColor()`：FAQ/文本筛选条/徽章/下拉选项前置彩点（实测 6 筛选点+12 tinted 徽章）。**F8** 左下角重做（景区卡+服务中脉冲点/头像账号/主题切换）。**F9** AI 输入框+通用输入框圆角+聚焦环。**F10** 场景背景选择缩略图从「人物合成图」改为纯景背景（由 raw PNG 缩略）；bingmayong 原图含兵马俑人形剪影（唇形毒化）→万相重生成空展厅（其余 7 张 raw 本就纯净）；git 提交 8 缩略图+新 bingmayong。**部署**：主后端 commit 95f7309(faq_priority+selftest+bridge subtitle)+67e6c36(背景)已 push；admin_api/admin 前端/kiosk 均非 git=scp+build+`.bak_adminup` 备份，kiosk relay 到 ECS /var/www/kiosk。Playwright 实测(完整chromium+API登录 cc_avb)：登录200、侧栏应急广播、上传弹窗、FAQ彩标+优先级pill、文本搜索、体检按钮、运营代理欢迎、左下角美化、kiosk字幕横幅全绿，零 pageerror。详见记忆 [[admin-panel-upgrade]]。

- [x] **团队素材库上服务器（2026-07-13，Windows 机，纯文件同步零服务变更）**：本机沉淀的项目"经历/经过/成果"原封不动导出至 AutoDL，供三人写文档与知识交流——`/root/autodl-tmp/team_materials/`（48 文件，README.md 为总导读）：01 项目总档案+全量进度日志（本文件+三子域 CLAUDE.md）、02 经验记忆库 11 篇（Claude Code 记忆原文：嘴唇坍缩根因/TRT 流水线/大屏卡顿取证/画像红线等）、03 实施计划书 2 份（画像 P123+形象升级 R1-R9 的 Fable 原始 plan）、04 API_DOC、05 docs 全量 25 篇 md、06 交接运维（CODEX_HANDOFF/迁移/RESTORE/iPhone 真机 bug）；tar 归档网盘 `/root/autodl-fs/team_materials_20260713.tar.gz`（301KB，换机不丢）。README 内置成果速查表（97.1%/4.7s/25.5fps 等口径+出处）与只读约定（修改回源头再同步防口径分叉）。注意坑：网盘挂载实际在 `/root/autodl-fs/` 无 data 子层；Bash 工具中文命令行仍挂（目录名用 ASCII、中文进文件内容/glob 通配绕过）。

- [ ] **建立用户画像深入实现 P1/P2/P3（2026-07-13，Windows 机，未碰 GPU；Fable 计划→Opus 执行）**：把"建立用户画像"从功能图上的空壳做实——**游中画像**（匿名 session 级、48h 惰性自清、人走画像消）。**P1 已完成并线上实测**：①`visitor_profile` 表（database.py 幂等建）+ 新 `backend/agent/profiler.py`（规则扫兴趣关键词 `history/nature/photo/food/culture` + 匹配本景区 TOURS 真实站名 + intent 计数 + 静态兴趣并入；`note_turn`/`profile_brief`/`profile_digest`；`_SKIP_SESSIONS={anonymous,0,空,s_anon}` 不建串人画像；全函数 try/except 静默）。②**注入红线**：`_directive_with_context` 仅在 `_CROWD_INTENTS`(navigation/recommend) 分支注入画像，**qa 事实问答链路一行不碰**（答案缓存键 `_cache_query` 零改）；`answer`/`answer_stream` 四处 `note_turn`（含 cache-hit）+ 透传 session_id/interests。③`chat.py` ChatRequest + `interests`、bridge AskIn + `interests` 转发 RAG；`recommend` 消费 `profile_ctx`（未访 POI 提示不重推）+ 缓存键加 `profile_digest`。④**webapp**：新增 `bizSessionId()`（复用 track.ts 的 per-tab `lingjing.sid`，与埋点 events 同源），liveAsk/liveAskStream/recommend 都带真实业务 `session_id`（此前只发 LiveTalking 的 `sessionid='0'`→画像会被 skip 且多人串；根治）。**实测全绿**：`tests/test_visitor_profile.py` 19/19（含**qa 不含画像红线断言**）；`test_accuracy.py lingshan` **20/20=100% 零回归**；线上 answer() 端到端演示——上午问素斋(qa,画像不进 prompt)→下午"推荐半天路线"(navigation)回复自然收尾**"您不是说想尝尝这里的素斋吗？…去灵山精舍吃一顿素斋"**（杀手镜头达成）；webapp 新包 index-wZW-Wl5C.js 部署+Playwright 冒烟 4/4（/recommend 真带 session_id、零 pageerror）。已部署重启 rag+bridge。commit 34fd5af/7fd33f5，API_DOC §1.7 已录。**P2 已完成并线上实测（真 qwen-flash）**：`maybe_summarize`（每 6 轮 daemon 线程 qwen-flash 出画像 JSON `{summary,style,needs,wishes,avoid}`，`_INFLIGHT` 防重入，`_llm` 可注入，严格 JSON 解析失败静默，note_turn 末尾自判触发，**不占 <5s 问答预算**）→ profile_brief 优先 summary + 追加"未了心愿"；recommend 强化未了心愿优先兑现；扫码接力 handoff：create 存 source_session_id+profile_summary、claim 带 session_id → `_copy_profile` 把源画像并入领取方（换设备"还认识你"）。**实测**：test 扩到 31/31（+摘要 gating/垃圾静默/接力/48h 清理，假线程同步化）；线上 6 轮真对话触发真 daemon 摘要 → SUMMARY="爱拍照、重文化、想看表演的深度型游客" wishes=["想看九龙灌浴的表演"] → 求推荐回复开篇"先去九龙灌浴，正适合您想看表演的心愿"、收尾"还满足了您想看九龙灌浴的愿望"（**未了心愿兑现杀手镜头**，还顺带织入素斋兴趣）。rag 已重启、webapp 新包 index-Dj1K4f-O.js 部署。commit fc27b96。**P3 已完成并线上实测**：`infer_trajectory`（读现有 geo_arrival/station_visit 事件推停留时长/游览风格/体力提示，**零新采集**）+ `update_trajectory`（note_turn 每 5 轮刷 traits.trajectory+visited 列，体力告急时 brief 追加"就近收尾多提休息点"，对接既有体力轴）；`analytics /profile` +三新字段 `dynamic_interests`（动态兴趣，**治静态 interests 稀疏**）/`styles`（游览风格分布）/`unmet_needs`（心愿+需求 top10=运营缺口，与 knowledge-gaps 互补），旧字段全保留；`seed_demo_data` 播种 visitor_profile 行 + geo_arrival 事件（demo- 前缀 --wipe 联动）。**实测**：test 扩到 42/42（+轨迹深度/打卡/体力提示 + /profile 三新字段断言）；`test_accuracy lingshan` 20/20=100% 再次零回归；8 景区已 seed，线上 `curl /profile?scenic_id=lingshan` 返回 profiled_visitors=83、dynamic_interests={特色美食35,自然风光32,…}、styles={亲子型16,深度型14,…}、unmet_needs={演出场次提醒16,想登高看日落14,…}、旧字段完好。rag 已重启。commit b7489a9，API_DOC §3.10 已录。**P1/P2/P3 全部完成交付**；**顺清两条老待办**：profile 稀疏（dynamic_interests 根治）、knowledge-gaps 偏薄（unmet_needs 补服务盲区维度）。计划见 `~/.claude/plans/visitor-profile-p123.md`。
- [ ] 【需管理端】**客群洞察三新字段可上卡片**（窗口①画像 P3 2026-07-13）：`GET /analytics/profile` 已增量返回 `dynamic_interests`（动态兴趣分布，治静态稀疏）/`styles`（游览风格）/`unmet_needs`（未满足心愿=运营缺口 top10）+ `profiled_visitors`；管理端「客群画像」板块可加：动态兴趣词云/环、游览风格饼、未满足需求排行榜（对标 knowledge-gaps 做"服务盲区"卡）。接口已上线（8 景区已 seed 演示数据），UI 归对应窗口。

- [ ] **数字人形象管理全面升级：生产者/消费者分离 + 管理端工作台重构 + 游客端过渡/过滤 + 甜美候选批（2026-07-13，Windows 机，未重启 GPU 流）**：用户 9 项需求（R1 游客端按景区过滤只见本景形象 / R2 管理端参数细化+实时预览+每参反馈 / R3 管理端 UI 统一感受度报告 .rpt 风格 / R4 游客切换过渡动画**禁用旧形象当过渡帧** / R5 多用户零串扰 / R6 万相甜美女性默认形象候选 / R7 文艺艺名可改 / R8 头身中轴**只校验不平移**+嘴幅初调"刚刚不露齿" / R9 自测通过再交付）。**Fable5 计划→本次实施**。**已完成并实测（A/B/C/D）**：①**Phase A 后端底座**（本地 git，已部署重启 rag）：SQLite 双表 `dh_avatar_meta`(艺名+欢迎语全局)+`dh_avatar_publish`(按景区发布/排序/艺名覆盖)；`GET /presets?scenic_id=&audience=visitor|admin`（无参=旧全量向后兼容，visitor 过滤他景区专属，admin 附 published）；`_DEFAULT_STAGE_NAMES` 20 个文艺艺名零播种（dh_lingshan=云岫…F1=知言 F2=绾云）；`PUT /avatar-meta`(艺名 1-8 字校验/欢迎语≤60)、`PUT /avatar-publish`(UPSERT)；tests/test_dh_avatar_meta.py 32/32。②**Phase B 管理端重构**（服务器 /root/digital-human，build 上线，.bak_avatarphaseB）：KPI 概览条+形象库卡(艺名 chip/已发布 pills/游客可见 el-switch)+参数工作台(艺名/欢迎语/音色试听/背景/情绪/嘴幅滑杆)+离线预览(`GET /live/avatar-plate` 底板 JPEG 同 `_live_avatar_candidates` 解析)+「应用到大屏」确认闸门；**串扰根治=点选只改 draft+换离线预览图，绝不热切直播流**（删除旧 pickAvatar/pickBackground 的 liveSetAvatar）；音色试听走 /voice_samples/manifest.json（rsync 自 webapp）。Playwright 登录实测 12/12：**调参预览期间零 /live/avatar 热切**（串扰修复铁证）、预览图随选形象变化、艺名可编辑、零 pageerror。③**Phase C 游客端**（kiosk+webapp 双端，上一段已完成 36/36）：过滤消费+`.dh-switching`/SwitchOverlay 过渡层（新形象立绘+模糊底+扫光+「正在换上『艺名』…」，**不碰 freezeFrame 旧帧**，失败回滚+toast）+艺名显示+欢迎语 queue 播报。④**Phase D 甜美候选**（本地 git，已部署）：`POST /generate-candidates`(后台批量甜美女性,prompt 不露齿+negative 排除背景人形剪影,落 staging 暂存)、`GET /candidates`、`candidate-preview`、`POST /candidates/{cid}/adopt`(拒未居中→复制双比例进 ditto+custom+艺名)；`_face_center_offset` **只校验不平移**（平移=唇形坍缩根因）；实测 6/6 生成成功、3 居中/3 拒(偏差 4.3-6.5%)、adopt 拒未居中 400 + 采用 c3(偏 1.2%,塔景无人形)→custom_20260713_183121(艺名 知欢)落 ditto + avatar-plate 解析 200；**6 候选已下载 scratchpad/cand/**（c0 粉旗袍居中但**背景有灵山大佛剪影=唇险**；c3 米色连衣裙居中正脸塔景**最佳**；c4 居中但低头；c1/c2/c5 偏心）。⑤**Phase E 部分**（本地 git，桥接已重启）：桥接 `POST /live/lip`+`/live/emotion` 转发路由（未装引擎补丁前如实回传失败不假成功）。**已定默认（2026-07-13）**：用户经 9 轮提示词迭代（甜美→网红→江南→童颜→…最终反查母版）后选定 **p0=cand_20260713_191136_1**（星脸批 s1，米白翻领针织、灵山亭台湖景背景）为**灵山大屏游客端默认**。**关键发现：候选生成质量差是因用了 `wanx2.1-t2i-turbo`；母版 dh_lingshan 实为 `wanx2.1-t2i-plus` + `scripts/gen_sweet_bob_16x9.py` 原 prompt**（已把候选生成器切成 plus+母版 prompt+灵山背景排除大佛人形）。落地：adopt→`custom_20260713_201715`(艺名**云栖**)双比例进 ditto → **lipmatrix 开口体检通过**(说话张口自然无坍缩) → 大屏 portrait 热切上身 + PUT /config 设灵山默认 + avatar-publish 发布 + `lt_run_portrait.sh` 启动默认改云栖底图(.bak_p0default)。手机 main 流仍 dh_lingshan（用户只指定大屏）。候选批留 staging 可继续挑。**Phase E/F 已完成（2026-07-13 GPU 窗口，用户授权）**：**嘴幅热调**——`DITTO_LIP_KNEE` 确认是空旋钮，改新建 `DITTO_LIP_SCALE`：motion_stitch.py `__call__` 逐帧读 env 把 lip 维 `[6,12,14,17,19,20]` 朝闭口拉（scale<1 收小张口）；引擎 routes.py 加 `/set_lip`+`/set_emotion`；桥接 `/live/lip {scale}`+`/live/emotion` 改 scale 语义。GPU 窗口串行重启双流(portrait 先起=云栖、main=dh_lingshan)→lipmatrix 逐档取证 **0.6 无齿/0.75 微露齿/0.68=最大无齿=「刚刚不露齿」→ 定默认 0.68**（双流已 live set + ditto_avatar setdefault 持久化）；管理端嘴幅滑杆启用(0.5-1.0/默认0.68/走应用闸门)。补丁备份 `.bak_lipscale`+仓库镜像 `livetalking_engine/`。**Phase F 全量验收**：test_dh_avatar_meta 32/32、admin Playwright 14/14(含嘴幅滑杆启用+零串扰热切)、kiosk 36/36、RAG 代码零改动(git diff 仅 avatar/bridge/engine)=准确率零回归。R1-R9 全绿。
- ~~用户挑选默认甜美候选~~（已完成：p0/云栖，见上）；~~嘴幅热调~~（已完成 0.68）；②**Phase E 嘴幅热调需 GPU 窗口**——**重大发现：`DITTO_LIP_KNEE` 在 ditto_avatar.py:42 setdefault+日志读取但全 SDK 无消费点**（grep ditto-talkinghead 零命中），知非现役旋钮，需先定位/补建消费点(改逐 chunk 读 env)+加引擎 /set_lip、/set_emotion HTTP 路由(server/routes.py，set_emotion 方法已存 :136)，再串行重启双流(当前 portrait 流仍挂旧坏底 sweet_bob_ditto_portrait_lingshan,重启即修为 dh_lingshan)+lipmatrix 逐档调"刚刚不露齿"值——**此窗口需用户在场确认无 SAM3 训练+人工核唇网格**（当前 GPU 仅双流无训练）；③体检通过后 PUT /config 设用户选定候选为各景区默认（D4）。⚠️注：R8 中轴校验/无人形背景/过渡不用旧帧均已落地，唯"嘴幅初调"待窗口。

- [x] **嘴唇坍缩复发：根因修死 + 三重默认拆弹（2026-07-13，Windows 机，未动 GPU 服务，仅 /live/avatar 热切 + bridge 重启）**：**终局根因 = 背景图里的"人形/面孔剪影"会毒化 Ditto 源处理**——判定链：坏图 `sweet_bob_ditto_portrait_lingshan.png` 用健康母版重跑 compose 竟逐字节复现（管线确定性产物，非历史修图损伤）；人物区像素与母版零差异 → 毒在背景；同管线对照实验 bg_xihu/纯渐变底全部健康、唯 bg_lingshan（大佛人形剪影+日辉）坍缩 → 锁死。修复：①重生成无人形灵山背景（万相，prompt 明令"无人物/佛像/雕像/人形剪影/面孔"，塔影可留）→ compose → **lipmatrix 体检通过后**替换上岗（坏图留档 `.bak_lipcollapse`；仓库资产 `assets/avatar_backgrounds/bg_lingshan.png` 同步换新，毒版改名 `.v1-buddha-lipbreaker.bak` 防再被合成引用）；②**拆三重默认**：bridge 未知 id 不再静默直落甜妹底板、优先 `dh_<scenic>` 专属身份（server.py `_live_avatar_candidates`，commit c5d5cb8，已重启 bridge 实测 UNKNOWN_TEST_ID→dh_gugong）；lt_run*.sh 启动默认形象 sweet_bob→`dh_lingshan__lingshan__{16x9,9x16}`（.bak_startupav，下次重启生效、免人工热切）；switch_avatar.sh 残留 Ampere 旧引擎路径顺手改 4090D（.bak_ampere）。抽验体检：dh_lingshan/dh_gugong/F1/F2/M1/sweet_outfit_vest/新 sweet_bob 竖版全部大开口露齿；16:9 版 `sweet_bob_ditto_bg_lingshan`（640×360）背景无人形不动。工具沉淀 `/root/autodl-tmp/lipmatrix.sh <avatar_id> <tag> [scenic]`。**铁律（已入记忆）：背景生成 prompt 必须排除人形/面孔剪影；新合成底图必须过 lipmatrix 开口体检才能上岗；修复验证必须逐图**。大屏已恢复 dh_lingshan。用户复报"嘴唇坍缩/张不开"。**逐项判别实验（服务器录竖版流→同台词'WELCOME! HAHAHA! OPEN WIDE!'→8fps 嘴部网格图对比）结论：根因 = `sweet_bob_ditto_portrait_lingshan.png` 这一张合成竖版底图本身驱动性损坏**——同引擎下 dh_lingshan/F1_modern/sweet_outfit_vest(同脸!)/母版裸底板 sweet_bob_ditto.png 全部大开口正常，唯独这张图全程抿嘴微启；图片字节 == 7-11 centerfix 备份（即备份时已是损伤版，7-12 回滚"恢复"的就是它，当时判定实验没测这张图故漏网）；SDK 无源缓存、非情绪残留（重 set_source 后依旧）、分辨率无异（720×1280）；该图历史被多轮手术（.shoulderfix_bak/.720bak/.540 变体）疑早期修图致损。**危险放大器：它身兼三重默认**——①bridge `DEFAULT_AVATAR="sweet_bob_ditto"`，未知/legacy avatar_id 一律静默回退到它（server.py:104,149）；②presets 的 female_sweet/female_elegant/female_young 都映射它；③lt_run 启动默认形象。昨日形象工坊上线后该路径被游客点到 →"复发"。**已做**：大屏竖版已热切回 dh_lingshan（口型正常，用户可先用）；测试工具沉淀 `/root/autodl-tmp/lipmatrix.sh`（换形象→录流→嘴部网格 tile 一条龙）。**待续修复清单**：①用健康母版 `sweet_bob_ditto.png` 重合成灵山 9:16 底图替换坏图（scripts/gen_avatar_background.py compose，CPU；换图后 lipmatrix 复验）；②防再犯：bridge 未知 id 回退改 `dh_<scenic>`（勿再落 sweet_bob 坏图）+ lt_run/switch_avatar.sh 启动默认同步换（注意 switch_avatar.sh 还残留指向 Ampere 旧引擎的 DITTO_DATA_ROOT，顺带修）；③全库底图跑一遍 lipmatrix 开口体检（尤其 9x16 全量），坏图登记/替换；④体检法与"合成图三重默认"教训写入记忆。

- [x] **大屏地图导航化 + 形象/音色工坊 + 故宫导览图点亮（2026-07-13，Windows 机，未动 GPU）**：用户三需求（地图显示不全→类高德导航；形象功能区细化对标 iPad 11 寸；使用手册标题清单），优先级=灵山>故宫>其余留空。①**地图"显示不全"治本**：根因=TerminalView `mapHeight` 写死 220px、1672×941 手绘图按宽放大后被裁成一条横带——改为按中栏宽×图片纵横比自适应（钳 [260, 45vh]，用户拖拽后停止接管），MapPanel 重写为 contain 完整整图起步。②**类高德导航**：新 `config/mapRegistry.js`（每景区 image/imgW/imgH/poiPos/facilityPos/legPaths，取代 isLingshan 硬门控；无图景区显"筹备中"，补图+坐标表即点亮零代码），灵山人工描 6 段贴路途经点（key `'poiA>poiB'`，反向自动取反、缺段回退直连）；Catmull-Rom 平滑曲线、当前段白色流动虚线（reduced-motion 静止）、分段进度着色（走过灰/当前高亮+光晕/未走半透明）、起/终 pin、每段弧长中点方向箭头；**导航镜头**：选路线自动 fit-bounds、tourStep 推进 420ms tween 跟随当前段、双击/⛶回全图；触控：双指捏合、滚轮绕光标缩放、44px 悬浮 +/− /取景钮，标记反向缩放保持屏幕恒大（SVG viewBox 改用图片像素坐标，虚线间距不再受纵横比拉伸）；TourControlCard 改读 selectedRoute（修"卡片永远显示默认线"旧偏差）+ haversine 下一站距离/全程里程（信息栏+导航播报词）。③**形象/音色工坊**（零后端）：横条卡放大（64px 缩略图）+「全部形象与音色」入口；新 `AvatarStudioSheet.vue` 底部滑出面板——形象 tab（风格 pill 筛选+大卡网格+本景区专属浮顶徽章+coming_soon 置灰+「已换上」toast，走 /live/avatar portrait 路）、音色 tab（女/男分组+/voice_samples 试听+选中写 currentVoiceId+队列播报确认语即点即听）；voice_id 全链路实测：bridge 日志逐句 Serena→Cherry 换声（liveAsk/liveSay 调用点本就带 voice_id，仅缺 UI）；坑：性别判断不能用 `/male/i`（'female' 含 'male' 子串）。④**故宫点亮**：万相 wanx2.1-t2i-plus 生成 4 张无文字候选（标签由 POI 层负责；存 `/root/autodl-tmp/gugong_map_candidates/`，换图=cp 覆盖 assets/scenic-map-gugong.png 重建），选 1 号等距鸟瞰接入，校准 5 景点+16 设施坐标+5 段中轴贴路，朱红主题+红色路线全景验证 OK。三口径 Playwright 全流程零 pageerror（1920×1080 / 1080×1920 / 1194×834 iPad11）；服务器源备份 *.bak_mapnav；上线 ECS 入口 index-5Y_cZ7jD.js（常开页 10min 内自动热重载）。使用手册「游客大屏端」二级标题清单已交付用户（兼验收检查单）。

- [x] **大屏 UI 方案B落地：向手机端定稿风格靠拢（2026-07-13，Windows 机，未动 GPU）**：用户拍板方案B（手机质感+轻氛围底），手机端与开屏图均不动；大屏需适配电脑显示器 16:9。①`design/global.css` token 全面对齐手机端 webapp 定稿：天蓝 #0284c7→友好靛蓝 #4F5BE0（hover/dark/light 三档同换）、暖橙→珊瑚 #E0785A、底色→暖白 #FEFDFB、中性阶→微蓝紫 hue274、阴影→柔和主色染、圆角 +2px 对齐 0.8rem 基准；景区换肤机制原样（/scenic/theme 运行时覆写 --color-primary）。②两处深蓝渐变页头（HeaderBar + ScenicSelectionView）改手机端浅色风：白底微透+blur、品牌名渐变字（background-clip:text 随主题色）、按钮改中性胶囊（radius-full）、适老激活态金黄→珊瑚。③清硬编码 5 文件：OnboardingWizard ~10 处、MapPanel 10 处（rgba(2,132,199,α)→color-mix 随主题）、TakeawayModal/AssistantBubble/SpeakingWave 兜底色；`design/tokens.js` 确认零引用不动。④TerminalView 方案B质感：氛围罩色改暖白同源并加深（底图只留 ~15% 余韵）、面板重玻璃(blur16)→白卡细边+轻玻璃(blur10)+var(--shadow-md)。Playwright 1920×1080 + 1080×1920 双口径截图核验：两端观感一致、零 pageerror、构建产物旧天蓝零残留。上线 ECS（入口 index-DLUDVzCl.js），源备份 *.bak_schemeB（自昨日网盘存档提取）。⚠️遗留：开屏流程增强（预加载/跳过/交叉淡出）与 splash_url 字段按用户指示暂不做。

- [x] **大屏逐句字幕真信号化 + 真实音波动画 + queue 包装器补漏（2026-07-13 凌晨，Windows 机，未动 GPU）**：①**补漏（重要）**：昨日播报有序化的前端层有断点——kiosk `api/index.js` 的 `liveSay` 包装器漏转发 `queue` 字段，7 处面板传的 `queue:true` 被丢弃、实际仍 interrupt 直发互相打断（昨日验证走 curl 直打桥接未经过包装器所以没暴露）→ 已补一行转发（`.bak_queuefix`）；教训已记入 [[kiosk-***REDACTED***]]：改包装器+调用点两层时验证必须走前端真调用。②**桥接新增 `GET /live/now-playing`**（commit 4114459，API_DOC 6.4）：三处送 `/human` 时（`_drive` 问答逐句 / `_speech_worker_loop` 队列播报 / 直发 say）登记 per-sid「正在播什么」，按字数估算自然过期、打断即清（`_drain_speech_queue` 顺带 pop）；纯内存查表轮询友好。③**kiosk 字幕改真信号驱动**：新 `useNowPlaying.js` 800ms 轮询——播什么显示什么（此前迎宾/客流/路线队列播报完全没字幕），长播报按标点切段随 elapsed/est 进度翻页保持逐句观感；接管期 `store.npOwned=true`，估算队列（useSSEChat）、迎宾手写字幕（TerminalView）、暂停填充语（DigitalHumanStage）三处让位，轮询连续失败 3 次自动回退估算方案。④**音波改真实频谱**：`SpeakingWave.vue` 重写为 canvas 24 柱频谱（`.bak_fakewave`），DigitalHumanStage 在首次解除静音手势里建 WebAudio 图（`createMediaElementSource` 同源反代流可捕获、每 video 仅建一次、断流重连复用同 videoEl；接 destination 保出声），静音/未解锁/构图失败回退正弦假动画。Playwright 双冒烟通过：排队两条+打断一条字幕逐条正确顶替、问答 8 段字幕随每句真实开口切换、零 pageerror。改动文件均 `.bak_nowplaying` 备份，build 上线 ECS（入口 index-Bn6vtAyu.js，常开页自动热重载）。方案一（嘴幅可调）/方案三（UI 向手机端靠拢）取证与方案见 plan 文件；方案三先出设计选型页供用户拍板，方案一实施时需请示 GPU 重启窗口。

- [x] **大屏卡顿终局修复三连 + 播报有序化 + kiosk 去 GPS（2026-07-12 晚，Windows 机，动了 GPU 服务·用户授权）**：用户复报"流畅几秒卡0.5秒"（多轮修后仍在）→ 本次包级取证找到**两个确定性根因并全部修死，6 分钟终验探针零卡顿**（delivery 0.99-1.02 恒实时、缓冲深度稳 1.6s、playbackRate 恒 1.000 连追帧都不需要，含 50s 长播报窗口）。**根因A（主犯）=中继时间戳空洞**：relay 的 mpegts 封装把音频攒成 460-552ms 大块 PES → ECS SRS `srt_to_rtmp` 转 RTMP 时每 ~0.72s 媒体撕出 ~380ms 时间戳空洞（27s 内容被撑成 52s；SRS 24h 刷 8803 条 `audio duration too large` 告警；源头 DTS 完美 40ms 等距、本地复现 mux 干净 → 锁死在 SRS SRT 摄取对大 PES 的处理）→ 修复=`relay_hz.sh` ffmpeg 加 `-muxdelay 0 -muxpreload 0 -pes_payload_size 384 -flush_packets 1`（回退件 `relay_hz.sh.bak_pes`）→ ECS 侧视频 40ms/音频 64ms 全等距零空洞、告警零新增。**根因B（从犯）=待机产帧仅 0.88x 实时**（时间戳修好后暴露：待机每 ~20s 冻 ~3s、说话反而零卡顿）：`base_asr.py get_audio_frame` 静音路径每 20ms 帧白等 10ms 超时 → `timeout 0.01→0.002`（`/root/autodl-tmp/LiveTalking/avatars/audio_features/base_asr.py`，回退件 `.bak_idletimeout`），串行重启双路 LiveTalking 后待机 0.995x 实时；重启后已把双屏热切回 `dh_lingshan`。**播报有序化（商定规则：自动播报一律排队，提问立即打断）**：桥接新增 per-sid 播报队列——`SayIn.queue=true` 入队串行播（`is_speaking` 轮询+估算收尾、90s 过期丢弃、`_ASK_ACTIVE` 计数防队列在 ask 句间停顿抢通道），`/live/ask*` 与 interrupt 直发 say=用户主动内容 → 清队+`/interrupt_talk` 硬清引擎残句（此前只靠"新首句 interrupt 弱冲"，两来源并发会句子穿插且 7 处面板播报互相打断）；实测三条排队严格按序、提问 1.1s 开口顶替（commit d53c0e0，API_DOC 6.3 已登记）。**kiosk 前端**（/root/visitor_web，build 上线 ECS，旧版 `/var/www/kiosk.bak_20260712`）：①播放器加 `enableStashBuffer+stashInitialSize 384`、target 1.2→2.0s/max 3.5s（用户拍板：+0.8s 开口观感换全程顺滑）；②迎宾/客流/设施/导航/路线×3 共 7 处 liveSay 改 `queue:true`；③**GPS 整链禁用**（用户明确大屏=固定端手动选景区：TerminalView 不再 startGps/startTrigger，"定位精度稍低"类语音+角标全消失，`.bak_nogps`）；④cdnfonts 死链移除（遗留待办清账）。⚠️请用户真机大屏 **Ctrl+F5 一次**后复核观感（此后新构建自动热重载接管），通过即可开录演示视频；lt_portrait pts/dts 日志洪水仍留窗口①。详见记忆 [[kiosk-***REDACTED***]]。

- [x] **算法章（第4章）数据充实：概念链路补真实输入/参数/中间结果/局部验证（2026-07-12，Windows 机）**：回应用户批评"缺少真实输入、实际参数、中间结果和局部验证"。数据来源三处全为实测：①生产服务器一次性 trace 脚本（云端 RAG，只读不落库、不碰 GPU）取回真实中间结果——改写器实输"它比乐山大佛高吗？"→"灵山大佛比乐山大佛高吗？"397ms、embed 145-164ms/BM25 31ms/稠密 4.4ms/融合 0.5ms、两路 top 候选原文、RRF 融合分、实体表 22 名、灵山库 113 块、佛足坛 chunk 原文 771 字；②tests/ea_rag_stress.json 门控标定原始分（库外题 top1=0.0065~0.6249、正常题最低 0.2985，解释 0.2 工作点与 0.3 起 1% 误拒的成因）；③tests/eval_report.json 逐题明细（3 道未命中题实录=数字念成中文/同义转述、陷阱题真实回复、各景区消融分项 裸模型西湖68.8% vs 拈花湾15.4%）。落点：4.1.4 真实 chunk 样例、新表 4-4 两路候选实测、4-7 全链路生产轨迹、4-10 各景区消融分项，门控表加 0.1/0.3 两档，Orchestrator 补 105 题零误路由局部验证；第4章表号 4-8 起整体 +3（现 4-1~4-32，内联引用同步）。`总体设计文档-3总体设计-4算法设计.docx` 已重导出（pandoc+reference.docx，5.0MB）。
- [ ] 【需窗口①】**云端检索的锚定叠加观察**（窗口③ 2026-07-12 trace 发现）：生产云端模式（无重排器）下，重复 chunk 会按出现次数叠加实体锚定加成（灵山 113 块中 56 块被锚定，重复块 0.02×N 叠加），"灵山大佛有多高"的标准答案 FAQ 块（融合分 0.059）被挤出 top4（top4 分 0.074~0.091）；本次回答仍正确（其他块含 88 米事实）但存在风险。建议：入库去重，或锚定加成按 doc 去重后只加一次，或云端也上轻量重排。本地模式有 reranker 精排不受影响（97.1% 口径无恙）。

- [x] **数字人嘴唇坍塌修复 + 生成端提速攻坚：原生 TRT 引擎 + 流水线并行化（2026-07-12，Windows 机，动了 GPU 服务·用户授权）**：①**嘴唇压塌成一条线根因 = 昨日 recenter 批量水平平移底图**——判定实验：平移图说话逐帧全程闭唇压扁，恢复原图后同台词张嘴露齿正常 → 275 张底图全量从 `/root/autodl-tmp/ditto_avatars_bak_centerfix_20260711` 回滚，双路热切生效；`digital_human.py` 生成管线的 `_recenter_person` 调用已禁用（防新形象重蹈覆辙，居中改生图 prompt 承担）。②**卡顿根因 = 生产端产帧不足**（SRS 20s 帧计数：竖版 18.8/主 21.7，标称 25；流比实时慢 ~25% → 播放器周期性耗干缓冲回补 ≈"说几个字卡 1 秒"；网络/编码均已排除：源头录流 silencedetect 只剩 0.3-0.8s 标点韵律停顿、rtmp 裸编码基准 720×1280=94fps）。三段修复：**(a) 官方 ONNX 重编原生 Ada TRT 引擎**（`ditto_trt_4090D`；坑：cvt 脚本在 sm≥8.0 上自动加 Ampere_Plus 兼容 flag 已补丁、polygraphy 需装、PATH 需带 lt env；构建脚本 `/root/autodl-tmp/build_trt_ada.sh`）→ GPU util 98%→68%；**(b) putback ROI 化**（mask 覆盖区外不 warp 不 blend，`putback.py`，19.5→11ms）；**(c) TRTWrapper 每模型独立 CUDA 流**（原全部挤默认流 0 → 同进程 warp/decode/stitch 全串行；改独立非阻塞流+调用内同步后各阶段真流水线，`tensorrt_utils.py`；无竞态依据=warp 每帧全新输出张量）→ **竖版 SRS 计数 19→27/s、主路 24.9/s，说话状态下持续达标，GPU 67% 有余量**。逐段耗时埋点保留（`stream_pipeline_online.py` [stage-prof]，每 300 帧 1 行）。**回退件**：`lt_run*.sh.bak_ampere`（指回 Ampere 引擎）、`tensorrt_utils.py.bak_stream0`、`putback.py.bak_roi`、`stream_pipeline_online.py.bak_preprof`。终验：整页截图张嘴说话口型清晰无画面异常；杭州中继侧录流仅剩韵律停顿。⚠️余留：服务重启后形象回启动默认（sweet_bob，既有行为）；本机深夜网络下无头浏览器仍偶见 1.5s 级回缓冲，**请用户在真机大屏 Ctrl+F5 后实测复核**；QwenTTS 空闲 300s 断连有自愈逻辑非本次问题。UI 改版定稿=C 服务岛布局 × B 青瓷配色，数字人链路稳定后开工。

- [x] **kiosk「抿嘴不说话/提问无声」二次排查=旧标签页缓存旧包 + 常开标签自动热重载（2026-07-12，Windows 机）**：用户复报"待机一直抿嘴、提问只有文字"——排查证实**线上包与后端链路全部正常**（竖版路 QwenTTS 合成 0.96s、`/live/say` portrait 200、待机唇形特写自然、当日新页面加载 ask_start 全为 `screen:"portrait"`），而 bridge 日志中用户当天的提问全打 `screen:"main"` = 浏览器里跑的是**换屏修复(index.js.bak_screen 那轮)之前的旧 JS**：大屏标签页常开不刷新，index.html 虽已 no-cache 但 SPA 不重载就永远用旧 bundle，驱动打到看不见的 8010 主路 →"抿嘴"实为"永不开口的待机"。治本：`/root/visitor_web/src/App.vue`（.bak_autoreload 已备）加**新构建自动热重载**——每 10min `fetch index.html(no-store)` 比对入口 chunk 指纹，发现新构建且用户空闲≥3min 时 `location.reload()`；已 build+rsync 上线（入口 index-DqdPNGGj.js），Playwright 冒烟视频正常。⚠️告知用户：现存旧标签页仍需**手动刷新一次**（Ctrl+F5），此后永不复发。顺带记录：lt_portrait 日志有 QwenTTS 空闲 300s 服务端断连事件，现有"合成前重连+失败重试一次"逻辑已正确自愈（本次实测 0.96s 重连合成），非本次故障根因。

- [x] **大屏端三连修：SRT 中继治卡顿跳句 + 竖版流/底图重居中 + 场景化 UI 融合（2026-07-11，Windows 机）**：①**卡顿跳句根因=北京→杭州公网 RTMP 被 AutoDL 出口 NAT 在带宽突发时掐断（relay 日志 30~60s 一次 Broken pipe，杭州 SRS 同刻 ECONNRESET）**→ 中继改走 SRT（ECS SRS 5.0.213 host 网络开 `srt_server` UDP 10080/latency 500ms/`srt_to_rtmp`，`relay_hz.sh` 改 ffmpeg 推 `srt://…streamid=#!::r=live/X,m=publish`，restart 0.5s+rw_timeout；安全组 UDP 10080 用户已放行；回退件 `relay_hz.sh.rtmp_bak`+`/root/srs.conf.bak_srt_20260711`），切换后 25 分钟含多次真实拉流播报**零断连**（旧链路同期 10+ 次）；播放端 kiosk+管理端预览统一换 mpegts.js 1.8 `liveSync` 倍速追帧（1.12x 悄悄追、绝不跳秒）+ 无限重试指数退避 + 断流 canvas 冻帧 20s 内不闪占位。②居中两个 bug：kiosk 一直在播 16:9 横流 cover 裁掉 75% 宽（专用竖流早已中继到位没人用）→ 切 `/stream_portrait.flv`（横流兜底、`object-position: center top`）；管理端预览框 `aspect-ratio 9/16` 被 max-height 钳制变宽致 cover 裁头 → 宽度联动 `min(100%, calc((100dvh-232px)*9/16))`（实测 0.563 精确 9:16）。治本=底图人物质心居中：`scripts/recenter_avatars.py`（cv2 最大人脸→水平平移+reflect 补边）批量修 **235/275 张偏心底图**（最大偏 ±100px；备份 `/root/autodl-tmp/ditto_avatars_bak_centerfix_20260711`，双路已热切重载生效），生成管线 `digital_human.py` 落盘前同校正（commit 3eb7948）。③kiosk 场景化 UI：桥接新增 `GET /live/scenic-bg`（当前形象底板缩小模糊 JPEG，API_DOC 4.7.1，commit f9807ea）→ 页面铺与数字人视频**同源**氛围底，面板改半透明玻璃（backdrop-filter+webkit 前缀），页头改 `color-mix` 随景区主题渐变（灵山禅金蓝/故宫朱红实测切换生效，换库不换码），视频框边缘羽化收边+字幕玻璃化。kiosk 源文件改动在 `/root/visitor_web`（队友工程，.bak_scenic/.bak_livesync 已备），build --base=/kiosk/ 后 rsync 至 ECS `/var/www/kiosk`（旧版备份 `/var/www/kiosk.bak_20260711`）。⚠️余留：macOS Safari 真机需抽检（liveSync/backdrop-filter 理论兼容）；单路竖流全景区共用，kiosk 切景区不会自动换直播形象（既有约束）；gugong 无导览图为数据缺失非本次问题。

- [x] **实时弹幕「游客正在问」+ Inter 字体升级（2026-07-11，Windows 机）**：①后端 `GET /analytics/danmaku`（近24h真实提问清洗：长数字脱敏/40字截断/归一化去重/blocklist 过滤 GPS 定位话术污染行；intent 关键词推断 qa/navigation/recommend/photo/empathy；不足时 `backend/data/danmaku_bank.py` 8景区手写题库兜底，`since` 增量轮询；API_DOC 3.3.5 已登记）；播种器演示提问 45% 混入同一题库口径同源，已重播种 8 景区。②前端 `DanmakuFlow.vue`（服务器 /root/digital-human）：纯 CSS transform 动画+轨道 busyUntil 调度防追尾、节流投放 0.8~2.3s/条、20s 增量轮询、断网/队列耗尽洗牌循环永不空场、hover 暂停、Tabler 意图图标×情绪着色；落位=大屏头部下方 3 轨暗玻璃带（矮视口自适应 2 轨；大屏头部新增弹幕开关，localStorage `admin-danmaku`）+ 管理端顶栏中段迷你条（全 tab 可见）。③字体借鉴学长国一（实为 Arco 默认栈，无商业字体文件）：自托管 Inter latin 400-700（~97KB，SIL OFL）打头、中文回落鸿蒙/雅黑，`--el-font-family` 对齐 + body tabular-nums；**根因：CDN 鸿蒙字体包内 `:lang(zh-CN)` 规则特异性压过 body 声明 → 摘除 admin/index.html 的 jsdelivr 外链**（本地 /fonts 鸿蒙 woff2 本就自托管，顺带断外网依赖；备份 index.html.bak_cdnfont）。④连带修大屏趋势图 24vh 定高溢出压下排 → 改随面板弹性伸缩，弹幕开关切换补图表 resize。Playwright 双形态验证通过（顶栏/大屏 pills 均在飘、零 pageerror、body 字体 Inter 打头）。追加（用户两轮调优定稿）：顶栏 52→62px（1.2 倍，admin-layout padding-top 联动）、侧栏 220→240px；字号最终=净+1（弹幕 13.5px/轨高 33、导航 14、顶栏元素 13~15），惟 logo 28px+品牌名 18px 再加大一号；AI 助手输出接 markdown 渲染（mdToHtml 共用函数：报告正文+AI 气泡，转义后转 h4/ul/b/code/hr，气泡内 :deep 样式，覆盖 pre-wrap）。中文主字体定稿=**阿里巴巴普惠体 3.0**（免费商用；服务器 fonttools 子集化 GB2312 6763 字+拉丁全角 → woff2 ~950KB×4 字重 400-700 自托管，生僻字回落鸿蒙→系统；深浅两主题 token 同源 Inter+普惠体，暗色 token 原缺 Inter 一并补齐）。品牌区强化（用户选方案A）：logo 34px+「途叨叨」20px/800 渐变蓝文字（浅 #1B5FD9→#5B9CF8 / 深 #5B9CF8→#8FBFFA，background-clip:text+兜底色），副标题淡化 12px 灰+细竖线隔开。数据大屏字号集体+1（图表 fontSize 27 处+CSS 20 处，按行区间脚本单次处理；弹幕带保持 13.5 不动）。本版管理端已整体备份至 AutoDL 网盘 `/autodl-fs/data/digital-human_admin_backup/digital-human_20260711_danmaku-puhuiti-brand.tar.gz`（23MB，含 dist 成品可免构建上线，排除 node_modules/venv；附 README 恢复说明）。
- [x] **管理端 UI 大改版：登录页双主题 + 数据大屏暗玻璃全屏模式 + 演示造数（2026-07-11，Windows 机）**：①登录页新增明暗切换胶囊（与侧栏共用 localStorage 约定），浅色左板从灰底改 HHU 蓝渐变，整页连续渐变消除左右割裂（多级色标缓入缓出防马赫带、白光晕挪离接缝），admin-dark.css 修正失效旧选择器（.login-card→.l-card）并补齐 el-switch/el-checkbox 深色覆盖；②数据大屏彻底重做：从侧栏 tab 改为**全屏投放模式**（侧栏「投放」分组渐变启动卡进入=Teleport+Fullscreen API，退出=右上按钮/Esc/fullscreenchange 三路同步、回到进入前页面、首次进入弹提示；刷新不记忆大屏 tab），视觉换**暗玻璃悬浮**（#12141F 底+紫/青/粉光斑+18px 磨砂玻璃卡，左右栏 300/330 不等宽+面板 flex 1.3/0.85/0.72 交错，边界互不对齐），图表富化（趋势双序列+峰谷 markPoint、新增时段热度双峰曲线、图表尺寸统一 min-height 110）；③近7日冷启动三级处理：全真数原样/部分有数按**周节律推演补全**（真值反推基准量×周末1.72 峰谷因子，空心虚线点+tooltip（推演）+面板口径标签）/全零走演示曲线；④底部新增**决策数据带**（xlsx 行为数据真接口）：消费结构环（bi/spending，客单价¥1151）+客群年龄结构（bi/demographics，7 桶+性别 meta）+景区运营对比（bi/attractions 访问量柱×满意度线双轴）；⑤`scripts/seed_demo_data.py`（commit d81e2f2）：conversations/events 造 8 景区近 7 天演示数据（每景区约 330 对话+700 事件，周节律+双峰时段+合理权重），demo- 前缀 `--wipe` 一键清除、按天种子幂等、已在服务器执行并全接口验证；侧栏重组为「日常运营/数字人/投放」三分组防空荡。管理端前端改动均已 build 上线（前端不在 git，改动落服务器 /root/digital-human）。
- [x] **管理端 logo 白框修复定稿（2026-07-11，用户验收）**：原图 RGB 无透明通道近白底 → 有色背景现白色方块。图案拓扑不闭合（头发穿出水滴轮廓），泛洪/几何拟合均失败，最终用「行列收缩包裹」法（art | row_span & col_span）：水滴内部白色全保留、外部透明、无白晕。原稿备份服务器 .bak_whitebox；方法沉淀在记忆 [[admin-logo-shrinkwrap]]。⚠️本条目由服务器侧代笔（本地 AI_Local/E 盘当时掉线，本地仓库需 git pull 同步）。
- [x] **杭州 ECS 固定公网入口上线（2026-07-10，Windows 机）**：游客端手机 `https://114.55.178.51:8443/`（或 :80）、大屏 kiosk `…:8443/kiosk/`、管理端 `…:8443/admin`，全项公网验证 200、直播流真实出流。实现 = AutoDL supervisor 新增 `tunnel_hz`（SSH 反向隧道 16006→bridge:6006，免密+autorestart）+ ECS nginx 上游从写死的 seetacloud 轮换域名全部改为隧道（旧配置备份 `default.bak_tunnel_*`；页面从此永远是 AutoDL 最新构建，token 轮换免疫）；视频流保持 relay_hz→ECS 本地 SRS 不过隧道。⚠️自签证书需手动信任；麦克风必须走 :8443 https；ECS 上另有用户水尺项目的 frps 勿动。详见记忆 [[hz-public-gateway]]。
- [x] **管理端按赛题梳理重构 + 假功能全部做真（2026-07-10，Windows 机）**：①后端新增 `POST /kb/self-test`（从 ChromaDB chunk 现场出题→完整 RAG 链路作答→关键词评分，不污染 conversations/缓存；实测灵山 3/3=100%、4.4s/题）、`GET/PUT/DELETE /kb/retrieval-config`（按景区覆盖 策略/top_k/门控阈值，SQLite 持久化，无配置=97.1% 基线零扰动）、`POST /kb/docs/{id}/reindex`（按 source 删旧 chunk 重灌）+ `DELETE /kb/docs/{id}` 升级真删向量；修两个已知坑：知识写操作自动清答案缓存+实体缓存、路由顺序 bug（DELETE /kb/retrieval-config 曾被 /kb/{scenic_id} 通配抢匹配误删库）。回归 tests/test_kb_admin.py 16/16。②管理端前端（队友工程 /root/digital-human，已 tar 备份后改+build 上线）：检索设置/重建索引/AI生成进度三个假功能接真；新增 知识库体检 tab、感受度报告「生成AI报告」按钮（接 /analytics/report）、大屏应急广播弹窗（/live/say 双屏可选）；操作逻辑整理=大屏默认内嵌+「投屏模式」才全屏（退出不再跳形象管理）、导航按使用频率重排（大屏→知识库→报告→形象）、scenicId 单源（修大屏/报告查错景区风险）、上传整库替换开关（防批量竞态）、侧栏景区名改只读、登录页品牌统一途叨叨；AI 助手数据源 hot-topics→topic-intents（admin_api 已重启）。API_DOC 已同步。⚠️余留：管理端写接口鉴权（X-Admin-Key）仍未做；AI 生成形象需 GPU 机的 Ditto 目录（云端 rag 会 503，属预期降级）。
- [x] **Windows→AutoDL git 同步链路跑通（2026-07-10，Windows 机）**：本机公钥免密 `ssh autodl`（connect.bjb2.seetacloud.com:19416，`~/.ssh/config` 已配 autodl/hz-ecs 别名）；服务器建 bare 仓库 `/root/autodl-tmp/repos/Digital_Person.git`（本地 remote 名 `autodl`），live 目录 `/root/autodl-tmp/Digital_Person` 已 git 化并与 main 对齐（迁移前脏工作区已收成 commit 58ac983+d5d7dd8；服务器旧版漂移文件备份在 `/root/autodl-tmp/pre_git_backup/`）。**日常流程：本机 commit → `git push autodl main` → bare 仓库 post-receive 钩子自动 `git pull` 进 live 目录 → 需要时手动 `supervisorctl restart rag bridge`（钩子不自动重启服务）**。注意：`webapp/dist` 不在 git 内（.gitignore dist/），前端发布仍需本机 build 后 scp 上去。顺带部署：prompts.py 体力轴裁决 + config.py 本地 LLM 兜底配置上服务器（已重启 rag 验证）。

**【前端窗口启用中】**（2026-06-13 起，用户指定：本窗口=窗口③前端细磨，长期负责 `webapp/ miniprogram/ talk.html`；窗口①不碰前端。服务启停仍归窗口①，端口不通在此留言。）

- [x] **形象管理·灵山×故宫双景区区分度 + 故宫专属身份（2026-06-26）**：scenic_type 类型画像底座（`backend/rag/scenic_types.py`：灵山=religious/故宫=museum… 按类型差异化讲解口吻·主动提醒·推荐侧重，纯数据零分支）；故宫专属身份 `dh_gugong`（沿用甜美脸+故宫背景，640×360/720×1280 底板）；`get_config` 智能默认 `dh_<scenic>` 零 DB 播种；形象工坊+管理端按绑定身份浮顶+「本景区专属」徽章+类型语境标签；形象命名正式化（去"甜美/清纯"→「<景区>·导览专员」/亲和·端庄知性）。准确率回归 100%、scenic_types 24/24、gugong 12/12、situation 26/26；已部署 AutoDL（仅重启 rag+bridge，GPU 未碰）。详见 [[scenic-type-differentiation]]。⚠️待晨检：公网网关 URL（token 轮换需控制台取）、故宫真机热切观感、管理端前端是否同步部署。

#### 已完成里程碑（详情见 git 历史 + 记忆，按需展开）

- **RAG 问答**：混合检索（BGE-M3 稠密 + BM25 稀疏）+ BGE-Reranker 重排 + QueryRewrite + EA-RAG 融合 + LRU 缓存；8 景区"换库不换码"；**准确率 97.1%（105 题）**。
- **数字人引擎**：MuseTalk → **Ditto** 全脸驱动（25.5fps / 首帧 719ms / 2.7G，治"死脸"）；TTS = Qwen-TTS；情绪→Ditto 表情条件；形象**热拔插切换**（~1s 不断流）；推流双向自愈、延迟攻坚至端到端 ~4.7s。详见 [[ditto-engine]]。
- **形象管理**：形象工坊五段（库 / 换装衣橱 / AI 定制 / 音色 / 背景）+ 管理端配置 tab；`/digital-human/{config,presets,generate}` + `/live/avatar` 热切；6 景区身份库 + 万相"人景一体"AI 生成。
- **创新点**：多智能体 Orchestrator（5 意图）、同行人格 `group_type`、视觉定位两段式、空间感知主动导游、景区类型画像、自身情况 5 维情境、扫码接力 / 家庭同游。
- **前端 webapp**：React + Tailwind 商业版（迎宾开场 / 跟我游高德地图 / 电子明信片 / 4 语言 / Phosphor 图标 / 鸿蒙字体）；跨平台手机网页（iOS HLS / 安卓 FLV）。
- **数据大屏接口**（供队友两块大屏）：analytics dashboard / bi / topic-intents / sentiment / crowd（POI 级实时）+ kb 管理 CRUD。
- **部署**：AutoDL 单网关全栈（RAG + 双路 LiveTalking 16:9/9:16 + SRS + 桥接），supervisor 守护、推流自愈；整套"开箱即跑"备份在网盘（[[system-backup-restore]]）。

#### 活跃待办（跨窗口，未完成）

- [ ] 【需窗口②】**总体设计文档纠错 + ground-truth 口径**（窗口① 2026-06-22）：审 `git diff docs/总体设计文档.md` 后连同自己改动一并 commit；核验 4.8 节 arXiv 与第 10 章竞品外链真实性；统一「语言数」口径（UI 4 语 vs lang 参数 9）；遵 `docs/CLAUDE.md` 第 11 条（惜墨如金 + 学长平实工程体 + 插图占位由用户手画）。**ground-truth 勿回退**：品牌「途叨叨」、导游名去人名化「<景区简称>AI智能导览数字人」、qa=qwen-plus / 生成性意图=qwen-flash / 多模态=qwen3-vl-plus / ASR=faster-whisper / TTS=Qwen-TTS、引擎 Ditto（25.5fps/719ms/2.7G，MuseTalk 仅历史）、准确率 97.1%（105 题；97.7% 仅限 44 题语境）、公网=AutoDL 单网关（ECS 已弃）+ supervisor（非 systemd）。
- [ ] 【需窗口①】**丰富管理端依赖的后端数据**（窗口③ 2026-06-15 审计）：管理端 15 个 analytics/kb 端点全 200 对齐，但 5 处数据空壳——hot-topics 应改 topic-intents（n-gram 碎片 + GPS 兜底回复污染 user_message，需修埋点 + 清污染行）、kb/faq 与 kb/docs 空（播种 FAQ + 登记已 ingest 文档）、analytics/profile interests 稀疏、knowledge-gaps 偏薄。数据厚了管理端各板块立刻丰富。
- [ ] 【需窗口①】**管理端写接口鉴权**（窗口② 2026-06-13）：`/kb/upload`、`DELETE /kb/{id}`、`PUT /digital-human/config` 等加 `X-Admin-Key` 头 + `.env` 的 `ADMIN_API_KEY`（FastAPI dependency 一个函数）；游客端只读接口不动。落地后窗口②补设计文档 8.4 鉴权节 + API_DOC。
- [ ] **非阻塞 backlog**：8 景区纯风景 postcard 背景图重生成（现程序化水墨兜底）、形象工坊 6 套 outfit 烘录解锁（face16 源图已备）；横版底板需求已被 Ditto"驱动原图"弱化。

---

## 数字人选型决策（2026-06-01 定稿，取代 5-23 的阿里云方案）

### 最终方案：本地 LiveTalking + **Ditto** 全脸驱动 + 自研 RAG 后端

演示态架构（本地 4080 开发/录制；公网走 AutoDL 单网关 `https://<实例>:8443`）：

```
手机浏览器 / 微信 H5
    ↓ HTTP-FLV（mpegts.js）/ HLS（iOS）
本地 4080 机器
  ├─ LiveTalking :8010   Ditto 全脸驱动（25.5fps），RTMP 推 SRS
  ├─ 桥接层 :9000        串 RAG→数字人、/live/avatar 热切形象、反代 /stream.flv
  └─ RAG 后端 :8000      cloud 模式（0 显存），检索 ~0.5s
AutoDL 公网网关 :8443 → SRS + 两路 LiveTalking(16:9/9:16) + RAG + 桥接，扫码即用
```

**引擎 = Ditto**（2026-06-12 起替换 MuseTalk）：LivePortrait warp「驱动原图本人」→ 身份/取景/眼神全保留 + 全脸协同动 + 仅 2.7G，根治 MuseTalk「活嘴死脸」。源肖像 PNG 即形象（景区背景离线烘进源图、运行时零开销），改 PNG 即换形象/换景区，**形象通用可配置**坐实赛题。MuseTalk 仅作历史回退（`--model musetalk`）。详见 [[ditto-engine]]、[[project-digital-human]]。

**选型理由**：阿里云数字人太贵；讯飞 Web SDK 仅 PC、不支持移动端浏览器。LiveTalking 本地零成本、HTTP-FLV 流任意浏览器（含手机/微信 H5）可播、`/human` 外部文字驱动直接接 RAG。桥接层端点（`/live/ask*`、`/live/avatar`、`/live/say`、`/live/health`）契约见 `API_DOC.md`。

### 本地全栈启动顺序（开发/演示，RTMP→FLV）

> RAG 用 `DEPLOY_MODE=cloud`（0 显存）、ASR 走 CPU，把 4080 整块留给数字人；全程不需要 ECS。
> Ditto TRT 需 `LD_LIBRARY_PATH=cudnn8`（TRT8.6.1 要 cuDNN8，与 torch 的 cuDNN9 共存）。
```bash
# ① SRS 媒体服务器（docker，收 RTMP 转 HTTP-FLV；只需启一次，会常驻）
docker start srs   # 端口 1935(RTMP) 1985(API) 8080(HTTP-FLV)

# ② 数字人（Ditto 全脸驱动，2026-06-12 起主引擎；RTMP 推流；TTS 用百炼 Qwen-TTS 云端实时）
#    --avatar_id 经 resolve_avatar.py 解析 = 形象 + 景区场景背景变体（管理端配 background_id 后下次启动自动换）
cd ~/Desktop/LiveTalking && unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy
DASHSCOPE_API_KEY=$(grep DASHSCOPE_API_KEY ~/Desktop/Digital_Person/.env | cut -d= -f2) \
LD_LIBRARY_PATH=/home/jiale/Desktop/cudnn8/nvidia/cudnn/lib \
  ~/miniconda3/envs/livetalking/bin/python app.py --transport rtmp --model ditto \
  --avatar_id $(~/Desktop/Digital_Person/.venv/bin/python ~/Desktop/Digital_Person/scripts/resolve_avatar.py --scenic lingshan) \
  --tts qwentts --REF_FILE Serena --push_url 'rtmp://localhost/live/livestream'
# 注：LD_LIBRARY_PATH=cudnn8 是 Ditto TRT 必需（TRT8.6.1 要 cuDNN8，与 torch 的 cuDNN9 共存）；详见 [[ditto-engine]]
# 注：--tts qwentts 需 livetalking 环境装 dashscope>=1.25.11；音色 Serena(知性温柔女声=默认)/Cherry/Jada(吴语)/Ethan/Dylan(京腔)
# 注：MuseTalk 旧引擎仍可用：--model musetalk --avatar_id sweet_bob --batch_size 4 + PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True（情绪底座 _happy/_concerned 热切换）

# ③ RAG 后端（cloud 模式，0 显存，0.0.0.0 让手机可访问）
cd ~/Desktop/Digital_Person && DEPLOY_MODE=cloud .venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
# ④ 桥接层（含 /stream.flv 反代：借桥接 CORS 让前端同源播 FLV，绕开 SRS 无 CORS 头）
cd ~/Desktop/Digital_Person && RAG_BASE=http://localhost:8000 LIVETALKING_BASE=http://localhost:8010 \
  .venv/bin/uvicorn bridge.server:app --host 0.0.0.0 --port 9000
```

验证链路：`curl localhost:1985/api/v1/streams/`（看 `active:true`）、`curl localhost:9000/live/health`。

访问（本机用 **localhost**；手机同 WiFi 用 `hostname -I` 查的 IP）：
- **`http://localhost:9000/` — 正式游客端（React 商业版 webapp，窗口③产出，唯一对外页）**：桥接当统一入口，
  托管 webapp/dist + 反代 `/rag /live /hls /stream.flv /vendor`，单源无跨域。2026-06-13 实测连通 Ditto 直播栈
  （灵山场景背景 + 主动迎宾 + 今日游园天气客流卡全部正常）。
- ⚠️ `talk.html`（`GET /talk`，RAG :8000）与 `/legacy`（桥接）**已弃用**，仅作 dist 缺失时的回退页，演示一律用 `:9000/`。
- `http://localhost:8000/m` — 后端功能测试台（开发自测用）
- ⚠️ 本机浏览器**别用局域网 IP**：系统代理(clash :12334)会劫持局域网 IP→502。用 localhost 或给代理加「绕过局域网」。

### 已排除方案

| 方案 | 排除原因 |
|---|---|
| 阿里云数字人 API | 商业计费太贵 |
| 讯飞数字人 Web SDK | 仅 PC Web，不支持移动端浏览器，卡赛题手机端要求 |
| SadTalker | 每句生成 10-30s，超 <5s 延迟红线 |
| Three.js + VRM | 动漫风格不适合景区导游，自然度输给写实方案 |

### 分工（2026-06-13 更新：主体全栈 + 队友承担两块大屏）

用户负责主体全栈：RAG 后端 + 桥接层 + LiveTalking 部署 + 形象生成 + 游客端手机网页/APK +
管理端手机 web + 交付材料；**队友承担 游客端大屏 web 与 管理端数据大屏 web**（我方供接口联调）。
Claude Code 作为协作编程伙伴全程参与。（曾一度"一人全栈"，2026-06-13 队友回归分担大屏。）

---

## 「灵境·导览」升级任务清单（来自新idea文档）

### 创新一：多智能体 Orchestrator（已完成 MVP，commit 6d96376）

- [x] **意图分类器**（`backend/agent/orchestrator.py`）
  - 五类：`qa` / `navigation` / `recommend` / `empathy` / `chitchat`
  - 混合策略：规则快筛命中即路由（0ms），模糊才 qwen-turbo 兜底
- [x] **意图处理器**（`backend/agent/handlers.py`）
  - 每类意图注入差异化任务指令到 system prompt（统一链路，无需独立模型）
  - 闲聊跳过 RAG 检索
- [x] **接入 `/chat` 主链路**（`pipeline.py` 入口分派，qa 分支零改动保住 97.7%）
- [x] **SSE 新增 `intent` 事件**（最早下发，供前端展示当前意图）
- [ ] **compound 复合请求拆解**（第二步：把"带孩子去厕所路上讲故事"拆成子任务串行执行）

### 创新二：同行人格切换（已完成，待 commit）

- [x] **`group_type` 参数**（ChatRequest，默认 `adult`）
  - `adult` / `family_kids` / `senior` / `couple`
- [x] **叙事人格指令**（`backend/llm/prompts.py` `_build_persona_directive`）
  - 亲子：讲故事+互动提问+亲子设施；老年：慢节奏+无障碍+休息点；情侣：浪漫+机位+祈福
  - 缓存键升级 `group_type::lang::query`，隔离不同人格
- [ ] **同步到 API_DOC.md**（`/chat` 补充 `group_type` + `intent` 字段说明）

> 设计思路详见 `docs/多智能体与人格切换设计.md`（答辩/总体设计文档用）

### 创新三：视觉辅助定位（简化版，加分项）

- [ ] **增强 `POST /chat/image` 的定位能力**
  - system prompt 加入：若图片中有景区地标，优先识别当前位置后再作答
  - 测试：拍灵山大佛照片 → 自动回答"您正在大佛广场，……"

- [ ] **景点图片特征库**（可选，如有时间）
  - 每个景点 2-3 张参考图存入知识库，用 qwen-vl 做图文匹配

### 创新四：空间感知「主动导游」（2026-06-04 讨论定向，产品总纲）

> 立意：把产品从「会说话的问答框」升级为**真正的导游**。真实导游职责实证（来源：导游岗位职责、
> "what makes a great tour guide"）= **讲故事的人 + 带路的人 + 随机应变的人**。
> 用户直觉「会说话还不够」精准命中后两项——也正是当前最缺的。

**真实导游职责 → 我们的功能映射**

| 真实导游职责 | 我们的功能 | 现状 |
|---|---|---|
| 讲解/讲故事（灵魂：事实→愿意听的体验） | RAG + 叙事人格 | ✅ 有，偏"报事实"，可调更"讲故事" |
| 带路/行程组织/控制节奏 | 路线推荐 + 逐段指路 | 路线推荐✅；**逐段指路缺** |
| 答疑 | RAG 问答 | ✅ 97.1%（105 题） |
| 随机应变（天气/人流→改行程） | 时间/天气/人流上下文感知 | ❌ **缺** |
| 安全 & 关怀 & 微笑服务 | empathy 意图 + 主动关怀 | empathy✅；主动性缺 |
| 因人而异（老人/孩子/情侣） | `group_type` 人格 | ✅ 有 |
| 会看地图、会用导航（导游硬技能） | 视觉定位 + 指路 | ❌ **缺（创新三）** |

**核心差别 = 主动**：触发源从「提问」扩展到「位置/时间/上下文」。多智能体已有
`navigation`/`recommend`/`empathy` 意图，缺的是由空间/上下文触发，而非提问触发。

**AR 的诚实拆解（关键认知）**：
- ✅ **AR-lite（做，初赛能落地）**：相机拍一帧 → qwen-vl 认地标 → 定位 + 口语指路。
  复用 `/chat/image`，体验上"开相机它就懂我在哪、给我指路"，**用户感觉到的 AR 80% 来自这里**。
- ⚠️ **真 AR（实景叠加 3D 箭头）= 深坑**：需 SLAM/ARCore/8thWall 空间定位+姿态追踪，
  一人几周必误交付。**标为赛后/决赛拉伸项**，答辩说"已规划"即可。

**落地优先级（演示惊艳 ÷ 工作量）**：
1. GPS 位置感知 + 主动讲解（`navigator.geolocation`，可加"模拟我在X点"下拉做演示）
2. 拍照视觉定位（= 创新三，坐实多模态硬指标）
3. 文字/语音逐段指路（景点结构化数据建关系图 + RAG）
4. 时间/天气感知推荐（天气 API + 当前时间，低成本高"贴心感"）

**演示叙事线**：打开 App→数字人微笑打招呼→开相机拍大佛→视觉定位"您在大佛广场"→
按 group_type 主动"带孩子我用讲故事方式"→指路→看天气"午后日晒强，先去室内梵宫"→边走边讲解。
（一条线串起 多模态+多智能体+空间感知+主动性+人格）

### 创新五：景区类型差异化画像（2026-06-12 头脑风暴定向，产品总纲）

> 立意：回答评委灵魂拷问——"换库不换码,那黄山和故宫的导游说一模一样的话,叫通用还是叫**同质化**?"
> 答案 = **泛化 ≠ 千人一面**：同一套代码,按景区类型呈现恰当的不同。`scenic_type` 管"景区是什么"、
> `group_type` 管"游客是谁",**两个正交维度**。另一来源 = 双角色头脑风暴结论：真实景区问询量大头是
> **服务性问答**（厕所/演出时间/紧急求助）而非文化问答,评委现场问"最近的厕所在哪"答含糊会砸 97% 光环。

**类型学（现有 8 景区天然覆盖 5 类）**

| scenic_type | 我们的景区 | 该类游客的根本性差异诉求 |
|---|---|---|
| 宗教人文 religious | 灵山 | 礼仪禁忌（殿内拍照/衣着）、**演出场次**（九龙灌浴）、祈福流程 |
| 自然山岳 mountain | 黄山、张家界 | **安全与体力第一**：天气突变、索道、日出时刻、装备、体力分级路线 |
| 博物馆/遗址 museum | 故宫、兵马俑、莫高窟 | **预约限流**、文物保护规则（莫高窟窟内**禁拍**）、深度讲解、动线单向 |
| 开放城市 urban_open | 西湖 | 免票无边界、**交通接驳**（地铁/船票）、夜景 |
| 度假小镇 resort_town | 拈花湾 | 住宿餐饮、夜游夜演、慢节奏"不赶景点" |

**类型差异落在 5 个杠杆**：①导游人格侧重（山岳=安全管家/博物馆=学者型/小镇=生活方式主理人）
②路线推荐的预算变量（体力预算 vs 时间+场次预算 vs 交通串联）③安全规则的**主动提醒**（莫高窟拍照
定位后应主动提"窟内禁拍"；黄山问日出附"山顶 5℃带外套"）④emergency SOP 按类型配模板（山上失温
≠馆内走散≠开放景区落水）⑤客流模型驱动因子（山岳=天气驱动；博物馆=预约配额,满了该建议"约后天"
而非"错峰"）。

**落地铁律：类型差异必须是配置+数据,不许 if-else 代码分支**（守住"换库不换码"）：
`SCENIC_CONFIG` 加 `scenic_type` 字段 + 新增 `TYPE_PROFILES` 纯数据表（人格侧重指令片段/推荐准则/
主动提醒规则/emergency SOP 模板/客流驱动因子），注入点 = 现有 `_directive_with_context`（与客流/
天气同一个口子）。新景区接入成本 = 数据 + 3 行配置（多选一个类型），零新代码路径。

**施工顺序（演示惊艳 ÷ 工作量,类型画像是 2/3/5 的承载底座）**：
1. [ ] `TYPE_PROFILES` + `scenic_type` 配置注入（~半天,底座）
2. [ ] `emergency` 意图 + 按类型 SOP 兜底模板（~2h,**防扣分必做**：游客喊救命不能回共情话术,要给广播站电话+最近服务点）
3. [ ] 演出时刻表问答（~半天,灵山/拈花湾先做）：结构化数据加场次字段,时间感知已有→"现在14:20,下一场九龙灌浴14:30,从大佛广场走过去约8分钟,建议现在出发"（KB+时间+空间一句话串起,演示视频天然镜头）
4. [ ] 管理端「知识库自检评测」（~1天,可并行）：产品化 `tests/eval_kb.py` 派生题逻辑为 `POST /kb/self-test`,上传新库→自动生成测试题→出准确率报告,直接回应"换库后还能90%吗"
5. [ ] 就近设施指引（~半天）：结构化数据位置字段+当前位置→最近厕所/餐厅/医务室（景区问询量第一名）
6. [ ] （可选）管理端「高频问询点位」洞察视图——撑起"数字人=景区传感器"叙事（很多人问厕所→该处指示牌不足）；应急广播推送（`/live/say` 已能说任意话,管理端加公告输入框即通）

**演示杀手镜头**：同一句"帮我推荐半天路线"三连切——黄山→体力分配+索道,故宫→中轴线+预约,
拈花湾→"别赶,傍晚看灯"。30 秒让评委直观看到"通用但不同质"。
**文档收口**：创新综述新增维度「插拔式知识库（换库不换码）× 景区类型画像（换库不同人格）」；
eval 按类型加特征题（黄山问装备/莫高窟问拍照规则）证差异化真生效。

### 初赛交付材料（硬性）

- [ ] **总体设计文档**：以 `新idea景区导览AI数字人.docx` 为底稿，补充：
  - 实测准确率 97.1%（105 题，8 景区；97.7% 仅限 44 题语境）
  - 真实延迟数据（后端首句 ~2s）
  - 各接口实现截图/示例
  - 多智能体架构图（可用文档中现有图）

#### 撰写规范 · 对标学长国一文档（`docs/两年前学长做的另一个赛题的详细设计文档.docx`）

> 学长拿**国一**的设计文档（11章81标题15表）。写我们文档时套这套范式，方法论记忆见 [[design-doc-methodology]]。

**11 章骨架**：引言(编写目的+**项目背景痛点**)→需求分析(按角色+用例图；算法需求用"预期输入/输出"契约)→总体设计(技术选型+系统架构)→**算法设计【重头戏·最大篇幅·深入原理】**→功能模块设计(讲数据流转)→数据库设计→数据交互设计→接口/权限/异常→界面设计(截图)→特色综述→结语。

**评委买账的 10 条写法**：
1. 背景从**行业痛点**切入（3个加粗痛点→我们解决），不直接堆技术
2. 需求分析**高度结构化**（角色拆分+用例图；算法需求 I/O 契约）
3. 技术选型=**组件+理由配对**（"用X做Y"），架构先给一句**设计理念**统领
4. **算法章是灵魂**：框架图→基座/方案选型（**对比+带数字**）→底层原理逐层（敢写到公式）→工程化（数据集/指标/后处理）。选型套路=「是什么→为何适合本任务→数据佐证」，证明**真懂非调包**
5. 用**数据与对比**说话（对标商用/SOTA/基线）
6. 功能模块讲**数据流转**（前端→后端→存储/算法→流式推回）+流程图，不堆界面
7. **诚实写"踩坑→解法"**——最显真实工作量与深度
8. 写**工程严谨细节**（隔离/鉴权/缓存/降级）体现成熟度
9. **图表密集**，几乎每功能配图
10. 特色综述用 **N 个加粗维度**收口 + 结语**回扣应用价值**

**我们的差异化发力点**：算法章主打 RAG 全链路（混合检索+重排+QueryRewrite）、多智能体 Orchestrator、数字人自然度/表情管理、**语音<5s 延迟优化**（埋点定位→生成吞吐瓶颈→四项优化→实测，天然符合范式④的"原理+数据+踩坑"）。踩坑素材直接从本进度日志取（SSE 伪流式 / MuseTalk OOM / 死脸 / 依赖地狱 / 客流冷加载尖峰）。

- [ ] **部署和使用手册**（参考 CLAUDE.md 云端维护章节扩写）

- [ ] **方案介绍 PPT**（对照文档第7章评分项覆盖表，每分都有对应实现）

- [ ] **演示视频**（≤7分钟）：建议叙事线——提问→多Agent分派→流式回复→数字人说话→管理后台实时大屏

---

## 最紧迫待办（按优先级）

> 核心链路（RAG / 数字人 / 形象管理 / 部署）已就绪。当前重心 = 交付材料 + 收尾。

1. **初赛交付材料**：总体设计文档定稿（窗口②）→ PPT → 演示视频（≤7min）；部署和使用手册。
2. **管理端数据补厚 + 写接口鉴权**（见上「活跃待办」两条）——评委查工程严谨性。
3. **灵山×故宫真机验证**：双景区切换的形象/口吻/主题区分度 + 故宫热切观感（无撕裂）。
4. **演示前体检**：AutoDL `preflight.sh` + 公网网关 URL 确认（token 会轮换）。

### 产品化（可选加分，赛后/有余力）

- [ ] **打包成 Android APK**（Capacitor 套壳现有手机网页，~1 天）：APK 是「壳客户端」，RAG/LLM 走云、数字人渲染留 GPU 服务器推流给 App（手机端不渲染）。
  - **顺带好处**：App 是安全本地源（`capacitor://`），**直接解决「手机 http 局域网 getUserMedia 禁麦」问题**，相机/麦克风免折腾 HTTPS。
  - 赛题最终形态要「小程序/H5」，APK 是合法加分项但非必须；**核心功能稳了再做**，别让打包拖延初赛交付。
  - 成本提醒：公开发布需常驻云 GPU 跑数字人；初赛演示用本地 4080 + 同 WiFi 即可。

## 迁移公告（2026-07-11）

- 用户要求把本机项目迁移到 Windows 后续可继续开发的分区，并保证 Claude Code / Codex 记忆可接上。
- 目标优先选 `AI_Local` 分区：Linux 挂载点 `/media/jiale/AI_Local`，目标目录 `/media/jiale/AI_Local/Digital_Person`。`990-PRO` 当前可用空间较少，只作为备选。
- 已完成整目录 `rsync` 迁移并校验：源/目标均约 7.4G，目录/文件/软链接数量一致，目标 `git status --short` 与源目录一致（99 条）。
- 本次必须复制完整工作区快照，而不是重新 clone：当前有大量未提交改动、未跟踪交付材料、`.env`、`.claude/settings.local.json`、`.mcp.json` 和 `CODEX_HANDOFF.md`。
- Windows/WSL 打开项目后先读：`CLAUDE.md`、`CODEX_HANDOFF.md`、`WINDOWS_MIGRATION_HANDOFF.md`、各子目录 `CLAUDE.md`。
- `.mcp.json` 里含 Linux 绝对路径和本机代理配置；Windows 原生使用 Claude Code 时要改成本机路径，WSL 使用时需在 WSL 内重装 node/uvx/Playwright 后调整。
- `.venv` 是 Linux 环境快照，迁移会保留，但 Windows 原生开发不应直接复用；建议用 Python 3.11 重新建环境。
