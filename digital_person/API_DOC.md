# 景区导览 AI 数字人 — 后端接口文档

**公网网关（AutoDL，下文 `{BASE}` 即指它）**：`https://u891802-x4xd-7f8146e7.bjb2.seetacloud.com:8443`

> **调用约定**（前端队友看这里）：
> - **RAG 后端接口**（chat / analytics / kb / theme / tour / digital-human …）：网关加 `/rag` 前缀 → `{BASE}/rag/<路径>`。例：`{BASE}/rag/chat`、`{BASE}/rag/analytics/bi/overview`。
> - **桥接接口**（数字人直播与驱动 `/live/*`、`/stream*`、`/hls/*`）：直接在网关下 → `{BASE}/live/ask`、`{BASE}/stream.flv`。
> - 全部 CORS 全开,`fetch` 直接用。本文档在线版:`{BASE}/api-doc`（永远最新）。
> - 本地开发直连 RAG 用 `http://localhost:8000`（无 `/rag` 前缀）。
>
> ⚠️ 阿里云 ECS（116.62.136.211）**已弃用**,文档里如还有该 IP 即为旧示例,一律以 `{BASE}` 为准。

**健康检查**：`GET {BASE}/rag/health` → `{"status": "ok"}`；`GET {BASE}/live/health`（含数字人直播状态）

---

## 目录

- [1. 对话接口（核心）](#1-对话接口核心)
  - [1.1 文本对话（同步）](#11-文本对话同步)
  - [1.2 文本对话（流式 SSE）](#12-文本对话流式-sse)
  - [1.3 图片对话（多模态）](#13-图片对话多模态)
  - [1.4 多语言问答](#14-多语言问答)
  - [1.5 同行人格切换](#15-同行人格切换)
- [2. 知识库管理](#2-知识库管理)
- [3. 数据分析（管理后台用）](#3-数据分析管理后台用)
  - [3.1–3.7 大屏/词云/情感/对话/报告/盲区/预警](#31-数据大屏核心数据)
  - [3.8 客流热度感知](#38-客流热度感知)
  - [3.9 游客行为事件上报 🆕](#39-游客行为事件上报-)
  - [3.10 客群画像 🆕](#310-客群画像-)
  - [3.11 功能使用率与满意度 🆕](#311-功能使用率与满意度-)
  - [3.12 文旅 BI 分析（人口/消费/景点画像）🆕](#312-文旅-bi-分析人口消费景点画像)
- [4. 数字人形象配置](#4-数字人形象配置)
- [5. 景区主题（管理端可配置换肤）](#5-景区主题管理端可配置换肤)
- [6. 数字人直播与驱动（桥接层·手机端16:9 + 大屏竖版9:16）🆕](#6-数字人直播与驱动桥接层)
- [附录：数据类型说明](#附录数据类型说明)

> 游客端导览接口（迎宾/今日卡/跟我游/设施/定位/游记）见 [`docs/数据采集与管理端对接.md`](docs/数据采集与管理端对接.md) 与各 `backend/api/{trip,tour}.py`；本文档聚焦核心对话 + 管理后台数据接口。

---

## 1. 对话接口（核心）

### 1.1 文本对话（同步）

> **队友 A**：适合调试用，生产环境推荐用流式版本。  
> **队友 B**：非流式场景（如文字展示）可用此接口。

```
POST /chat
Content-Type: application/json
```

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `message` | string | ✅ | 游客问题 |
| `scenic_id` | string | ✅ | 景区 ID，见下方枚举 |
| `session_id` | string | | 会话 ID，用于区分用户，默认 `"anonymous"` |
| `history` | array | | 历史对话，格式见下，默认空 |
| `fast` | bool | | `true` 用 qwen-turbo（延迟减半，适合简单问答），默认 `false` |
| `lang` | string | | 回答语言，`auto`（跟随提问语言）或 `en`/`ja`/`ko`… 强制指定，默认 `auto`，详见 1.4 节 |
| `group_type` | string | | 同行关系，切换叙事人格，默认 `adult`，详见 1.5 节 |
| `situation` | object\|null | | 游客自身情况标签（与 `group_type` 正交），按非默认值调讲解侧重，详见 1.6 节 |
| `interests` | string[] | | 静态兴趣（开场快选，`history`/`nature`/`photo`/`food`/`culture`），默认 `[]`。**仅入游中画像，不直接进 prompt**；qa 事实问答链路零接触（守准确率），详见 1.7 节 |
| `stream` | bool | | 必须为 `false`（或不填），流式用 1.2 节 |

**景区 ID 枚举**

| `scenic_id` | 景区 |
|---|---|
| `lingshan` | 灵山胜境 |
| `nihuawan` | 拈花湾禅意小镇 |
| `xihu` | 杭州西湖 |
| `huangshan` | 安徽黄山 |
| `gugong` | 北京故宫博物院 |

**`history` 格式**（最近 N 轮，用于多轮对话）

```json
[
  {"role": "user",      "content": "灵山大佛有多高"},
  {"role": "assistant", "content": "灵山大佛高88米……"}
]
```

**请求示例**

```bash
curl -X POST {BASE}/rag/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user_001",
    "message": "灵山大佛有多高？",
    "scenic_id": "lingshan"
  }'
```

**响应体**

```json
{
  "reply": "灵山大佛通高88米，相当于30层楼那么高！它是世界最高的青铜坐佛……",
  "emotion": "excited",
  "sources": ["灵山胜境 景点结构化数据集"],
  "context_used": true,
  "intent": "qa",
  "from_cache": false
}
```

| 字段 | 说明 |
|---|---|
| `reply` | 干净的回复正文（已去除内部标记） |
| `emotion` | 情绪键，见[情绪枚举](#情绪-emotion-枚举) |
| `sources` | 命中的知识库文档名（用于调试） |
| `context_used` | 是否检索到相关知识库内容 |
| `intent` | 意图分派结果，见[意图枚举](#意图-intent-枚举)（Orchestrator 判定） |
| `from_cache` | 是否命中 LRU 缓存（<5ms 返回） |

---

### 1.2 文本对话（流式 SSE）

> **队友 A（重点）**：这是驱动数字人的主接口。  
> 第一个事件是 `intent`（意图，LLM 调用前即下发），紧接着 `emotion`（在 LLM 输出第一个字前下发），数字人可以**立刻**设置表情。  
> `sentence` 事件每完成一个自然句就下发一次，**收到即可送 TTS**，无需等待全文。

```
POST /chat
Content-Type: application/json
```

请求体与同步版本相同，**额外设置** `"stream": true`。

**响应格式**：SSE（Server-Sent Events），`Content-Type: text/event-stream`

事件流结构：

```
event: intent
data: {"type":"intent","value":"qa","label":"知识问答"}

event: emotion
data: {"type":"emotion","value":"excited"}

event: sentence
data: {"type":"sentence","text":"哇，灵山大佛可真是壮观呢！","index":0}

event: sentence
data: {"type":"sentence","text":"它通高88米，相当于30层楼那么高！","index":1}

event: sentence
data: {"type":"sentence","text":"是世界最高的青铜坐佛之一哦！","index":2}

event: end
data: {"type":"end","full_text":"[情绪:兴奋]\n\n哇，灵山大佛……"}
```

**事件类型说明**

| `event` | 数据字段 | 时机 | 用途 |
|---|---|---|---|
| `intent` | `value: string`，`label: string` | **最先到达**，LLM 调用前 | 展示当前意图（可选，可忽略） |
| `emotion` | `value: string` | LLM 输出第一个 token 后 | 设置数字人面部表情 |
| `sentence` | `text: string`，`index: number` | 每完成一个自然句 | 送 TTS 合成语音 |
| `end` | `full_text: string` | 全部完成 | 关闭连接，记录日志 |

> 事件顺序：**intent → emotion → sentence… → end**。`intent` 为新增事件，老客户端忽略即可，向后兼容。

**JavaScript 接入示例（队友 A / B 均适用）**

> ⚠️ 因为是 POST 请求，不能用浏览器原生的 `EventSource`，需要用 `fetch` + `ReadableStream`。

```javascript
async function chatStream(message, scenicId, sessionId, onEmotion, onSentence, onEnd) {
  const response = await fetch('{BASE}/rag/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message: message,
      scenic_id: scenicId,
      stream: true,
    }),
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // 保留未完成的行

    let currentEvent = '';
    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        if (currentEvent === 'intent')   onIntent?.(data.label);    // 可选，展示当前意图
        if (currentEvent === 'emotion')  onEmotion(data.value);
        if (currentEvent === 'sentence') onSentence(data.text, data.index);
        if (currentEvent === 'end')      onEnd(data.full_text);
        currentEvent = '';
      }
    }
  }
}

// 使用示例
chatStream(
  '灵山大佛有多高？',
  'lingshan',
  'user_001',
  (emotion)        => setDigitalPersonExpression(emotion),  // 立刻设置表情
  (text, index)    => sendToTTS(text),                      // 逐句送 TTS
  (fullText)       => console.log('对话结束'),
);
```

**Python 接入示例（队友 A 后端集成）**

```python
import httpx, json

def stream_chat(message: str, scenic_id: str, session_id: str):
    with httpx.stream("POST", "{BASE}/rag/chat",
                      json={"message": message, "scenic_id": scenic_id,
                            "session_id": session_id, "stream": True}) as r:
        current_event = ""
        for line in r.iter_lines():
            if line.startswith("event: "):
                current_event = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                if current_event == "emotion":
                    print(f"[情绪] {data['value']}")          # → 数字人表情
                elif current_event == "sentence":
                    print(f"[第{data['index']}句] {data['text']}")  # → TTS
                elif current_event == "end":
                    break
```

---

### 1.3 图片对话（多模态）

> 满足赛题"至少使用 1 个多模态大模型"的硬性要求。  
> 使用 `qwen-vl-max-latest` 模型，支持游客上传景点照片提问。

```
POST /chat/image
Content-Type: application/json
```

**请求体**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `image_b64` | string | ✅ | 图片的 Base64 编码（不含 `data:image/...` 前缀） |
| `question` | string | | 对图片的提问，默认 `"请介绍一下图片里的内容"` |
| `scenic_id` | string | | 景区 ID，用于人格设定，默认 `"lingshan"` |
| `session_id` | string | | 会话 ID，默认 `"anonymous"` |
| `image_format` | string | | `jpeg` / `png` / `webp`，默认 `"jpeg"` |

**请求示例**

```bash
# 先把图片转 base64
IMAGE_B64=$(base64 -w 0 photo.jpg)

curl -X POST {BASE}/rag/chat/image \
  -H "Content-Type: application/json" \
  -d "{
    \"session_id\": \"user_001\",
    \"scenic_id\": \"lingshan\",
    \"image_b64\": \"$IMAGE_B64\",
    \"question\": \"这是什么建筑？有什么历史？\"
  }"
```

**JavaScript 示例**

```javascript
async function chatWithImage(file, question, scenicId) {
  // File → Base64
  const base64 = await new Promise(resolve => {
    const reader = new FileReader();
    reader.onload = e => resolve(e.target.result.split(',')[1]); // 去掉 data:...前缀
    reader.readAsDataURL(file);
  });

  const resp = await fetch('{BASE}/rag/chat/image', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: 'user_001',
      scenic_id: scenicId,
      image_b64: base64,
      image_format: file.type.includes('png') ? 'png' : 'jpeg',
      question: question,
    }),
  });
  return await resp.json(); // { reply, emotion, model_used }
}
```

**响应体**

```json
{
  "reply": "这是灵山梵宫，是一座融合了多种宗教艺术风格的大型佛教文化建筑……",
  "emotion": "excited",
  "model_used": "qwen-vl-max-latest"
}
```

---

### 1.4 拍照打卡核验（闭集多模态）

> 「跟我游」地图路线的拍照打卡用。**不做开放识别**（易幻觉），而是给 VL 路线候选景点 + 各自标志性特征，
> 做**闭集核验**并强制结构化输出 evidence；可选 GPS（GCJ-02，与景点坐标同基准）做位置软门；
> 融合出决策 + 可信理由。准确率高、理由可复核。

```
POST /checkin
```

**请求体**

| 字段 | 类型 | 说明 |
|---|---|---|
| `scenic_id` | string | 景区 id（默认 lingshan） |
| `image_b64` | string | base64 图片（必填） |
| `image_format` | string | jpeg/png/webp（默认 jpeg） |
| `target_id` | string? | 游客想打卡的当前站 id |
| `candidates` | array | 路线候选站 `[{id,name,lng?,lat?}]`（坐标用于位置佐证） |
| `gps` | [number,number]? | `[lng,lat]` GCJ-02（AMap 定位）；不传则纯视觉+路线，演示/室内友好 |

**响应体**

```json
{
  "decision": "confirmed | wrong_stop | uncertain",
  "matched_id": "dafo",
  "matched_name": "灵山大佛",
  "confidence": 0.98,
  "evidence": ["巨大的青铜立佛，右手施无畏印、左手与愿印，立于莲花座之上"],
  "distance_m": null,
  "reason": "到啦，确认你在「灵山大佛」——我认出了……，打卡成功！",
  "alt_id": null
}
```

- `decision`：`confirmed`（命中目标站→直接打卡）/`wrong_stop`（认出的是别的站→建议调序）/`uncertain`（没把握→提示再拍）。
- `evidence`：VL 在照片里真实看到的具体特征（可人工复核、防编造）。
- 决策阈值：默认 0.7；有近距 GPS 佐证（≤120m）放宽到 0.6；GPS 近(≤80m)加信、远(≥300m)减信。

---

### 1.4 多语言问答

> 服务外籍游客。通过 `/chat`（同步或流式）的 `lang` 参数控制回答语言，接口其余字段不变。

**两种模式**

| `lang` 取值 | 行为 | 适用场景 |
|---|---|---|
| `auto`（默认） | 自动跟随游客提问的语言（英文问 → 英文答） | 外宾直接用母语提问 |
| `en` / `ja` / `ko` / `fr` / `de` / `es` / `ru` / `zh` | 无论提问语言，强制用指定语言回答 | 前端语言切换按钮 |

**请求示例**

```bash
# 英文提问，自动英文作答
curl -X POST {BASE}/rag/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"How tall is the Grand Buddha?","scenic_id":"lingshan"}'

# 中文提问，强制英文作答
curl -X POST {BASE}/rag/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"灵山大佛多高","scenic_id":"lingshan","lang":"en"}'
```

> **队友 A 注意**：`emotion` 事件值始终是固定的英文键（`happy`/`excited`…），不随回答语言变化，数字人表情控制逻辑无需改动。

---

### 1.5 同行人格切换

> 情境感知能力：同一段讲解，讲给带娃家庭、老人、情侣方式截然不同。通过 `/chat` 的 `group_type` 参数切换叙事人格，接口其余字段不变。

**取值**

| `group_type` | 同行关系 | 叙事风格 |
|---|---|---|
| `adult`（默认） | 通用成人 | 标准热情导游 |
| `family_kids` | 亲子家庭 | 讲故事、互动提问（“小朋友猜猜看～”）、提示亲子设施 |
| `senior` | 老年长辈 | 放慢节奏、强调无障碍/休息点、避免推荐爬山久站 |
| `couple` | 情侣出游 | 浪漫视角、推荐合影机位与祈福点 |

**请求示例**

```bash
# 亲子家庭模式
curl -X POST {BASE}/rag/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"灵山有什么好玩的","scenic_id":"lingshan","group_type":"family_kids"}'
```

> **队友 B**：可在游客端开场用一次性选择（"和谁一起来？"）设置 `group_type`，后续请求带上即可。
> `group_type` 与 `lang`、`fast`、`stream` 可任意组合。

---

### 1.6 自身情况标签 `situation`（🆕 2026-06-21）

> 与 `group_type`（"和谁来"）**正交**的第二维度：游客**自身**怎样。开场多步向导收集，按**非默认值**调讲解侧重（无障碍只推无台阶路线、祈福重礼仪、半天给精华…）。`/chat`、`/chat`(stream)、`/recommend`、`/live/ask`、`/live/ask_stream` 均接受。

**`situation` 对象字段**（全部可选，缺省=中性默认值）

| 字段 | 取值（**默认**加粗） | 含义 |
|---|---|---|
| `age` | `teen` / **`youth`** / `middle` / `elder` | 年龄段 |
| `pace` | `half` / **`day`** / `deep` | 游览节奏（半天精华 / 一整天 / 深度慢游） |
| `mobility` | `stroller` / `wheelchair` / **`normal`** / `hiker` | 出行方式（婴儿车 / 无障碍 / 普通 / 徒步） |
| `purpose` | `photo` / `kids_fun` / `pray` / **`relax`** / `study` | 此行目的 |
| `first_time` | **`first`** / `return` | 是否初次到访 |

**关键语义（back-compat 保证）**：`situation` 为 `null`、缺省、或**全为默认值**时，后端行为与不带该字段**逐字节一致**——系统 prompt 不变、问答缓存键不变 → **准确率零影响、缓存零失效**。只有**非默认值**才注入"因人而异"讲解指令并进入独立缓存键（不同情境不串答）。

**请求示例**

```bash
# 需无障碍 + 祈福参拜
curl -X POST {BASE}/rag/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"帮我安排今天怎么逛","scenic_id":"lingshan",
       "situation":{"mobility":"wheelchair","purpose":"pray"}}'
```

> **前端**：游客端开场向导一次性收集 5 维，存 localStorage，之后每次 `/live/ask*`、`/recommend` 自动带上。可与 `group_type`、`lang`、`fast`、`stream` 任意组合。

### 1.7 游中画像（🆕 2026-07-13）

> **立意**：真人导游靠头十分钟"察言观色"认人。系统从对话在线积累每个 `session_id` 的**兴趣 / 关心点 / 问过的景点 / 意图分布**，让**推荐与路线**"懂他"——上午问过素斋，下午推荐路线就自然带一句"记得您想尝素斋"。**匿名 session 级、48h 惰性自清、人走画像消**（不采 PII）。

**怎么建**：`/chat`、`/live/ask*` 每轮问答后端自动记一笔（规则扫兴趣关键词 + 匹配本景区真实站名 + intent 计数 + `interests` 静态兴趣并入）。无需前端额外调用。`session_id` 为 `anonymous`/`0`/空/`s_anon`（匿名或大屏共享通道）时**不建画像**（避免多人串扰）。

**怎么用（红线）**：画像**只注入 `navigation` / `recommend` 意图**与推荐卡，**绝不进 `qa` 事实问答链路**——qa 的 system prompt 与缓存键逐字节不变，**准确率零影响**。画像构建失败一律静默降级为"无画像"，不影响主链路。

**前端要点**：`/live/ask*`、`/recommend` 需带**稳定的业务 `session_id`**（webapp 用 per-tab 的 `lingjing.sid`，与埋点 events 同源），画像才能跨"问素斋"与"求推荐"两次调用累积。大屏 kiosk 用固定通道、不建画像（符合"多人共用一屏"语义）。

### 1.8 语音识别 `POST /asr`（🆕 2026-07-18 云端口音增强）

游客语音输入的转写入口（webapp 录音后调用，转写文本再喂 `/live/ask*` 或 `/chat`）。

```
POST /asr        multipart/form-data
  file       音频文件（webm/opus、m4a/aac、wav、mp3 等浏览器录音格式均可，无需转码）
  scenic_id  景区 ID（默认 lingshan；用于注入该景区专名做识别偏置）
  language   "zh"（默认，强制中文）/ "auto" 自动检测 / en/ja/ko 等
→ { "text": "九龙灌浴几点开始表演？", "language": "zh", "duration": 3.1,
    "hotwords_used": true, "engine": "cloud" }
```

**双引擎调度**（`ASR_PROVIDER` 环境变量，默认 `auto`）：
- `auto`：**云端 `qwen3-asr-flash` 优先**（识别大模型：带口音的普通话/方言/多语种显著更准，
  景区专名表作上下文偏置，附带标点与数字归一化），超时（默认 4.5s）或失败**自动落回本地
  faster-whisper**——游客侧永不失败，断网也能用；
- `cloud` / `local`：强制单引擎（联调排查用）。
- 返回字段 `engine` 标明本次实际引擎（`cloud` / `local`），前端无需处理、仅排障参考。

口音对比（Qwen-TTS 口音音色合成 16 句灵山专名提问，两引擎同题）：云端 **14/16**（京腔、
川普全对，两句吴语真方言里还有一句是忠实转写方言词"小囡"）、本地 whisper-small 5/16；
云端平均 0.63s，比本地（~1.6s）更快，语音问答总时延预算不受影响。

---

## 2. 知识库管理

> **队友 B（管理后台用）**：用于上传新景区文档、查看知识库状态。

### 上传文档并入库

```
POST /kb/upload
Content-Type: multipart/form-data
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `scenic_id` | string（form） | 景区 ID |
| `files` | file[]（form） | 文档文件，支持 `.docx / .pdf / .txt / .md`，可同时上传多个 |
| `replace` | bool（form） | `true` 时先清空该景区知识库再入库，默认 `false` |

```bash
curl -X POST <BASE>/kb/upload \
  -F "scenic_id=lingshan" \
  -F "files=@灵山胜境指南.docx" \
  -F "files=@补充说明.pdf"
```

```json
{
  "scenic_id": "lingshan", "files": 2, "chunks_indexed": 45,
  "items": [
    {"filename": "灵山胜境指南.docx", "chunks": 38, "status": "indexed"},
    {"filename": "补充说明.pdf",       "chunks": 7,  "status": "indexed"}
  ]
}
```
> 每个文件按后缀分派解析（docx 解析段落+表格；pdf 用 pymupdf 抽文本层；txt/md 直读）。
> **无文本层的 PDF**（扫描件 / 字体轮廓化）抽不出文字 → 该文件 `status: "unsupported"`、`chunks: 0`（仍存档登记，但不入 RAG，需先转可复制文本的 PDF 或 OCR）。
> 每次上传会自动登记到 `GET /kb/docs`（真实文档列表，前端上传后即可刷新看到）。

### 查看所有知识库状态

```
GET /kb/list
```

```json
{
  "lingshan": 45,
  "nihuawan": 6,
  "xihu": 18,
  "huangshan": 19,
  "gugong": 20
}
```

### 删除知识库

```
DELETE /kb/{scenic_id}
```

```json
{ "deleted": "lingshan" }
```

### 知识库内容管理 🆕（FAQ / 文本段落逐条 CRUD，持久化 + 实时同步进 RAG）

> 与整文档 `/kb/upload` 互补：管理员手填的细粒度知识条目，**新增/编辑即时以稳定 id upsert 进
> 对应景区的向量库、删除即时移除**——游客问答立刻能检索到。数据落 SQLite（刷新不丢）。
> 经公网网关调用统一加 `/rag` 前缀（如 `…:8443/rag/kb/faq`）。

**FAQ**
```
GET    /kb/faq?scenic_id=lingshan        列出（scenic_id 可省=全部）
POST   /kb/faq                            新增  body: {scenic_id, question, answer, category?}
PUT    /kb/faq/{id}                       编辑  body 同上
DELETE /kb/faq/{id}                       删除
```
新增/编辑返回 `{"id":N,"synced":true}`（synced=已写入 RAG）；列表项含 `id/scenic_id/question/answer/category/created_at/updated_at`。

**文本段落**（字段 `title/content/category`，其余同 FAQ）
```
GET /kb/text?scenic_id=   POST /kb/text   PUT /kb/text/{id}   DELETE /kb/text/{id}
```

**已上传文档列表**（真实记录，替代假文件名）
```
GET    /kb/docs?scenic_id=lingshan        列出 {filename,size_bytes,chunks,status,created_at}
DELETE /kb/docs/{id}                       删除登记 + 该文档全部向量 chunk（按 source=文件名）
POST   /kb/docs/{id}/reindex               重建索引：删旧 chunk → 重新解析原文件 → 重新入库 🆕
```
> `/kb/upload` 现在每次上传成功会自动登记到此列表（前端文档列表从 `/kb/docs` 查即可，上传后自动更新）。
> reindex 返回 `{"id":N,"filename":"…","chunks":M,"status":"indexed"}`；原始文件已丢失时返回 410。
> 所有知识写操作（upload/faq/text/docs 删改）现在会**自动清该景区答案缓存**，编辑后旧问句不再命中改前答案。

### 检索设置 🆕（管理端「检索配置」按景区真实生效）

> 无配置时走系统默认基线（97.1% 准确率验收配置）；管理员保存后立即覆盖该景区检索行为。

```
GET    /kb/retrieval-config?scenic_id=lingshan
       → {configured, strategy, top_k, threshold, defaults:{…}}   configured=false 表示未配置过
PUT    /kb/retrieval-config    body: {scenic_id, strategy: hybrid|semantic|keyword, top_k?: 1-10, threshold?: 0-1}
DELETE /kb/retrieval-config?scenic_id=lingshan     恢复系统默认
```
> `strategy`：hybrid=稠密+BM25 融合（默认）/ semantic=仅稠密 / keyword=仅 BM25。
> `top_k`：最终送入 LLM 的 chunk 数（覆盖 rerank_top_k）。
> `threshold`：置信度门控阈值，仅本地重排（DEPLOY_MODE=local）生效；云端模式无 reranker 自动忽略。

### 知识库自检 🆕（POST /kb/self-test：换库后一键验证准确率）

> 从当前 ChromaDB chunk 现场自动出题（程序化抽数字/专名当评分关键词，qwen-flash 组织问法），
> 走与游客完全相同的检索+生成链路作答，关键词命中评分。**不写 conversations、不进答案缓存**，
> 测试流量不污染运营分析。每题 2 次 LLM 调用，约 5-10s/题，前端需配长超时。

```
POST /kb/self-test    body: {scenic_id, sample: 1-10 (默认6)}
```
```json
{
  "scenic_id": "lingshan", "total_chunks": 113, "sample": 6, "passed": 6,
  "accuracy": 100.0, "duration_s": 41.2,
  "items": [{ "question": "灵山大佛有多高？", "keywords": ["88"], "hit_keywords": ["88"],
              "passed": true, "answer": "……88米……" }]
}
```
空库返回 404；库中无确定性事实（数字/专名）返回 422。

---

## 3. 数据分析（管理后台用）

> **队友 B（数据大屏用）**：所有接口均为 `GET`，支持按景区和时间段筛选。

### 3.1 数据大屏核心数据

```
GET /analytics/dashboard?scenic_id=lingshan&days=7
```

| 参数 | 说明 | 默认 |
|---|---|---|
| `scenic_id` | 景区 ID | `lingshan` |
| `days` | 近 N 天 | `7` |

```json
{
  "scenic_id": "lingshan",
  "period_days": 7,
  "total_conversations": 128,
  "total_sessions": 43,
  "satisfaction_rate": 0.875,
  "context_hit_rate": 0.921,
  "emotion_distribution": {
    "happy": 62, "excited": 50, "neutral": 10, "curious": 4, "apologetic": 2
  },
  "daily_stats": [
    {"date": "2026-05-17", "conversations": 18, "sessions": 6},
    {"date": "2026-05-18", "conversations": 22, "sessions": 8}
  ]
}
```

### 3.2 游客热门话题（词云数据）

```
GET /analytics/hot-topics?scenic_id=lingshan&days=7&limit=10
```

| 参数 | 说明 | 默认 |
|---|---|---|
| `limit` | 返回词数量 | `10` |

```json
{
  "topics": ["灵山大佛", "九龙灌浴", "门票", "梵宫", "拈花湾", "开放时间", "大佛高度"]
}
```

### 3.3 满意度趋势

```
GET /analytics/sentiment-trend?scenic_id=lingshan&days=30
```

```json
{
  "overall_satisfaction": 0.875,
  "trend": [
    {
      "date": "2026-05-01",
      "total": 15,
      "happy_ratio": 0.867,
      "emotion_counts": {"happy": 8, "excited": 5, "neutral": 2}
    }
  ]
}
```

### 3.3.5 实时弹幕流（大屏/管理端「游客正在问」）

```
GET /analytics/danmaku?scenic_id=lingshan&limit=40&since=2026-07-11 14:00:00
```

| 参数 | 说明 | 默认 |
|---|---|---|
| `scenic_id` | 景区 | `lingshan` |
| `limit` | 最多返回条数（≤100） | `40` |
| `since` | 上次拿到的最新 `ts`，传了走增量轮询（增量模式不做题库兜底） | 无 |

近 24h 真实提问（清洗：脱敏长数字/截断 40 字/归一化去重），不足 `limit` 且非增量时用内置题库兜底补位（`backend/data/danmaku_bank.py`，8 景区手写提问）。

```json
{
  "items": [
    { "text": "九龙灌浴下一场是几点", "emotion": "curious", "intent": "qa",
      "ts": "2026-07-11 14:21:03", "demo": false },
    { "text": "最近的厕所在哪里", "emotion": "neutral", "intent": "navigation",
      "ts": null, "demo": true }
  ],
  "real": 23,
  "bank_filled": 17
}
```

`intent` 取值 `qa / navigation / recommend / photo / empathy`（关键词+情绪推断），供前端配图标；`ts=null` 表示题库兜底条目。

### 3.4 历史对话列表（分页）

```
GET /analytics/conversations?scenic_id=lingshan&days=7&limit=20&offset=0
```

| 参数 | 说明 | 默认 |
|---|---|---|
| `scenic_id` | 景区筛选（可选） | 全部 |
| `session_id` | 会话筛选（可选） | 全部 |
| `days` | 近 N 天 | `7` |
| `limit` | 每页条数 | `50` |
| `offset` | 偏移量（分页用） | `0` |

```json
{
  "total": 128,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "session_id": "user_001",
      "scenic_id": "lingshan",
      "user_message": "灵山大佛有多高？",
      "ai_reply": "灵山大佛通高88米……",
      "emotion": "excited",
      "context_used": 1,
      "created_at": "2026-05-23 14:32:11"
    }
  ]
}
```

### 3.5 生成游客感受度报告（消耗 LLM API，按需调用）

```
POST /analytics/report
Content-Type: application/json
```

```json
{ "scenic_id": "lingshan", "days": 7 }
```

```json
{
  "scenic_id": "lingshan",
  "period_days": 7,
  "report": "## 游客感受度报告\n\n**总体满意度**：本期满意度较高，约87.5%……\n\n**游客最关注话题**：\n1. 灵山大佛高度与规模\n2. 九龙灌浴表演时间……"
}
```

### 3.6 知识盲区（知识库自进化闭环）

> 找出游客问过、但知识库答不上来的问题（`context_used=0`），按频次排序，
> 指导管理员针对性补充文档。`cluster=true` 时调 LLM 把盲区归纳成主题并给出补充建议。

```
GET /analytics/knowledge-gaps?scenic_id=lingshan&days=30&limit=20&cluster=false
```

| 参数 | 说明 | 默认 |
|---|---|---|
| `scenic_id` | 景区 ID | `lingshan` |
| `days` | 近 N 天 | `30` |
| `limit` | 返回盲区条数 | `20` |
| `cluster` | `true` 时额外调 LLM 归纳主题+建议（消耗 API） | `false` |

```json
{
  "scenic_id": "lingshan",
  "period_days": 30,
  "total_conversations": 128,
  "total_unanswered": 9,
  "unanswered_rate": 0.07,
  "gaps": [
    {"question": "灵山有充电宝租借吗", "count": 3, "last_asked": "2026-05-24 11:49:35"},
    {"question": "景区内能带宠物吗", "count": 1, "last_asked": "2026-05-24 10:12:00"}
  ],
  "suggestions": "（仅 cluster=true 时返回）## 1. 便民服务\n建议补充充电宝租借点位置..."
}
```

### 3.7 实时负面情绪预警

> 在时间窗口内聚合负面情绪（`empathetic`/`apologetic`），负面数 ≥ `threshold`
> 且占比 ≥ `min_rate` 时触发告警，附负面对话样本，供管理方实时定位投诉热点。

```
GET /analytics/alerts?scenic_id=lingshan&window_hours=24&threshold=3&min_rate=0.3
```

| 参数 | 说明 | 默认 |
|---|---|---|
| `scenic_id` | 景区 ID，**留空则扫描全部景区** | 全部 |
| `window_hours` | 统计时间窗口（小时） | `24` |
| `threshold` | 触发告警所需最少负面对话数 | `3` |
| `min_rate` | 触发告警所需最低负面占比 | `0.3` |

```json
{
  "scenic_id": "all",
  "window_hours": 24,
  "alert_triggered": false,
  "total_in_window": 37,
  "negative_count": 4,
  "negative_rate": 0.108,
  "threshold": 3,
  "min_rate": 0.3,
  "negative_by_scenic": {"nihuawan": 3, "lingshan": 1},
  "samples": [
    {"scenic_id": "lingshan", "question": "排队太久了", "emotion": "apologetic", "asked_at": "2026-05-24 12:02:43"}
  ]
}
```

---

### 3.8 客流热度感知

> 用真实游客行为数据（14 万行）算热门度 + 季节性，叠时段模型 → 拥挤档位 + 旺淡季 + 错峰时段。
> 供数据大屏「客流分布」、游客端地图 **POI 级拥挤热力**、与导游错峰建议。
>
> **`granularity` 两档**：`lingshan` 返回 **POI 级**（7 个点位，含演出聚集/天气耦合/趋势）；
> 其余景区返回**景点级**（来自行为数据，黄山/故宫不在数据中 → `has_data:false`、`attractions:[]`）。
> 真实性来源：热门度/季节性=真实行为数据；九龙灌浴/梵宫演出=景区公示场次（人群随场次聚集）；
> 天气=实时查询；分钟级拥挤=时段模型估计（`note` 已如实标注）。**同一点会随时间/天气/演出临近自然变化**，前端可定时轮询（建议 30~60s）。

```
GET /analytics/crowd?scenic_id=lingshan
```

```json
{
  "scenic_id": "lingshan", "has_data": true, "granularity": "poi",
  "season": "旅游旺季", "quiet_hours": "清晨 8 点前或傍晚 17 点后",
  "as_of": "2026-06-19 14:30",
  "next_show": {"poi": "九龙灌浴", "at": "15:00", "minutes": 30},
  "attractions": [
    {
      "poi_id": "jiulong", "attraction": "九龙灌浴", "name": "九龙灌浴",
      "lng": 120.099984, "lat": 31.424601, "indoor": false,
      "crowd_level": "较多", "crowd_index": 1.18, "trend": "上升",
      "popularity": 0.92, "in_show": false,
      "next_show": "15:00", "minutes_to_show": 30,
      "hint": "15:00 有演出，人群正在聚集，想看建议提前到、避堵可错峰",
      "factors": {"base": 0.92, "season": 1.11, "hour": 0.94, "weather": 1.0, "show": 0.0, "gate": 0.0}
    }
  ]
}
```

> 字段：`crowd_level` 空闲/适中/较多/繁忙（前端可映射绿/黄/橙/红）；`trend` 上升/平稳/下降（画箭头）；
> `next_show`/`minutes_to_show` 仅演出点位有；`hint` 一句可直接展示的错峰建议；`factors` 透明化各因子供调试。
> `attraction`==`name` 为兼容旧消费方保留。非 lingshan 的景点级条目仍是旧字段（`month_factor`/`satisfaction` 等）。

---

### 3.9 游客行为事件上报 🆕

> **数据采集「主动上报」半边**：游客端把服务端从对话里看不到的信号（画像/功能/到访/满意度）
> POST 上来，落 `events` 表。**管理端无需调用**，由游客端自动埋点；列此仅供备查。
> 详见 [`docs/数据采集与管理端对接.md`](docs/数据采集与管理端对接.md)。

```
POST /analytics/event
Content-Type: application/json
```

```jsonc
{
  "session_id": "s_ab12cd",          // 客户端独立会话 id（非 RTMP 的 sessionid）
  "scenic_id": "lingshan",
  "type": "session_start",            // 见下表
  "group_type": "family_kids",        // 仅 session_start 带
  "lang": "zh",                        // 仅 session_start 带
  "payload": { "interests": ["history"], "device": "ios" }
}
```

| `type` | 触发时机 | `payload` |
|---|---|---|
| `session_start` | 进入导览 | `{interests:[], device}` |
| `feature_open` | 打开功能 | `{feature}` ∈ tour/gps/facility/trace/photo/voice/postcard |
| `station_visit` | 听某站讲解 | `{name, via}` ∈ tour/gps |
| `photo_locate` | 拍照定位成功 | `{location}` |
| `milestone` | 走完路线/生成明信片 | `{kind}` ∈ route/postcard |
| `session_end` | 退出（sendBeacon） | `{duration_s, asks, photos, visited}` |
| `rating` | 满意度评分 | `{score:1-5, comment?}` |

返回：`{"ok": true}`（容错落库，永不抛错给前端）。

---

### 3.10 客群画像 🆕

> 同行类型 / 语言 / 兴趣 分布，来自 `session_start` 事件。供数据大屏「客群画像」。

```
GET /analytics/profile?scenic_id=lingshan&days=7
```

```json
{
  "scenic_id": "lingshan", "period_days": 7,
  "total_visitors": 36,
  "group_type": {"family_kids": 12, "couple": 9, "adult": 11, "senior": 4},
  "lang": {"zh": 30, "en": 4, "ja": 2},
  "interests": {"history": 18, "nature": 12, "photo": 9, "food": 7, "culture": 6},
  "situation": {
    "age": {"youth": 14, "elder": 6, "middle": 9, "teen": 3},
    "pace": {"day": 20, "half": 8, "deep": 5},
    "mobility": {"normal": 28, "stroller": 4, "wheelchair": 2, "hiker": 2},
    "purpose": {"relax": 15, "photo": 8, "pray": 5, "kids_fun": 6, "study": 2},
    "first_time": {"first": 26, "return": 7}
  },
  "profiled_visitors": 83,
  "dynamic_interests": {"特色美食": 35, "自然风光": 32, "禅意文化": 30, "历史人文": 30, "拍照打卡": 29},
  "styles": {"亲子型": 16, "深度型": 14, "悠闲型": 11, "打卡型": 10, "摄影型": 8},
  "unmet_needs": {"演出场次提醒": 16, "想登高看日落": 14, "就近餐饮": 13}
}
```

枚举：`group_type` ∈ adult/family_kids/senior/couple；`lang` ∈ zh/en/ja/ko；
`interests` ∈ history/nature/photo/food/culture。
`situation`（🆕 2026-06-21）= 自身情况标签 5 维分布（来自 `session_start` 事件 payload，取值见 1.6 节）；
仅展示游客实际上报过的值，老会话无此数据则各维为空对象。

**游中画像洞察（🆕 P3 2026-07-13，来自 `visitor_profile` 表，见 1.7 节）**：`profiled_visitors`=有画像的会话数；
`dynamic_interests`=对话在线推断的兴趣分布（中文标签，**治静态 `interests` 稀疏**——游客跳过开场快选也有数据）；
`styles`=游览风格分布（LLM 摘要 `style` 或轨迹推断 `style_hint`）；`unmet_needs`=游客提过但未满足的心愿/需求
top10（= 运营 & 知识库缺口，与 `/knowledge-gaps` 互补：gaps=知识盲区，unmet_needs=服务盲区）。全部增量，老前端忽略即可。

---

### 3.11 功能使用率与满意度 🆕

> 各功能打开次数 + 满意度均分 + 活跃会话数，来自 `feature_open` / `rating` 事件。
> 供数据大屏「功能使用率」「满意度」面板。

```
GET /analytics/feature-usage?scenic_id=lingshan&days=7
```

```json
{
  "scenic_id": "lingshan", "period_days": 7,
  "active_sessions": 36,
  "feature_open": {"tour": 20, "voice": 15, "photo": 12, "gps": 8, "facility": 7, "trace": 6, "postcard": 4},
  "rating_count": 18, "avg_rating": 4.5
}
```

`avg_rating` 无评分时为 `null`。

---

### 3.12 文旅 BI 分析（人口/消费/景点画像）🆕

> **队友 B（数据大屏用）**：与 3.1–3.11 的会话类分析互补——本组数据源为**游客行为数据库**
> （赛题 `景点景区旅游数据行为分析数据.xlsx` + 8 景区合成补充样本，共 ~16 万行），挖**人口画像、
> 消费结构、景点热度、满意度**等传统文旅 BI 指标。全部 `GET`、CORS 全开、可直接 `fetch`。
> 数值已聚合好，前端 ECharts 直接喂。
>
> 通用参数 `scenic_id`：8 个之一（`lingshan/nihuawan/xihu/huangshan/gugong/zhangjiajie/bingmayong/mogaoku`）
> 或 `all`（全景区汇总）。未知 id 优雅降级（`visitors:0` / 空数组）。先调 `/scenics` 拿可选项。

**① 可选景区清单**（前端下拉用）
```
GET /analytics/bi/scenics                 默认列出数据集全部景点（赛题 xlsx 全部 + 我方 8 个，共 ~159）
GET /analytics/bi/scenics?managed_only=true   只列我方接入的 8 个景区
```
```json
{"count": 159, "scenics": [
  {"scenic_id": "lingshan", "name": "灵山胜境", "samples": 2736, "managed": true},
  {"scenic_id": "同里古镇", "name": "同里古镇", "samples": 5476, "managed": false}
]}
```
> `scenic_id` 既接受我方 8 个 id（`lingshan`…），也直接接受 xlsx 里的景点名（如 `同里古镇`，URL 编码即可）。
> 所以 `/scenics` 返回的任一 `scenic_id` 拿去查 `overview/spending/demographics` 都通——**赛题表格里所有景区的数据都可访问**。

> **时间范围**：`overview`/`spending`/`demographics` 均支持可选 `days`（`1`=今日 / `7`=本周 / `30`=本月，
> 相对数据集最新日期；缺省或 `0`=全部）。例：`/analytics/bi/overview?scenic_id=lingshan&days=7`。

**② 核心 KPI 概览**（顶部数字卡）
```
GET /analytics/bi/overview?scenic_id=lingshan&days=7
```
```json
{
  "scenic_id": "lingshan", "visitors": 2736,
  "avg_spend_per_capita": 1151.5,   // 客单价（元）
  "total_revenue": 3150436.0,        // 总营收（元）
  "avg_satisfaction": 4.24,          // 平均满意度（1-5）
  "avg_stay_hours": 4.5,             // 平均停留（小时）
  "avg_group_size": 2.7              // 人均同行规模
}
```

**③ 消费结构**（饼图 structure + 客单价分布直方 histogram）
```
GET /analytics/bi/spending?scenic_id=lingshan
```
```json
{
  "scenic_id": "lingshan", "avg_total": 1151.5,
  "structure": [
    {"category": "门票", "avg": 537.1, "ratio": 0.466},
    {"category": "餐饮", "avg": 157.0, "ratio": 0.136},
    {"category": "购物", "avg": 259.8, "ratio": 0.226},
    {"category": "交通", "avg": 92.0,  "ratio": 0.08},
    {"category": "娱乐", "avg": 105.7, "ratio": 0.092}
  ],
  "histogram": [{"range": "<500", "count": 214}, {"range": "500-1000", "count": 1048}, ...]
}
```

**④ 人口画像**（年龄段/性别/同行规模，柱状/饼图）
```
GET /analytics/bi/demographics?scenic_id=lingshan
```
```json
{
  "scenic_id": "lingshan",
  "age": [{"range": "<18", "count": 208}, {"range": "18-25", "count": 402}, ...],   // 7 段
  "gender": [{"gender": "女", "count": 1498}, {"gender": "男", "count": 1238}],
  "group_size": [{"size": 1, "count": 507}, {"size": 2, "count": 938}, ...]
}
```

**⑤ 景点热度排名 + 类型分布**（横向条形 ranking + 类型饼图 by_type）
```
GET /analytics/bi/attractions?limit=10&managed_only=false
```
- `managed_only=true`：仅统计本产品接入的 8 景区（名称可辨识，**演示推荐用**）；
  `false`（默认）：数据集全域景点视图。
```json
{
  "ranking": [
    {"attraction": "灵山胜境", "visitors": 2736, "avg_spend": 1151.5, "avg_satisfaction": 4.24, "avg_stay": 4.5},
    ...
  ],
  "by_type": [{"type": "自然山岳", "count": 5000}, {"type": "宗教文化", "count": 2500}, ...]
}
```

### 3.12.1 消费分析 → 营销决策 🆕（管理端「消费分析」页 + 数据大屏；数据源=赛题行为数据 xlsx 真实样本）

> 全部端点默认 `real_only=true`（只用赛题《景点景区旅游数据行为分析数据》真实样本、不掺演示补量），
> 可对评委证明「基于此资料」。`overview`/`spending`/`demographics` 亦新增 `real_only` 参数（默认 `false`
> 保大屏既有口径）。规则化确定性输出，数字均可溯源到真实样本。灵山口径=236 条真实样本。

```
GET /analytics/bi/overview?scenic_id=lingshan&real_only=true   # 附 source 溯源字段
GET /analytics/bi/spend-tiers?scenic_id=lingshan               # 客单价分层 + 营收贡献
GET /analytics/bi/spend-drivers?scenic_id=lingshan             # 停留时长/同行规模 × 客单价
GET /analytics/bi/satisfaction-value?scenic_id=lingshan        # 满意度×消费四象限 + 散点
GET /analytics/bi/spend-trend?scenic_id=lingshan&by=month      # by=month|week 消费/客流/营收趋势
GET /analytics/bi/marketing-advice?scenic_id=lingshan          # 规则化营销建议（洞察→建议→预期）
```
```json
// spend-tiers
{"scenic_id":"lingshan","total":236,"source":"赛题《景点景区旅游数据行为分析数据》· 236 条",
 "tiers":[{"name":"低消费(<600)","count":100,"ratio":0.424,"avg_spend":402.5,"revenue_share":0.184,
           "avg_age":37.4,"avg_satisfaction":3.5,"avg_stay":4.0},
          {"name":"中消费(600-1200)","count":73,"ratio":0.309,"revenue_share":0.274, ...},
          {"name":"高消费(1200+)","count":63,"ratio":0.267,"revenue_share":0.542, ...}]}
// spend-drivers
{"stay":[{"range":"2-4h","avg_spend":964.3,"count":125}, ...],
 "group":[{"range":"独自","avg_spend":723.5,"count":28},{"range":"5人+","avg_spend":1772.8,"count":9}, ...]}
// satisfaction-value
{"median_spend":686.0,"median_sat":3.0,
 "quadrants":{"high_spend_high_sat":80,"high_spend_low_sat":38,"low_spend_high_sat":108,"low_spend_low_sat":10},
 "scatter":[{"spend":3213.0,"sat":3.0}, ... 最多 150 点]}
// spend-trend
{"trend":[{"period":"2025-03","visitors":17,"avg_spend":1145.4,"revenue":19472.0}, ...]}
// marketing-advice
{"sample":236,"avg_spend":927.2,"source":"...236 条",
 "advice":[{"insight":"消费结构中「购物」占比最高，约 27%（人均 ¥248）…",
            "action":"围绕购物做组合套餐/会员权益…","expected":"提升连带消费、拉高客单价"}, ...]}
```
> **实现注**：xlsx（16.7MB/140k 行）首读 openpyxl ~24s，落 `behavior_data.pkl` 派生缓存（<0.02s、
> 旧于 xlsx 自动重建、gitignore 不入库）根治并发首调挤爆线程池导致的端点 hang。

### 3.13 话题意图分类 🆕（替代 hot-topics 的 n-gram 碎片）

> `/analytics/hot-topics` 返回的是 2-4 字 n-gram 词频（"灵山/山大/大佛"碎片），适合词云但不是有意义的话题。
> 本接口用 LLM 把游客提问归入语义类别并计数，结果**缓存 10 分钟**（首次调用约 1-2s，之后秒回）。

```
GET /analytics/topic-intents?scenic_id=lingshan&days=30&limit=8
```
```json
{
  "scenic_id": "lingshan", "period_days": 30, "sample_size": 120,
  "topics": [
    {"intent": "景点介绍", "count": 72},
    {"intent": "路线推荐", "count": 9},
    {"intent": "票价咨询", "count": 3},
    {"intent": "交通方式", "count": 2}
  ],
  "cached": false
}
```
类别取自固定集合：景点介绍/票价咨询/交通方式/开放时间/餐饮推荐/路线推荐/设施服务/住宿预订/其他。
无会话数据时 `topics:[]`（前端可降级用 `/analytics/hot-topics` 词云）。

---

## 4. 数字人形象配置（管理端默认 ↔ 游客端精调，两端互通）

> **互通数据流**：
> ```
> 管理端(队友B)                    后端                          游客端
>   PUT /digital-human/config ──▶ digital_human_config 表
>   (配景区默认形象+音色)              │
>                                    ├─◀─ GET /config?scenic_id ── 进场取景区默认
>                                    └─◀─ GET /presets ─────────── 取形象/音色目录(画 gallery)
>                                                                  游客精调存 localStorage：
>                                                                  · 音色 → 每条 /live/ask|say 带
>                                                                    voice_id，消息级**即时生效**
>                                                                  · 形象 → 存偏好，「下次唤醒数字
>                                                                    人时换上」(进程级约束)
> ```
> 形象/音色 ID 由桥接层 AVATAR_MAP/VOICE_MAP 翻译成真实 Ditto avatar / Qwen-TTS 音色，接口契约稳定。
> **场景背景**（`background_id`）：按景区配一张默认背景，离线烘进 Ditto 源肖像（变体
> `<avatar>_bg_<bg_id>.png`），运行时零开销；桥接解析变体、缺失自动回落原图。详见 4.6。

### 4.1 获取可选形象与音色列表

```
GET /digital-human/presets                                  # 无参=全量（旧行为，向后兼容）
GET /digital-human/presets?scenic_id=lingshan&audience=admin    # 全量 + 每项 published(该景区可见性)
GET /digital-human/presets?scenic_id=lingshan&audience=visitor  # 只回已发布形象（游客端，本景区过滤）
```

> **生产者/消费者分离**（🆕 2026-07-13）：管理端=生产者看全量，游客端=消费者只看「本景区已发布」。
> `audience=visitor&scenic_id=X` 过滤规则：本景区专属身份 + 通用推荐形象可见；他景区专属身份、
> `coming_soon`、`legacy` 隐藏；本景区专属浮顶排序。发布表 `dh_avatar_publish` 可逐个覆盖（见 4.1.1）。
> 每个形象附增量字段 `stage_name`(艺名，文艺平实、游客端展示) 与 `welcome_text`(欢迎语)。

> **形象库分类法**（对标 HeyGen/Synthesia/讯飞的 faceted 多维标签，裁剪适配景区导览）：
> 主轴 `style`（前端顶部 tab：推荐由 `recommended` 派生 + 现代/古风/民族）+ 副筛 `gender`，
> 每卡片再打 `persona`(气质人设) / `outfit`(服饰) / `age`(年龄段) / `fit`(适配景区) 标签——管理端/游客按习惯浏览选对。

```jsonc
{
  "avatars": [
    {"id": "female_sweet", "name": "亲和讲解员", "gender": "female", "style": "现代",
     "persona": "亲切热忱", "outfit": "浅色活力装", "age": "青年", "fit": "现代/都市景区",
     "preview": "/avatars/female_sweet.jpg", "recommended": true},
    {"id": "female_guofeng", "name": "古典讲解员", "gender": "female", "style": "古风",
     "persona": "知性温雅", "outfit": "汉服襦裙", "age": "青年", "fit": "古镇·禅意",
     "preview": "/avatars/female_guofeng.jpg", "recommended": true},
    {"id": "male_casual", "name": "阳光讲解员", "gender": "male", "style": "现代",
     "persona": "亲切热情", "outfit": "休闲装", "age": "青年", "fit": "现代/都市景区",
     "preview": "/avatars/male_casual.jpg", "recommended": true},
    // AI 换装系列（InstantID 锁脸换装，烘录后上架；管理端不可设为默认）。name=服饰名
    {"id": "outfit_qipao", "name": "旗袍", "gender": "female", "style": "古风",
     "persona": "典雅端方", "outfit": "旗袍", "age": "青年", "fit": "古镇·民国街区",
     "preview": "/avatars/outfit_qipao.jpg", "coming_soon": true},
    // …共 6 款换装(旗袍/汉服/职业正装/民族服饰/导览马甲/冬季大衣) + 1 款 female_mature(中年)，coming_soon=true；另有 legacy:true 旧 id（UI 隐藏）
    // 身份库命名统一为「[特征]+讲解员」职务称谓（F1 知性/F2 汉服/F3 活力/F4 旗袍/F5 民族/F6 资深/M1 儒雅/M2 文士/M3 青年/M4 商务）
  ],
  "voices": [
    {"id": "voice_gentle_f", "name": "知性温柔", "gender": "female", "tone": "知性、从容（默认）"},
    {"id": "voice_lively_f", "name": "活泼亲和", "gender": "female", "tone": "明快、亲和"},
    {"id": "voice_wu_f",     "name": "吴侬软语", "gender": "female", "tone": "吴语方言、软糯（江南景区特色）"},
    {"id": "voice_calm_m",   "name": "沉稳大气", "gender": "male",   "tone": "低沉、可靠"},
    {"id": "voice_bright_m", "name": "京腔青年", "gender": "male",   "tone": "北京话、爽朗"}
  ],
  "backgrounds": [
    {"id": "",            "name": "极简灰底（原始）", "scenic": null,       "preview": null},
    {"id": "bg_lingshan", "name": "灵山·禅意佛境",   "scenic": "lingshan", "preview": "/avatar_backgrounds/bg_lingshan.jpg"},
    // …共 8 景区预设；管理端上传的自定义背景（source:"upload"）合成完(status:"ready")后也出现在此
  ]
}
```

形象字段：`style`(现代/古风/民族，**风格主轴 tab**) · `gender`(female/male，**副筛**) ·
`persona`(气质人设：活力向导/知性讲解/沉稳儒雅/亲切热情) · `outfit`(服饰) · `age`(青年/中年/长者) ·
`fit`(适配景区提示) · `preview`(预览图) · `recommended`(进"推荐"tab) · `coming_soon`(仅预览不可选) · `legacy`(旧 id 隐藏) ·
`ready`(**该形象在 ditto_avatars/ 是否真有底板**——文件系统真值，无底板者强制 `coming_soon`，杜绝"列了却没烘→选了静默回落")。
> 当前 `ready:true` = 10 身份库(F1–F6/M1–M4，各配 8 景区 × 16:9/9:16) + female_sweet + 6 同脸换装(outfit_*) = 17 个，
> 均可经 4.7 `POST /live/avatar` 直播热切。`female_guofeng`/`male_casual`(无 ditto 底板) 自动 `coming_soon`。
音色字段：`gender` + `tone`(音色描述)。
形象增量字段：`stage_name`(艺名) · `welcome_text`(欢迎语) · `published`(仅 `audience=admin&scenic_id` 时返回)。

### 4.1.1 形象艺名 / 欢迎语 / 按景区发布（管理端=生产者）🆕 2026-07-13

```
GET /digital-human/avatar-meta?scenic_id=lingshan
```
返回全量形象的艺名/欢迎语/该景区发布状态（形象管理列表页）：
```jsonc
[ { "avatar_id": "dh_lingshan", "name": "灵山·导览专员", "stage_name": "云岫",
    "welcome_text": "大家好，我是云岫，很高兴为您导览。",
    "enabled": true, "sort": 0, "stage_name_override": null, "source": "default" }, … ]
```

```
PUT /digital-human/avatar-meta      { "avatar_id": "dh_lingshan", "stage_name": "云岫", "welcome_text": "…" }
```
更新某形象的艺名（全局）。`stage_name` strip 后须 1–8 字且含有效文字，否则 **400**；`welcome_text` ≤60 字。
不传的字段保持原值（部分更新）。非法 `avatar_id` → **400**。

```
PUT /digital-human/avatar-publish   { "scenic_id": "lingshan", "avatar_id": "dh_gugong",
                                      "enabled": true, "sort": 0, "stage_name_override": "…" }
```
设置某形象在某景区的发布状态/排序/艺名覆盖（UPSERT）。`enabled=false` 强制对游客端隐藏，
`true` 强制显示（可让他景区形象在本景区上架）；`stage_name_override` 空串=清除覆盖。

### 4.2 获取某景区配置

```
GET /digital-human/config?scenic_id=lingshan
```

回落顺序（带 `"fallback": true`）：① 该景区显式配置行 → ② 🆕 **该景区专属身份形象**（身份库
`dh_<scenic>` 且底板就绪，如灵山→`dh_lingshan`、故宫→`dh_gugong`，**零 DB 播种自动生效**）→
③ 全局 `default` 行 → ④ 内置默认值。即每个景区默认就用自己的专属数字人，无需逐景区配置。

```json
{
  "scenic_id": "lingshan",
  "avatar_id": "female_sweet",
  "avatar_name": "亲和讲解员",
  "voice_id": "voice_gentle_f",
  "voice_name": "知性温柔",
  "background_id": "bg_lingshan",
  "background_name": "灵山·禅意佛境",
  "stage_name": "云岫",
  "updated_at": "2026-06-12 23:03:12"
}
```
> `stage_name`(🆕 2026-07-13) = 当前形象艺名（游客端进场即知），按 4.1.1 规则解析。

### 4.3 保存/更新配置

```
PUT /digital-human/config
Content-Type: application/json
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `scenic_id` | string | ✅ | 景区 ID，`default` 表示全局默认 |
| `avatar_id` | string | ✅ | 形象 ID，须来自 presets |
| `avatar_name` | string | ✅ | 形象显示名 |
| `voice_id` | string | ✅ | 音色 ID，须来自 presets |
| `voice_name` | string | ✅ | 音色显示名 |
| `background_id` | string | 可选 | 场景背景 ID，须来自 presets.backgrounds 或已 ready 的上传背景；省略/空 = 原始灰底 |
| `background_name` | string | 可选 | 背景显示名 |

```bash
curl -X PUT {BASE}/rag/digital-human/config \
  -H "Content-Type: application/json" \
  -d '{"scenic_id":"lingshan","avatar_id":"female_sweet","avatar_name":"亲和讲解员","voice_id":"voice_gentle_f","voice_name":"知性温柔","background_id":"bg_lingshan","background_name":"灵山·禅意佛境"}'
```

```json
{ "ok": true, "scenic_id": "lingshan" }
```

> 提示：可为每个景区配置不同形象+音色（灵山禅意女声、故宫古风男声），切换景区时一并切换形象，体现「插拔式」设计。

### 4.4 获取全部景区配置

```
GET /digital-human/config/all
```

返回已配置的所有景区快照数组，用于管理后台列表页。

### 4.5 游客端音色精调（桥接层，消息级即时生效）

> 游客在「数字人形象」面板选音色后，前端在每条驱动请求里带 `voice_id`，**覆盖**管理端景区默认：

```jsonc
POST {BASE}/live/ask   // 或 /live/say
{ "sessionid": "0", "message": "…", "scenic_id": "lingshan",
  "voice_id": "voice_wu_f" }    // 可选；省略 = 跟随管理端景区默认
```

桥接按 VOICE_MAP 译成 `tts.ref_file`（如 voice_wu_f→Jada），qwentts 检测到音色变化自动重连——**下一句话就换声**。
形象（外观/服饰）有两种生效方式：**即时热切**见 4.7 `POST /live/avatar`（直播当场换、不断流，推荐）；
或存为偏好走连接级（`GET /live/avatar` 解析 → /offer），下次唤醒生效。

### 4.6 场景背景（按景区自动 · 下次连接生效）

> 数字人身后不再是空白灰底——每景区配一张场景背景（灵山雾山佛光 / 西湖烟雨 / 故宫秋色…）。
> **原理**：Ditto"驱动原图"，输出帧背景 = 源肖像背景 → 背景离线烘进源图（抠像+景深虚化+色调对齐
> 合成，`scripts/gen_avatar_background.py`），**运行时零开销**，实测说话/头动时背景稳定。

**数据流**：

```
管理端 PUT /config 带 background_id ──▶ digital_human_config 表
                                          │
桥接 /live/avatar、scripts/resolve_avatar.py
   读配置 → 变体 <avatar>_bg_<bg_id>.png 存在 → 用变体；缺失 → 回落原图
   LiveTalking 启动: --avatar_id $(resolve_avatar.py --scenic <id>)   ← 下次连接生效
```

**自定义背景上传**（拉取式：后端可在 ECS，合成必须在本地 GPU 机执行）：

| 端点 | 说明 |
|---|---|
| `POST /digital-human/background/upload` | multipart：`file`(png/jpg ≤20MB) + `name` + `scenic_id`(可选)。登记为 `pending` |
| `GET /digital-human/background/pending` | 本地合成脚本轮询待办 |
| `GET /digital-human/background/file/{bg_id}` | 本地脚本下载原图 |
| `POST /digital-human/background/{bg_id}/ready` | 合成完成回调；之后才可被 PUT /config 引用 |

本地闭环命令：`scripts/gen_avatar_background.py sync --backend {BASE}/rag`
（拉 pending → 下载 → 抠像合成 → 回调 ready）。

`GET {BASE}/live/avatar?scenic_id=lingshan` 响应已带 `background_id` 字段（前端展示/排障）。

### 4.7 热拔插切换形象（直播不断流）🆕

> 选一下形象/换装，**正在直播的数字人当场换人/换装（~1s），不重连、不断流**——区别于 4.5「下次唤醒生效」的进程级约束。
> **原理**：Ditto 把"身份"存成逐帧 numpy 列表（appearance/motion/putback），不绑 TRT 引擎状态；引擎
> `set_source()` 重跑源注册后**原子替换**该列表（仿 `set_emotion` 热切），LiveTalking `/set_avatar` 路由触发。

```
POST {BASE}/live/avatar
Content-Type: application/json
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `avatar_id` | string | ✅ | 形象 ID（presets 里 `ready:true` 的，如 `F2_hanfu`/`outfit_qipao`/`female_sweet`） |
| `scenic_id` | string | 可选 | 景区（默认 lingshan）；决定取哪张带景底板 |
| `sessionid` | string | 可选 | 直播会话 ID（webapp 常量 `"0"`） |
| `screen` | string | 可选 | `main`=手机 16:9(8010) / `portrait`=大屏 9:16(8011) |

桥接按「形象 × 景区 × 屏幕比例」解析到真实底板（身份库 `<id>__<scenic>__<aspect>` 或 sweet 传统
`<base>_bg_<scenic>`），存在性校验 + 缺失优雅回落，再调 LiveTalking `/set_avatar` 原子热切。

```bash
curl -X POST {BASE}/live/avatar -H "Content-Type: application/json" \
  -d '{"avatar_id":"outfit_qipao","scenic_id":"lingshan","sessionid":"0","screen":"main"}'
```

```json
{ "ok": true, "avatar_id": "outfit_qipao",
  "resolved": "sweet_outfit_qipao__lingshan__16x9", "screen": "main",
  "detail": {"code":0,"msg":"ok","data":{"avatar_id":"sweet_outfit_qipao__lingshan__16x9","switched":true}} }
```

> **前端接法**（游客端形象库「试穿/换装」、管理端「形象配置」即时预览）：选 `ready:true` 形象 →
> `POST /live/avatar` → 直播热切。要持久化为景区默认，另调 `PUT /digital-human/config`（两者互补、互不耦合）。
> ⚠️ 底板须与当前**直播流分辨率**一致（main 16:9=640×360 / portrait 9:16=720×1280）——桥接已按 `screen`
> 自动取对应比例底板，前端只传 `screen`。底板分辨率与流不符会导致 Ditto putback 撕裂/过曝（已实测）。

#### 4.7.1 场景氛围底图（kiosk 页面背景与视频同源）🆕

```
GET {BASE}/live/scenic-bg?scenic_id=lingshan&screen=portrait
```

返回该景区**当前配置形象底板**的缩小模糊 JPEG（≤128px、GaussianBlur，Cache-Control 10min），
供大屏页面 `background-image: cover` 铺环境底——页面氛围与数字人视频天然同一个场景，
换景区/换形象自动跟随（换库不换码）。`screen` 同 4.7；无底板时 404（前端可忽略，保持纯色底）。

#### 4.7.2 形象底板离线预览（管理端调参 · 零串扰）🆕 2026-07-13

```
GET {BASE}/live/avatar-plate?avatar_id=dh_lingshan&scenic_id=lingshan&screen=portrait&background_id=
```

把 `(avatar_id, scenic_id, screen, background_id)` 按与 `POST /live/avatar` **完全相同**的候选解析
落到实际底板，返回该底板缩略 JPEG（宽≤540、不模糊、**不触碰直播流**）。管理端形象工作台调任一参数即
换此预览图，所见 = 热切后空闲画面，天然一致、多用户零串扰。响应头 `X-Resolved-Plate` = 实际底板名
（变体缺失自动回落原图，前端可据此提示）；无底板 404。

#### 4.7.3 说话嘴幅 / 情绪基调热调（桥接→引擎）🆕 2026-07-13

```
POST {BASE}/live/lip      { "scale": 0.68, "screen": "both" }      # scale∈[0.3,1.0]，1=原始，越小张口越含蓄
POST {BASE}/live/emotion  { "emotion": "happy", "screen": "portrait", "sessionid": "0" }
```

- **嘴幅**：桥接转发 LiveTalking `POST /set_lip` 写进程级 env `DITTO_LIP_SCALE`，Ditto `motion_stitch` **每帧读**
  → 把 lip 维度朝 source(闭口)拉，`scale<1` 收小张口。调优默认 **0.68 ≈「刚刚不露齿」**（0.6 无齿、0.75 微露齿）。
  `screen`：`both`/`main`/`portrait`。即时生效、不停流、零开销。管理端形象工作台「说话嘴幅」滑杆即调此值。
- **情绪**：转发 `POST /set_emotion`（暴露 `ditto_avatar.set_emotion`，单属性原子赋值热切）。
  `emotion`∈ happy/excited/neutral/calm/curious/concerned/empathetic/apologetic。
- 引擎补丁：`ditto-talkinghead/core/atomic_components/motion_stitch.py`（lip-scale）+ `LiveTalking/server/routes.py`
  （两路由），服务器备份 `.bak_lipscale`，仓库镜像 `livetalking_engine/`。

---

### 4.8 AI 定制形象（万相在线生成，即时入库可驱动）🆕

> 一句话描述 → 万相文生图「人景一体」生成一位**全新向导** → 落 `ditto_avatars/` 双比例底板 →
> **立即加入形象库（`ready:true`）并可 4.7 热切上身**。无需烘录：Ditto「驱动源图」，源图存在即可驱动，
> `set_avatar` 运行时重跑源注册。16:9 与 9:16 用同一 seed 两次生图保证同一人，分供手机端/大屏端。

```
POST {BASE}/digital-human/generate
Content-Type: application/json
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `prompt` | string | 可选 | 形象描述（如「身着米色针织衫、温柔亲切的年轻女导游」），空则用通用导览员模板 |
| `scenic_id` | string | 可选 | 景区（默认 lingshan）；决定生成的场景背景 |
| `gender` | string | 可选 | `female`(默认) / `male` |
| `style` | string | 可选 | `现代`(默认) / `古风` / `民族` |
| `name` | string | 可选 | 形象名（默认「我的专属向导」） |

```json
{ "ok": true, "scenic_id": "lingshan",
  "avatar": { "id": "custom_20260619_170212", "name": "测试向导", "gender": "female",
    "style": "现代", "persona": "AI 定制", "preview": "{BASE}/digital-human/avatar-preview/custom_20260619_170212",
    "recommended": true, "custom": true, "ready": true } }
```

> 生成约 **30 秒**（两次万相文生图）。新形象写入 `custom_avatars.json`，随后出现在 4.1 `/presets` 的
> `avatars[]`（`ready:true`、`custom:true`），可被 4.3 `PUT /config` 设为景区默认、被 4.7 `POST /live/avatar` 热切。
> **预览图**：`GET {BASE}/digital-human/avatar-preview/{id}` → image/jpeg（绝对 URL，跨前端可达）。
> 前端接法：游客端「形象工坊·AI 定制」、管理端「AI 生成专属向导」均填描述 → 调本端点 → 刷新形象库 + 热切上身。

### 4.10 甜美女性候选批（生成 → 挑选 → 体检 → 采用为默认）

> 与 4.9 同管线，但专为「甜美女性默认形象」：①甜美微笑不露齿基调 ②强制居中构图 +
> negative 排除背景人形/剪影（唇形健康铁律）③落 staging 暂存目录，**未采用不进 ditto_avatars**
> ④每张只**校验**居中偏差、绝不平移（平移=唇形坍缩根因）。

```
POST {BASE}/digital-human/generate-candidates   { "scenic_id": "lingshan", "count": 6, "prompt": "" }
→ { "ok": true, "started": true, "target": 6, "scenic_id": "lingshan" }   （后台任务，立即返回）

GET  {BASE}/digital-human/candidates
→ { "candidates": [ { "cand_id": "cand_20260713_...", "scenic_id": "lingshan", "seed": 123,
      "center_offset_pct": 1.2, "centered": true,
      "preview": "{BASE}/digital-human/candidate-preview/cand_...", "created_at": "..." }, ... ],
    "progress": { "running": false, "target": 6, "done": 6, "error": null, "scenic_id": "lingshan" } }

GET  {BASE}/digital-human/candidate-preview/{cid}?asp=      # asp 空=缩略 jpg；asp=16x9/9x16→原比例 png

POST {BASE}/digital-human/candidates/{cid}/adopt   { "name": "甜甜", "stage_name": "甜甜" }
→ { "ok": true, "avatar": { "id": "custom_...", ... "ready": true }, "stage_name": "甜甜" }
   # 拒未居中（400）；复制双比例进 ditto_avatars + 写 custom_avatars.json + 艺名；不写 config
```

> 采用后形象即出现在 4.1 `/presets`，需再 `PUT /config` 显式设为景区默认（设默认是独立动作）。
> **上岗前必须过 lipmatrix 开口体检**（GPU 机 `/root/autodl-tmp/lipmatrix.sh <custom_id> adopt lingshan`）。

---

## 5. 景区主题（管理端可配置换肤）

> 每个景区一套品牌色（`primary` 主色 + `sweet` 暖点缀，OKLCH 字符串）。游客端切景区时拉
> `GET /scenic/theme` 把颜色套到 CSS 变量 → **整 App 随景区换肤**（灵山禅金 / 西湖湖青 / 故宫朱红…）。
> **管理端**可 `PUT /scenic/theme` 覆盖默认色、`GET /scenic/themes` 取全部做配色面板。
> 深色模式由游客端本地切换（浅色/深色/跟随系统），与景区主题正交叠加，无需后端。

### 5.1 获取某景区主题

```
GET /scenic/theme?scenic_id=gugong
```
```json
{"scenic_id": "gugong", "name": "故宫·朱红",
 "primary": "oklch(0.55 0.19 28)", "sweet": "oklch(0.78 0.14 82)",
 "primary_hex": "#c93029", "sweet_hex": "#e4ad3c",
 "guide_name": "故宫AI智能导览数字人",
 "scenic_type": "museum", "type_label": "博物展陈"}
```
> **两种颜色格式都给**：`primary`/`sweet` 是 OKLCH（游客端 webapp 直接喂 CSS 变量）；
> `primary_hex`/`sweet_hex` 是同色的 Hex（**管理端色板直接用，无需自己做 OKLCH↔Hex 转换**）。
>
> `guide_name` = 该景区数字人对外名（去人名化，统一「<景区简称>AI智能导览数字人」）。
>
> 🆕 `scenic_type` + `type_label` = 景区类型画像（`religious` 禅意宗教 / `museum` 博物展陈 /
> `mountain` 自然山岳 / `urban_open` 开放城市 / `resort_town` 度假小镇）。后端据此让讲解口吻、
> 主动提醒、推荐侧重**按类型差异化**（灵山禅意温润 ↔ 故宫文博学者）；前端可用 `type_label` 做
> 景区语境标签（如形象工坊「为〈故宫·博物展陈〉配置」）。未知景区两字段为空串。

### 5.2 获取全部景区主题（管理端列表/配色面板）

```
GET /scenic/themes
```
```json
{"themes": [
  {"scenic_id": "lingshan", "name": "灵山·禅金", "primary": "oklch(0.575 0.2 268)", "sweet": "oklch(0.77 0.13 70)"},
  {"scenic_id": "gugong",  "name": "故宫·朱红", "primary": "oklch(0.55 0.19 28)",  "sweet": "oklch(0.78 0.14 82)"}
]}
```

### 5.3 覆盖某景区主题（管理端配置）

> 部分字段更新：只传想改的字段，未传的保留原值。**颜色传 Hex 或 OKLCH 都行**（自动识别），
> 也可用 `primary_hex`/`sweet_hex` 字段直传 Hex。内部统一规范成 OKLCH 落库。

```
PUT /scenic/theme
Content-Type: application/json
```
```jsonc
{ "scenic_id": "lingshan", "primary_hex": "#7c5cff", "sweet_hex": "#e0a86b" }  // 管理端色板直传 Hex
// 或 { "scenic_id": "lingshan", "primary": "oklch(0.6 0.18 30)" }              // OKLCH 也行
```
返回合并后的完整主题（同 5.1 结构，含 `primary_hex`/`sweet_hex`）。前端拿到即可实时套用。

---

## 6. 数字人直播与驱动（桥接层）🆕

> 桥接层 `:6006`（公网网关 `https://<autodl>:8443`）同时提供**两路独立数字人**，互不干扰：
>
> | 屏幕 | 比例 | 用途 | `screen` 取值 |
> |---|---|---|---|
> | 手机端 | 16:9（1280×720） | 游客端手机网页 / APK | `main`（默认） |
> | **大屏竖版** | **9:16（720×1280）** | 游客端大屏立屏 web | `portrait` |
>
> 两路共用同一套 RAG 知识库与 8 景区，问答内容一致；通过 `screen` 字段路由到对应的 LiveTalking 实例。

### 6.1 拉取数字人直播画面

| 用途 | 手机端 16:9 | 大屏竖版 9:16 |
|---|---|---|
| FLV（低延迟，安卓/桌面/Chrome） | `GET /stream.flv` | `GET /stream_portrait.flv` |
| HLS（iOS Safari） | `GET /hls/livestream.m3u8` | `GET /hls/livestream2.m3u8` |

均为同源、CORS 全开，前端 `<video>`（HLS）或 mpegts.js（FLV）直接播。

### 6.2 驱动数字人答问（游客提问 → 数字人开口）

```
POST /live/ask
Content-Type: application/json
```
| 字段 | 类型 | 说明 |
|---|---|---|
| `message` | string | 游客问题 |
| `scenic_id` | string | 8 景区之一，默认 `lingshan` |
| `sessionid` | string | LiveTalking 会话 ID，固定 `"0"`（WebRTC 通道，多路共享） |
| `session_id` | string | RAG 业务会话 ID（历史/分析/游中画像），默认 `anonymous`；游客端应传 per-tab 稳定 id 才能积累画像 🆕 |
| `screen` | string | `main`(手机端 16:9，默认) / `portrait`(大屏竖版 9:16) 🆕 |
| `group_type` | string | `adult`/`family_kids`/`senior`/`couple`，默认 `adult` |
| `situation` | object? | 自身情况标签（透传 RAG），字段见 1.6 节；缺省/全默认 = 行为不变 🆕 |
| `interests` | string[] | 静态兴趣（透传 RAG 入游中画像），见 1.7 节；默认 `[]` 🆕 |
| `lang` | string | `auto`/`zh`/`en`/… 默认 `auto` |
| `voice_id` | string? | 精调音色（覆盖景区默认） |

```jsonc
// 大屏竖版驱动示例
{ "message": "灵山有什么好玩的", "scenic_id": "lingshan", "sessionid": "0", "screen": "portrait" }
```
```json
{
  "ok": true, "reply": "...", "emotion": "happy", "intent": "qa",
  "sentence_count": 3, "drive_failures": 0, "mode": "avatar", "degraded": false
}
```
返回后数字人随即逐句开口（首句 ~1-2s）。`mode:"avatar"` = 正常驱动；`mode:"text"` = 容量满降级为纯文字（答案照出）。
响应另含 `first_sentence_ms`（首句送达耗时 ≈ 数字人开口时刻）。⚠️ JSON 端点要等**整段答案生成完**才返回——长答案(如"讲个故事")会到 6-9s；这是生成总时长，**不是开口延迟**。要"字幕随说话逐字吐 / 拿真实开口延迟"用下面的 SSE 流式版。

#### 6.2.1 字幕流式版 `POST /live/ask_stream`（卡拉OK式同步字幕，🆕 2026-06-18）

同 `/live/ask`（请求体字段完全一致），但以 **SSE** 把字幕逐句下发——每把一句送数字人开口就立即下发该句，让前端字幕与数字人说话**同步流式吐字**。响应 `Content-Type: text/event-stream`，每个 `data:` 一行一个 JSON 事件：

| `type` | 字段 | 时机/说明 |
|---|---|---|
| `open` | `drive_enabled`(bool), `voice`(str) | 最先到：本轮是否真开口（决定字幕节奏） |
| `sentence` | `text`, `index`, `emotion` | 每句送数字人开口时下发（前端据此按说话速率逐字吐） |
| `done` | 同 `/live/ask` 完整响应 dict（`reply`/`mode`/`degraded`/`intent`/`emotion`/`first_sentence_ms`…） | 收尾 |
| `error` | `detail`, `status` | 出错 |

前端用法：累积 `sentence.text` 成完整答案，按说话速率(~5 字/秒)推进字符游标显示；首句到达 ≈ 数字人开口时刻（诚实延迟口径，~2-4s），而非整段生成。L1 命中(`mode:clip`)直接 `done` 带 `clip_url`，无 `sentence`。

### 6.3 让数字人说指定文字（迎宾/公告，不走问答）

```
POST /live/say
{ "text": "欢迎来到灵山胜境", "scenic_id": "lingshan", "sessionid": "0", "screen": "portrait", "emotion": "happy", "queue": true }
```
`screen` 同 6.2；`emotion` 切换面部表情底座（见附录情绪枚举）。用于大屏主动迎宾、应急公告、拍照定位讲解等。

**有序播放规则（2026-07-12 起）**：
- `queue: true` → 入该屏播报队列串行播放：一条播完才播下一条，自动播报（迎宾/客流/设施/路线）之间**永不互相打断**。返回 `{ ok, queued: true, position }`。排队超 90s 未轮到自动丢弃。**大屏面板类主动播报一律用此模式。**
- `queue` 缺省（false）→ 直发，行为与旧版完全一致；`interrupt: true` 时视为**用户主动内容**：立即打断当前播报、清空该屏排队、硬清引擎端残句。
- `/live/ask*`（用户提问）永远是用户主动内容：立即打断 + 清空排队，保证提问秒响应。

### 6.4 查询当前正在播的内容（逐句字幕 / 音波真信号）🆕

```
GET /live/now-playing?screen=portrait&sessionid=0
→ { "speaking": true, "text": "灵山大佛通高88米…", "source": "ask", "elapsed_ms": 1200, "est_ms": 5300, "avatar_id": "dh_lingshan" }
→ { "speaking": false, "text": "", "source": "", "elapsed_ms": 0, "est_ms": 0, "avatar_id": "dh_lingshan" }
```
> `avatar_id`(🆕 2026-07-13) = 该屏当前直播的形象 id（热切成功即登记），供游客端切换过渡层收尾对账。

桥接在每次把文本送数字人引擎时登记「该屏正在播什么」，三路全覆盖：问答逐句
（`source:"ask"`，随每句开口滚动更新）、播报队列（`"queue"`）、直发 say（`"say"`）。
纯内存查表零下游调用，轮询友好（前端建议 ~800ms）。条目按字数估算时长自然过期；
用户提问/interrupt 打断时立即清空（字幕即刻让位）。大屏用它驱动逐句字幕与音波兜底动画，
比前端按字数估算滚动更贴近真实开口时刻（偏差 ≤ 驱动提前量 ~0.8s）。

### 6.5 应急广播 + 上屏字幕 🆕（2026-07-14）

管理端「应急广播」一次调用即让所选屏数字人开口播报（打断当前讲解），并可同时向现场大屏推一条醒目字幕横幅。

```
POST /live/broadcast
{ "text": "请游客注意，景区将于17:30闭园", "screens": ["portrait","main"],
  "scenic_id": "lingshan", "emotion": "concerned", "subtitle": true, "duration_s": 20, "style": "alert" }
→ { "ok": true, "spoken": {"portrait": true, "main": true}, "subtitle": true, "screens": ["portrait","main"] }
```
- `screens`：目标屏（`portrait`=大屏 / `main`=手机端）。内部对每屏调 `/live/say`（interrupt 直发）。
- `subtitle: true` 时同时写上屏字幕（各屏独立）；`style`=`alert`(警示红)/`info`(通知蓝)；`duration_s` 停留秒数。

```
POST /live/subtitle   { "text": "...", "screen": "portrait|main|both", "duration_s": 20, "style": "alert" }
→ { "ok": true, "screens": ["portrait"], "cleared": false }        // text 为空=撤下字幕
GET  /live/subtitle?screen=portrait
→ { "active": true, "text": "...", "style": "alert", "remain_ms": 12000 }   // 无/过期 active:false
```
> kiosk 轮询 `GET /live/subtitle`（建议 ~1s）在数字人层之上渲染字幕横幅，到期自动淡出。纯内存查表、轮询友好。

---

## 7. 扫码接力 / 同游（跨设备带走对话与个性化）🆕

把一台设备上的「对话历史 + 个性化画像」打成短时快照(token)，另一台设备扫码即接着逛。
**双向通用**：大屏 Kiosk →手机（游客带走导览）、手机→手机（家人同游 / 换机续逛）。

**机制**：源端 `create` 提交快照（它已渲染的对话 + 当前画像）→ 拿不透明 `token` →
用**自己的 origin** 拼 `claim_url = <origin>/?h=<token>` → 由 `qr.png` 渲成二维码展示 →
另一端扫码打开 `claim_url` → 前端读 `?h=` 调 `claim` 取回快照 → 注水画像(localStorage)+
注入历史对话+跳过开场。**快照本体不进 URL，只凭 token 取**；TTL 默认 5min、过期即焚；
TTL 内可重复 claim（容忍扫码重试）。隐私：公共大屏应**按需生成 + 倒计时自毁**，不常驻二维码。

### 7.1 生成接力快照

```
POST /handoff/create
{
  "scenic_id": "lingshan",
  "group_type": "family_kids",        // adult / family_kids / senior / couple
  "lang": "zh",
  "interests": ["history", "photo"],
  "avatar_id": null,                   // 可选：形象/音色精调偏好（空=景区默认）
  "voice_id": null,
  "messages": [                        // 源端已渲染的对话，最近 N 轮（服务端截 40 条、过滤空文本）
    { "role": "user", "text": "灵山大佛有多高" },
    { "role": "assistant", "text": "灵山大佛高88米。", "emotion": "happy", "intent": "qa" }
  ],
  "trace": null,                       // 可选：足迹/明信片状态（手机→手机携带）
  "source_session_id": null,           // 可选：不便序列化 messages 时，给源会话 id 由服务端回读 conversations
  "poi": null,                         // 可选：深链接，接力后定位到某景点
  "source": "kiosk",                   // kiosk | phone
  "situation": {                       // 🆕 可选：自身情况标签 5 维（手机→手机携带，字段见 1.6 节）；
    "mobility": "wheelchair", "purpose": "pray"   //   仅带有值的维度平铺进快照、claim 时一并返回
  },
  "ttl": 300                           // 秒，30~1800，默认 300
}
→ 200 { "ok": true, "token": "zVMGib_nAIQ", "expires_in": 300, "claim_path": "/?h=zVMGib_nAIQ", "msg_count": 2 }
```
源端拿到 `token` 后：`claim_url = location.origin + claim_path`，二维码 = `GET /handoff/qr.png?data=<encodeURIComponent(claim_url)>`。

### 7.2 领取接力快照

```
POST /handoff/claim
{ "token": "zVMGib_nAIQ", "session_id": "s_ab12cd34" }   // session_id=领取方业务会话 id 🆕
→ 200 { "ok": true, "scenic_id": "lingshan", "group_type": "family_kids", "lang": "zh",
        "interests": ["history","photo"], "avatar_id": null, "voice_id": null,
        "messages": [...], "trace": null, "poi": null, "source": "kiosk",
        "source_session_id": "s_xy...", "profile_summary": "爱拍照、想看表演的深度型游客" }  // 🆕 游中画像接力
→ 404 { "ok": false, "reason": "not_found" }   // token 不存在
→ 410 { "ok": false, "reason": "expired" }      // 已过期（顺手 GC）
```
前端 claim 成功后：写 localStorage（`lingjing.scenic/group/interests/lang/voice/avatar`）、
把 `messages` 注入聊天流、`onboarded=1` 跳过开场；失败则正常进开场。
**游中画像接力（🆕 P2）**：`create` 时源端传 `source_session_id` → 快照带上其一句话画像 `profile_summary`；
`claim` 带领取方 `session_id` → 服务端把源画像**并入**领取方会话（UPSERT 合并 interests，不覆盖），
换设备后推荐/导航继续"懂他"。见 1.7 节。

### 7.3 二维码图片

```
GET /handoff/qr.png?data=<任意文本，通常是完整 claim_url>
→ 200 image/png（segno 渲染，Cache-Control max-age=300）
```
源端传它自己 origin 拼好的 `claim_url` → 跨公网网关/局域网都扫得通（服务端无需知道公网地址）。

---

## 附录：数据类型说明

### 情绪 `emotion` 枚举

| 值 | 中文含义 | 触发场景 |
|---|---|---|
| `happy` | 开心 | 正面讲解、日常介绍 |
| `excited` | 兴奋 | 描述震撼景点或重大亮点 |
| `neutral` | 平静 | 客观陈述数据、信息 |
| `curious` | 好奇 | 引导游客互动探索 |
| `empathetic` | 关切 | 游客困惑或遇到问题时 |
| `apologetic` | 抱歉 | 知识库无相关信息时 |

### 意图 `intent` 枚举

由 Orchestrator（调度中枢）对每轮提问判定，决定走哪条处理逻辑。

| 值 | 中文含义 | 触发场景 |
|---|---|---|
| `qa` | 知识问答 | 询问历史/文化/数据等（默认，走 RAG） |
| `navigation` | 路线规划 | 询问游览路线、顺序、行程安排 |
| `recommend` | 个性推荐 | 寻求推荐（值得去的、适合的、拍照点） |
| `empathy` | 情感安抚 | 表达负面情绪、抱怨、求助 |
| `chitchat` | 闲聊互动 | 与景点无关的闲聊、问候（跳过 RAG） |

### 错误响应格式

```json
{ "detail": "错误描述" }
```

| HTTP 状态码 | 含义 |
|---|---|
| `400` | 请求参数错误（如 `image_b64` 为空） |
| `500` | 服务内部错误（如 LLM API 调用失败） |

### 多轮对话说明

后端**不保存对话上下文**，每次请求均需客户端在 `history` 字段中携带历史记录。建议前端维护最近 3-5 轮的对话，避免 prompt 过长。

```json
{
  "message": "它多高？",
  "scenic_id": "lingshan",
  "history": [
    {"role": "user",      "content": "灵山大佛是什么"},
    {"role": "assistant", "content": "灵山大佛是世界最高的青铜坐佛……"}
  ]
}
```

---

*文档版本：v0.5 | 更新日期：2026-05-26*
