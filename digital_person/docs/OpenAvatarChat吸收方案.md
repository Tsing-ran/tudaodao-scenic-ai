# OpenAvatarChat 吸收方案

> 参照项目：[HumanAIGC-Engineering/OpenAvatarChat](https://github.com/HumanAIGC-Engineering/OpenAvatarChat)（阿里达摩院孵化，3.5k★）
> 目的：它和本项目是**同一架构形状**（ASR + LLM + TTS + Avatar + 可插拔），把它趟过的工程经验筛选吸收。
> 原则：**不整包搬**，只取"能落地、对中软杯评分有用"的部分。

## 逐模块对照

| 模块 | OpenAvatarChat | 本项目现状 | 差距/动作 |
|---|---|---|---|
| VAD | Silero-VAD，自动断句 | ASR 内置 `vad_filter`，但**前端要手动点停** | 补：前端录音自动断句 |
| ASR | SenseVoice / Qwen-Omni | faster-whisper small + **自研景区热词** | 我方更优，保持 |
| LLM | OpenAI 兼容 / Qwen-Omni | qwen-max + **RAG 知识库** | 我方更优（它无知识库），保持 |
| TTS | **CosyVoice** | edge-TTS（LiveTalking 内置，占位） | 换 CosyVoice，自然度↑ |
| Avatar | LiteAvatar / LAM / MuseTalk | MuseTalk | 加 LiteAvatar 备选 |
| 打断 | 手动 + 双工打断 | 桥接已做 `interrupt` 首句抢跑 | 已对齐 |
| 端到端 | i9+4090 **2.2s** | 4080 Laptop 待实测 | 作为对标基准写进 PPT |

---

## 四件事，按"性价比/风险"排序

### ① 模块化架构叙事（0 代码，立即）— 答辩弹药
OpenAvatarChat 的卖点是"ASR/LLM/TTS/Avatar 可插拔 + 2.2s 延迟"。本项目桥接层
（`bridge/server.py` 的 `VOICE_MAP`/`AVATAR_MAP`，RAG 可指本地/云端）本质同一思想。
**动作**：把这套"可插拔 + 对标 2.2s"写进总体设计文档 / PPT。
**价值**：直接命中评审对"架构先进性"的观感。零风险。

### ② 前端 VAD 自动断句（中等，体验+赛分高）
**对方怎么做**：Silero-VAD 监听音频流，检测到静音即判定一句话说完，自动提交。
**本项目落地**：游客端不该手动点"停止录音"。两种实现：
- 轻量方案：浏览器端用 `@ricky0123/vad-web`（JS 版 Silero）检测停顿 → 自动停录 → 传 `/asr`。改 `talk.html` / `test_mobile.html`，**后端零改动**。
- 重量方案：流式 ASR 边说边转。改造大，赛期不值。
**取轻量方案**。工作量 ~半天。风险低（纯前端）。
**价值**：交互自然度直接提升，是"语音问答"体验分。

### ③ TTS 换 CosyVoice（中高，命中"自然度"红线）
**对方怎么做**：CosyVoice（FunAudioLLM），音色自然、可克隆。
**本项目落地（已完成）**：早期 TTS 为 LiveTalking 内置 edge-TTS（占位）；现已切换为云端实时 Qwen-TTS（0 本地显存），并接入队友 CosyVoice 服务作备选（桥接 `VOICE_MAP` 按音色名映射 `tts.ref_file`）。
LiveTalking 原生支持 `--tts cosyvoice`，需：
1. 起一个 CosyVoice 服务（或用百炼 CosyVoice API，省显存）；
2. LiveTalking 启动参数切到 cosyvoice，桥接 `VOICE_MAP` 改成 CosyVoice 音色/参考音频。
**风险**：本地 CosyVoice 吃显存，与 MuseTalk 抢 4080 → **优先走百炼 CosyVoice API**（云端合成，0 本地显存，与"RAG 用 cloud 模式省显存"同思路）。
**价值**：赛题硬指标含"**口型同步 + 表情自然度**"，音色自然度是其中一环；且支持"克隆景区专属声音"=形象管理加分。工作量 ~1 天。

### ④ LiteAvatar 备选形象（高/存疑，加分项，最后做）
**对方怎么做**：LiteAvatar 是 2D 轻量 avatar，~4G 显存即可跑。
**本项目落地的现实**：LiteAvatar 是 OpenAvatarChat 自带模型，**LiveTalking 不原生支持**，
要把它接进 LiveTalking 是不小的集成工。
**赛期替代**：若只是为了演示"形象可配置/切换"，**再生成一个 MuseTalk avatar（古风男/女各一套）成本低得多**，
直接填进 `AVATAR_MAP` 即可，效果对赛一样。LiteAvatar 仅在"MuseTalk 显存/帧率真出问题"时才作为 plan C 评估。
**结论**：先不做集成；用"多套 MuseTalk avatar"满足形象切换演示，LiteAvatar 记为二期。

---

## 建议执行顺序
1. **①模块化叙事** —— 随手写进文档，0 成本。
2. **②前端 VAD** —— 纯前端，体验提升明显，先做。
3. **③CosyVoice（走百炼 API）** —— 自然度红线，次做。
4. **④LiteAvatar** —— 暂缓，用多套 MuseTalk avatar 替代其"形象切换"演示价值。
