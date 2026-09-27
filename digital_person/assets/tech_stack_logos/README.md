# 技术栈 LOGO 素材包（途叨叨 · 景区 AI 数字人）

绘制技术栈流程图用。SVG = 品牌色矢量（可无限放大，首选）；PNG = GitHub 组织头像/favicon（研究项目/无官方矢量 logo 者的兜底标识）。总览见 `_总览预览.png`。

## 清单（按角色分类）

### 01 后端框架
| 技术 | 在系统中的角色 | 文件 |
|---|---|---|
| Python | 后端主语言 | `Python.svg` |
| FastAPI | Web 框架（RAG :8000 / 桥接 :6006 / 管理端 :6008） | `FastAPI.svg` |
| Pydantic | 数据模型/校验 | `Pydantic.svg` |
| Uvicorn | ASGI 服务器 | `Uvicorn-encode.png`（encode 组织头像） |
| SQLite | 会话/分析存储 | `SQLite.svg` |
| ChromaDB | 向量数据库（多景区 collection 隔离） | `ChromaDB.png` |
| Pandas | 行为数据/BI 分析 | `Pandas.svg` |
| NumPy | 数值底座 | `NumPy.svg` |

### 02 LLM 与 RAG
| 技术 | 角色 | 文件 |
|---|---|---|
| 通义千问 Qwen / DashScope | 文本 LLM（qwen-plus/flash）+ 多模态（qwen3-vl-plus）+ Qwen-TTS | `通义千问Qwen-DashScope.svg` |
| 阿里云百炼 | DashScope 模型平台 | `阿里云百炼-DashScope.svg` |
| BGE-M3 / BGE-reranker（FlagEmbedding，托管 HuggingFace） | 稠密嵌入 + 重排序 | `HuggingFace-BGE-FlagEmbedding.svg` |
| ModelScope 魔搭 | 模型来源（备） | `ModelScope魔搭.png` |
| OpenAI Whisper（faster-whisper） | 语音识别 ASR | `OpenAI-Whisper.png` |
| LangChain | RAG 编排（早期/部分） | `LangChain.svg` |
| BM25（rank_bm25） | 稀疏检索（混合检索一路） | 无 logo → **文字标** |

### 03 数字人与媒体
| 技术 | 角色 | 文件 |
|---|---|---|
| Ditto | 实时全脸驱动引擎（直播主引擎） | `Ditto-talkinghead.png`（antgroup 头像） |
| LiveTalking | 数字人推流框架 | `LiveTalking.png`（作者 lipku 头像） |
| SRS | 流媒体服务器（RTMP→FLV/HLS） | `SRS流媒体.png`（ossrs 头像） |
| FFmpeg | 媒体处理/中继 | `FFmpeg.svg` |
| WebRTC | 低延迟传输 | `WebRTC.svg` |
| PyTorch | 深度学习框架 | `PyTorch.svg` |
| NVIDIA TensorRT / CUDA | GPU 推理加速（4090D/4080） | `NVIDIA-TensorRT-CUDA.svg` |
| ComfyUI | 离线形象生成工作流 | `ComfyUI.png` |
| 通义万相 Wanxiang | 文生图/图生视频（形象素材） | 用 `通义千问Qwen-DashScope.svg` 或阿里云代 → 或**文字标** |

### 04 前端
| 技术 | 角色 | 文件 |
|---|---|---|
| React | 手机游客端（webapp） | `React.svg` |
| Vue | 游客大屏 Kiosk + 管理端大屏 | `Vue.svg` |
| Vite | 构建工具 | `Vite.svg` |
| TypeScript | 前端语言 | `TypeScript.svg` |
| Tailwind CSS | 样式 | `TailwindCSS.svg` |
| shadcn/ui | 组件库 | `shadcnui.svg` |
| Radix UI | 无样式组件原语 | `RadixUI.svg` |
| Phosphor Icons | 图标体系 | `PhosphorIcons.svg` |
| Apache ECharts | 数据大屏图表 | `ApacheECharts.svg` |
| 高德地图 AMap | 跟我游地图/客流 | `高德地图AMap.png`（favicon，低清，建议替成官方矢量） |
| Capacitor | 安卓 APK 套壳 | `Capacitor.svg` |
| HarmonyOS Sans（华为） | 中文字体 | `HarmonyOS字体.svg`（华为标） |

### 05 部署运维
| 技术 | 角色 | 文件 |
|---|---|---|
| Nginx | 杭州公网网关/反代 | `Nginx.svg` |
| Docker | SRS 容器 | `Docker.svg` |
| Git / GitHub | 版本管理 | `Git.svg` / `GitHub.svg` |
| Ubuntu / Linux | 服务器系统 | `Ubuntu-Linux.svg` |
| AutoDL | GPU 云主机（4090D 公网部署） | 无 logo → **文字标** |
| Supervisor | 进程守护 | 无 logo → **文字标** |

## 建议的系统数据流（画流程图骨架参考）

```
游客端 React/Vue + Vite + Tailwind + ECharts + AMap + Capacitor
   │  HTTPS
   ▼
Nginx(杭州网关) / AutoDL 网关
   │
   ▼
FastAPI 桥接 ──► RAG(FastAPI/Pydantic)
                   │  混合检索
                   ├─ BGE-M3 嵌入 + BGE-reranker 重排(FlagEmbedding)
                   ├─ BM25 稀疏检索
                   ├─ ChromaDB 向量库
                   └─► Qwen/DashScope 生成 ──► 答案
   语音: faster-whisper(ASR) │ Qwen-TTS(合成)
   │
   ▼ 数字人
桥接 ──► LiveTalking + Ditto (PyTorch/TensorRT/CUDA·NVIDIA)
            └─► SRS(FFmpeg) ──► WebRTC/FLV/HLS ──► 流回前端

数据: SQLite(会话/分析) + Pandas(行为/BI)
离线生成: ComfyUI + 通义万相 + InstantID
部署: Docker · Supervisor · AutoDL · Nginx · Git/GitHub · Ubuntu
```

## 需文字标（无标准 logo）
BM25 / 通义万相（可用阿里云标代）/ AutoDL / Supervisor / InstantID

> 低清兜底项（建议有空换官方矢量）：高德 AMap（favicon 64px）。研究项目用的是 GitHub 组织头像而非官方 logo（Ditto/LiveTalking/SRS/ChromaDB/ComfyUI/Uvicorn），答辩够用。
