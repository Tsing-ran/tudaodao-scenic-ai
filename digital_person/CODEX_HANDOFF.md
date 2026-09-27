# Codex 接手交接笔记

更新时间：2026-07-02  
范围：只读梳理 `CLAUDE.md`、各域 `CLAUDE.md`、核心后端、桥接、前端、部署与测试脚本后的接手记录。  
原则：本文件是 Codex 后续工作的本地知识沉淀，不替代 Claude 原有记忆。原 `CLAUDE.md` 仍是历史进度和分工公告板。

## 1. 项目定位

本项目是第十五届中国软件杯 A 组“景区导览服务 AI 数字人”作品。当前产品品牌为“途叨叨”，定位是通用智能景区导览与管理方案，不是只为灵山做的单景区 demo。

核心叙事：

- 游客端：扫码遇见随身 AI 数字人导游。
- 景区端：景区点击拥有可运营的数字员工。
- 技术底座：插拔式知识库、RAG 准确率承诺、实时数字人、主动导游、管理端运营闭环。

必须守住的 ground truth：

- 品牌：途叨叨。
- 导游名：去人名化，统一为“<景区简称>AI智能导览数字人”。
- 文本 LLM：事实问答用 `qwen-plus`，生成性意图用 `qwen-flash`。
- 多模态：`qwen3-vl-plus`。
- ASR：faster-whisper small，CPU int8。
- TTS：Qwen-TTS。
- 数字人主引擎：LiveTalking + Ditto。MuseTalk 仅历史回退。
- 准确率口径：97.1%，105 题，8 景区。
- 延迟口径：语音端到端约 4.7s，是我方工程目标；赛题硬红线只有准确率 >= 90%。
- 部署主线：AutoDL 单网关 + supervisor。阿里云 ECS `116.62.136.211` 已弃用，不应继续引用为当前方案。

## 2. 目录地图

- `backend/`：FastAPI 主后端，RAG、LLM、ASR、analytics、theme、tour、digital-human 等接口。
- `bridge/`：数字人桥接层，托管前端 dist，反代 `/rag`、`/live`、`/stream.flv`、`/hls`，串联 RAG 与 LiveTalking。
- `webapp/`：游客端 React + Vite + Tailwind v4 + shadcn/ui，生产由 bridge 托管。
- `miniprogram/`：微信小程序原生版本。
- `docs/`：交付文档、设计文档、部署手册、图表。
- `tests/`：独立脚本式测试，不是 pytest 套件。
- `deploy/autodl/`：AutoDL supervisor、一键起停与体检脚本。
- `livetalking_engine/`：本项目对上游 LiveTalking 的改造归档，极重要，因为实际 LiveTalking 改动未提交到上游 git。

关键文件：

- `backend/main.py`：FastAPI app 入口，router 汇总。
- `backend/rag/pipeline.py`：RAG 主链路，意图分派、缓存、检索、prompt、流式输出。
- `backend/rag/retriever.py`：EA-RAG 检索器。
- `backend/rag/scenic_types.py`：景区类型画像，通用但不同质的关键数据表。
- `backend/llm/client.py`：DashScope / local LLM 封装，修过流式阻塞问题。
- `backend/api/digital_human.py`：形象、音色、背景配置。
- `bridge/server.py`：桥接核心，容量池、barge-in、FAQ 成品视频、直播反代、前端托管。
- `webapp/src/hooks/useGuide.ts`：游客端主业务 hook，连接、提问、语音、拍照、接力、主动讲解都在这里。
- `webapp/src/App.tsx`：游客端主界面。
- `API_DOC.md`：接口契约，改接口必须同步。

## 3. 当前工作区状态

接手时 `git status` 显示大量未提交改动，覆盖后端、桥接、webapp、docs、测试报告和图片资源。必须假设这些都是用户或 Claude 之前的成果：

- 不回退。
- 不清理。
- 不用 `git checkout --` / `git reset --hard`。
- 如果要提交，先确认改动范围，避免把无关大文件或历史修改误打包。

根 `CLAUDE.md` 当前仍有“前端窗口启用中”记录。后续实际协作时，如果用户没有新指示，应避免随便改前端或启停服务；但用户明确让 Codex 接手后，可按用户最新任务执行。

## 4. 运行拓扑

本地开发 / 演示：

- RAG：`:8000`，建议 `DEPLOY_MODE=cloud`，避免本地 BGE/Reranker 占 GPU。
- Bridge：`:9000`，生产入口式托管前端与反代。
- LiveTalking：`:8010`，本地主数字人。
- SRS：`1935/1985/8080`。
- 浏览器正式入口：`http://localhost:9000/`。`talk.html` / `/legacy` 已弃用，只作回退。

AutoDL：

- RAG：`127.0.0.1:8000`。
- Bridge：`0.0.0.0:6006`，映射到公网 `:8443`。
- LiveTalking main：`:8010`，手机 16:9。
- LiveTalking portrait：`:8011`，大屏 9:16。
- SRS：`1935/1985/8080`。
- supervisor 管 6 个服务：`srs`、`rag`、`livetalking_main`、`livetalking_portrait`、`bridge`、`relay_hz`。

坑点：

- 本地端口和 AutoDL 端口不同：本地 bridge 是 `9000`，AutoDL bridge 是 `6006`。
- AutoDL 公网 token 会轮换，`API_DOC.md` 或脚本里的固定 URL 可能过期，演示前必须从控制台确认当前 URL。
- `preflight.sh` 里有固定杭州备用网关地址，也可能与当前部署状态不一致。
- 本机浏览器不要用局域网 IP，系统代理 clash 可能劫持局域网 IP 到 502；本机用 localhost，手机才用 `hostname -I` 的局域网 IP。

## 5. 后端与 RAG 要点

RAG 链路：

1. `/chat` 进 `backend/api/chat.py`。
2. `pipeline.answer` 或 `answer_stream` 分类意图。
3. 非闲聊走 query rewrite + retrieve。
4. 构造 prompt，注入景区名、导游名、上下文、意图指令、同行人格、situation、景区类型画像。
5. 调 `backend/llm/client.py`。
6. 提取 `[情绪:X]`，保存 conversations。

EA-RAG 三个机制：

- 实体锚定：结构化 chunk 内 `景点名称:` 提取实体，query 命中时加权。
- 自适应融合：数字/量词问题偏 BM25，长口语问题偏 dense。
- 置信度门控：本地 reranker top1 低于阈值返回空召回，触发兜底。

坑点：

- `settings.deploy_mode == "cloud"` 时不跑本地 reranker，门控不生效，只走融合与锚定。
- `qwen-turbo`、`qwen-vl-max` 等旧注释仍散落在部分代码和文档中，实际配置已迁移到 `qwen-flash` / `qwen3-vl-plus`，不要被旧注释带偏。
- `-latest` 模型名曾 403，配置中强调用稳定别名。
- 系统代理会影响 DashScope/HF/wttr 等调用，多个模块主动 `unset` 或 `trust_env=False`。
- RAG `answer_cache` 是进程内 LRU，知识库增删改目前只失效了实体缓存，没有明显清答案缓存；编辑知识库后旧问句可能短时间命中旧答案。
- `/kb/upload replace=True` 清 Chroma collection，但不会同步清 `uploaded_docs` 表，管理端文档列表可能残留旧记录。
- 改 SQLite 表结构必须走 `backend/db/database.py` 的 `_ensure_columns` 幂等迁移，不能手写一次性裸 ALTER。

## 6. Prompt 与个性化要点

`backend/llm/prompts.py` 的硬约束很重要：

- 必须先输出固定中文情绪标签 `[情绪:开心]` 等。
- 正文第一句必须短，15 字以内，方便数字人首句抢跑开口。
- 口播格式禁止 Markdown、编号清单、表格和代码块。
- 无资料要兜底，不要编。

`group_type` 与 `situation` 是正交维度：

- `group_type` 管同行关系：adult / family_kids / senior / couple。
- `situation` 管游客自身：age / pace / mobility / purpose / first_time。
- 全默认 situation 不应改变 prompt 和缓存键，这是测试里的 back-compat 红线。
- `hiker + senior/elder` 有体力轴裁决，安全稳妥优先。

景区类型画像：

- 数据在 `backend/rag/scenic_types.py`。
- 原则：类型差异只进数据，不写 if-else 业务分支。
- `persona` 注入所有意图，`reminders` 只注入 navigation/recommend，避免 QA prompt 膨胀。

## 7. 数字人桥接要点

`bridge/server.py` 是关键串联层。

请求层次：

- `/live/ask`：一次性 JSON。
- `/live/ask_stream`：SSE 字幕流，前端主用。
- `/live/say`：直接让数字人说给定文本，不走 RAG。
- `/live/avatar` GET：连接前解析当前景区默认真实 avatar。
- `/live/avatar` POST：热拔插切换直播形象，约 1s，不持久化配置。
- `/stream.flv` / `/hls/*`：反代 SRS。
- `/rag/*`：反代 RAG。
- `/`：托管 `webapp/dist`，不存在时回退旧 H5。

重要状态：

- `sessionid` 是 LiveTalking 会话 ID，RTMP 单路通常固定 `"0"`。
- `session_id` 是 RAG 业务会话 ID，和 `sessionid` 不是一回事。
- 前端 `SESSION_ID = '0'`。
- 传错 `sessionid` 可能造成 LiveTalking session not found、数字人不开口，甚至桥接池状态异常。

容量池与降级：

- `AVATAR_POOL_SIZE` 默认 1。
- main 屏幕占池，portrait 独立实例不占手机端共享池。
- LiveTalking 不可用、池满、驱动失败时降级为文字答复，保证有答案。
- `barge-in` 通过 `_ASK_GEN` 控制，同一 session 新问会打断旧问。

FAQ / Greeting 成品视频：

- Bridge 启动加载 `webapp/{dist,public}/faq/manifest.json`。
- 命中 FAQ 直接返回 `mode=clip`，前端播成品视频，0 GPU、0 LLM。
- Greeting clip 在前端读取 `/greeting/manifest.json`。

坑点：

- 热切形象只切当前直播，不写入景区默认；持久化要 `PUT /digital-human/config`。
- 形象解析有多级候选：`<base>__<scenic>__<aspect>`、灵山同形兜底、传统背景命名、base、默认。
- `api_doc()` 页面标题仍写“智游导览”，这是旧名残留，文档或界面统一时要修。

## 8. 数字人配置与资产

数字人配置接口在 `backend/api/digital_human.py`。

关键行为：

- `GET /digital-human/config?scenic_id=x`：若无显式配置，优先返回景区专属身份 `dh_<scenic>`，再回落 default，再内置默认。
- `PUT /digital-human/config`：只允许 ready 且非 coming_soon 的 avatar。
- `GET /digital-human/presets`：会根据本机 Ditto 目录真实文件标注 ready/coming_soon。
- AI 定制 `/digital-human/generate` 要本机有 Ditto 形象目录，适合 GPU 部署机，不适合纯云逻辑后端。

坑点：

- `_DITTO_DIR` 不存在时，ready 不强判，纯云环境仍可能返回专属身份，交给 bridge 兜底解析。
- 背景上传只是登记 pending，实际合成必须在有 LiveTalking 数据目录的机器上跑 `scripts/gen_avatar_background.py sync`。
- 自定义 preview 走 `PUBLIC_RAG_BASE`，默认值可能是旧公网 URL，部署迁移时要检查。

## 9. 前端要点

技术栈：

- React 19 + Vite + Tailwind v4 + shadcn/ui。
- 图标主用 Phosphor，emoji 字段已弃用。
- 字体：Geist + HarmonyOS Sans SC 自托管。
- 生产全部用相对路径，经 bridge 同源访问。
- Vite dev proxy 指向 `http://localhost:9000`，所以只跑 `npm run dev` 不足以完整联调，bridge 要先可用。

游客端主链路：

- `useGuide.connect()` 优先 WebRTC `/rtc/v1/play/`，AutoDL 无该端点时回退 HLS/FLV。
- iOS / Safari 走 HLS，安卓 / Chrome 走 FLV。
- `/live/ask_stream` 下发 open/sentence/done，前端按说话速率做卡拉 OK 字幕。
- 未连接时仍可文字提问，数字人只是增强项。
- `photo()` 调 `/rag/chat/image`，成功后再 `/live/say` 让数字人说出来。
- `toggleVoice()` 依赖浏览器麦克风权限，本地 http 在 iOS 上有权限坑，HTTPS 或 APK 壳更稳。

前端覆盖能力边界：

- UI 语言只有 4 种：中/英/日/韩。
- 后端 `LANG_NAMES` 支持更多语言。文档里“语言数”要区分 UI 语言和后端 `lang` 参数能力。
- 前端地图路线 `SCENIC_ROUTES` 目前只有灵山有真高德 POI 路线；其他景区“跟我游”回退清单页。
- 实时 POI 客流也是灵山最完整；其他景区多为景点级或无数据。

设计/实现坑点：

- 不要硬编码景区名、导游名、主题色，主题从 `/scenic/theme` 动态取。
- `object-cover` 适配 16:9 上景底板；早期竖版流 canvas 模糊边方案已不应随意恢复。
- `index.html` 必须 no-cache，否则手机可能长期加载旧 bundle。
- 地理定位：浏览器返回 WGS-84，前端转 GCJ-02 与高德 POI 比较。
- iOS 定位调用必须紧贴用户手势，不能先 await 异步脚本。

## 10. 数据分析与主动导游

analytics 数据源分两类：

- `conversations`：服务端自动落库，对话、情绪、context_used。
- `events`：游客端主动埋点，画像、功能打开、推荐曝光点击、rating 等。

管理端空壳风险来自 `CLAUDE.md` 活跃待办：

- `hot-topics` 是 n-gram 碎片，应优先用 `/analytics/topic-intents`。
- GPS 兜底回复可能污染 `user_message`，影响热点统计。
- `kb/faq` 与 `kb/docs` 可能为空，需要播种 FAQ 和登记已 ingest 文档。
- `analytics/profile` interests 稀疏。
- `knowledge-gaps` 偏薄。

主动导游能力：

- `trip/today`：天气、时段、客流建议。
- `tour/routes` / `tour/facilities`：路线与设施。
- `tour/nearby`：后端备用最近点，前端实际主要用 routeData。
- `analytics/crowd`：灵山 POI 级模型，含演出聚集、天气、趋势。
- `recommend`：画像 + 兴趣 + situation + 环境 + 客流，生成 3 张推荐卡。

边界：

- 灵山最完整；黄山/故宫等有类型画像和经典路线，但非所有 POI/客流/地图能力都等价。
- 文档中不能把灵山级细粒度能力无条件写成“所有景区均已同等落地”。

## 11. 多模态与拍照

两个多模态链路：

- `/chat/image`：开放拍照问答。默认两段式：VL 定位地标，再把位置交 RAG 做接地讲解与指路。
- `/checkin`：闭集打卡核验。给路线候选和视觉特征，VL 只在候选里选或 none，再融合 GPS 软门。

坑点：

- `backend/llm/multimodal.py` 顶部注释仍写 qwen-vl-max，实际配置是 `settings.vl_model = qwen3-vl-plus`。
- `/chat/image` 识别到位置后构造 nav_query 走 RAG，因此准确性依赖该地标在知识库中可检索。
- `/checkin` 目前特征表只给了灵山，其他景区候选缺具体视觉特征，准确率会弱。

## 12. 部署坑点

AutoDL：

- 数据盘 `/root/autodl-tmp` 放代码、大模型和 LiveTalking。
- AutoDL 只对外映射 6006/6008，bridge 监听 6006。
- supervisor 不随开机自动拉起，必须显式 `dp_up.sh`，演示结束 `dp_down.sh` 释放 GPU。
- LiveTalking 两路出流大约 85s，刚启动时 preflight 双流不足可能是正常。

Ditto / LiveTalking：

- 实时 Ditto 必须 TRT online cfg，PyTorch cfg 是离线版，不能实时流式。
- TRT 8.6.1 没有 Python 3.12 bindings，LiveTalking 需单独 Python 3.10 conda env。
- TRT 需要 cuDNN8，通过 `LD_LIBRARY_PATH` 注入，不能和 torch cuDNN9 混装。
- `rtmp_streaming` 是 Python 版本相关 C++ 绑定，换 Python 要重编。
- HF 的 Ditto 引擎包曾缺 `motion_extractor_fp32.engine`，需要从已跑通本地补传。
- QwenTTS 空闲超时可能静音，验证音频必须抓流做 `ffmpeg volumedetect`，不能只看日志。

网络 / 代理：

- AutoDL `source /etc/network_turbo` 可加速 GitHub/HF，但可能拖慢 pip/nvidia 源，装包前需按情况 unset 代理。
- 多处 httpx 使用 `trust_env=False`，这是为了绕开本地 SOCKS 代理。

## 13. 测试与验证

测试都是独立脚本，常见跑法：

- 纯逻辑，适合快速回归：
  - `.venv/bin/python tests/test_scenic_types.py`
  - `.venv/bin/python tests/test_situation.py`
  - `.venv/bin/python tests/test_gugong_avatar.py`
- 需要模型/API/知识库，谨慎跑：
  - `.venv/bin/python tests/test_accuracy.py lingshan`
  - `.venv/bin/python tests/eval_kb.py`
  - `.venv/bin/python tests/test_rag.py`
- 前端：
  - `export PATH=$HOME/.local/node/bin:$PATH`
  - `cd webapp && npx tsc -b --noEmit`
  - `cd webapp && npm run build`
- AutoDL 演示前：
  - `bash /root/autodl-tmp/preflight.sh`
  - `bash /root/autodl-tmp/preflight.sh --audio`

注意：

- 准确率测试会调用 DashScope/嵌入/知识库，不应在没准备好 key、网络和成本意识时随手跑。
- 改 RAG、prompt、检索参数前后，至少跑相关准确率抽测。
- 改前端必须 tsc + build 双过。
- 改语音/TTS/LiveTalking，必须做可听音频验证。

## 14. 当前高优先待办

来自根记忆和代码阅读的优先级：

1. 初赛交付材料收尾：总体设计文档、PPT、演示视频、部署使用手册。
2. 管理端写接口鉴权：`X-Admin-Key` + `.env ADMIN_API_KEY`，游客端只读接口不动。
3. 管理端数据补厚：FAQ/docs 播种、topic-intents 替换 hot-topics、清污染数据、profile/knowledge-gaps 补厚。
4. 知识库管理一致性：编辑/上传/replace 时同步清答案缓存、修 `uploaded_docs` 与 Chroma 状态不一致。
5. 灵山/故宫真机验证：形象、口吻、主题、热切观感。
6. 演示前 AutoDL 体检：当前公网 URL、双路推流、音频 dB、GPU 进程身份。

## 15. 后续动手规则

通用：

- 不改动无关文件。
- 不回退未提交改动。
- 不用破坏性 git 命令。
- 接口变化必须同步 `API_DOC.md`。
- 文档事实以 ground truth 为准，不引用旧 ECS、旧品牌、旧模型名。

后端：

- `.venv/bin/python` 为主。
- 装包用 uv，注意代理。
- SQLite 迁移只走 `_ensure_columns`。
- RAG 改动考虑准确率、缓存键兼容和答案缓存失效。

前端：

- 不硬编码景区和导游名。
- Phosphor 图标，不用 emoji 当图标。
- 改完 tsc + build。
- dev 需要 bridge 同源代理支持。

部署/GPU：

- GPU 任务串行。
- 动 GPU 前先看进程 cmdline，避免误杀用户训练。
- LiveTalking / ComfyUI / 训练不能随意并行抢显存。

## 16. Windows / AI_Local 迁移快照（2026-07-11）

用户要把当前项目迁移到 Windows 后续开发盘，并保证 Claude Code / Codex 能无缝接上进度。

已确认：

- 源目录：`/home/jiale/Desktop/Digital_Person`。
- 优先目标：`/media/jiale/AI_Local/Digital_Person`。
- `AI_Local` 为 NTFS 分区，挂载后约 51G 可用；`990-PRO` 只剩约 16G，可用但不宽裕。
- 源目录约 7.4G，其中 `.venv` 约 6.1G，`.git` 约 282M。
- 当前工作区有大量未提交和未跟踪文件，迁移必须用整目录复制，不能只依赖 git。
- Claude 记忆入口存在：`CLAUDE.md`、`backend/CLAUDE.md`、`docs/CLAUDE.md`、`webapp/CLAUDE.md`、`.claude/settings.local.json`。
- Codex 记忆入口存在：`CODEX_HANDOFF.md`、本节、`WINDOWS_MIGRATION_HANDOFF.md`。
- `.codex/` 和 `.agents/` 当前为空目录，但迁移时仍保留。

迁移后接手规则：

- Windows / WSL 上打开项目根目录后，先读 `WINDOWS_MIGRATION_HANDOFF.md`。
- 立即跑 `git status --short`，确认脏工作区和未跟踪交付材料没有丢。
- `.mcp.json` 中有 Linux 绝对路径和本机代理配置；Windows 原生 Claude Code 需要改路径，WSL 则按 WSL 工具链重建。
- `.venv` 会作为快照保留，但不作为 Windows 原生环境复用。新环境按 Python 3.11 + `requirements.txt` 重建。
- 旧 ECS `116.62.136.211` 在现有记忆中已标记弃用；若后续用户重新启用 ECS，要先更新部署真相，再改文档和脚本。

执行结果：

- 2026-07-11 已用 `rsync -aH --no-owner --no-group --modify-window=1` 完成迁移。
- 目标目录 `/media/jiale/AI_Local/Digital_Person`。
- 源/目标体积均约 7.4G；文件结构计数一致：6650 个目录、69369 个普通文件、31 个软链接。
- 源/目标 `git status --short` 均为 99 条，脏工作区状态一致。
- dry-run 仅剩 `.agents/`、`.codex/` 空目录的时间/权限元数据差异，内容无缺失。
