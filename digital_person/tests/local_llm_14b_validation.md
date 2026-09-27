# 本地 LLM 兜底（Qwen2.5-14B）验证报告

> 日期：2026-06-20　执行：窗口① 全栈　目的：验证「本地 LLM 离线兜底」能否满足赛题两项硬指标
> 背景：阿里云百炼 2026-07-13 下线 qwen-turbo/qwen-vl-max（已迁 qwen-flash/qwen3-vl-plus，见 API_DOC）；
> 进一步做「云端默认 + 本地兜底」双后端，本报告验证本地后端的可用性。**结论：够用，不是更优。**

## 一、测试配置

| 项 | 值 |
|---|---|
| 模型 | Qwen2.5-14B-Instruct，Q4_K_M GGUF（bartowski），9.0 GB |
| 推理引擎 | Ollama 0.30.10（OpenAI 兼容端点 :11434/v1），`num_ctx=8192` |
| 后端切换 | `LLM_BACKEND=local`（云端路径零改动，仅此分支切走；见 `backend/llm/client.py`） |
| 硬件 | AutoDL RTX 4090D 24G；14B 占 ~10G + 数字人双流 ~5.7G = 16G/24G，**100% 上 GPU、无 CPU 卸载** |
| 嵌入/检索 | 不变（DashScope text-embedding-v3 + BGE-reranker + BM25 混合） |
| 判分口径 | `any(keyword in reply)`，与云端基线**完全同口径**（apples-to-apples） |

## 二、准确率（赛题硬红线 ≥90%）

| 景区 | 命中 | 命中率 |
|---|---|---|
| 灵山胜境 | 20/20 | 100% |
| 西湖 | 8/8 | 100% |
| 黄山 | 8/8 | 100% |
| 故宫 | 8/8 | 100% |
| **合计** | **44/44** | **100%** |

- 云端基线（qwen-plus）同口径 97.7%（44 题混合集）/ 本测试集 100%。
- **诚实口径**：100% vs 97.7% 无统计意义——该判分极宽松（只看"有没有答出关键事实/没拒答"），
  云端与本地在此尺子上都基本饱和，**测不出真实质量差**。答案的流畅度/讲故事深度/口播格式/
  多语言/幻觉控制等维度本测试**看不见**，这些维度上云端大模型（qwen-plus/max）大概率**等于或优于** 14B。
- 准确率守得住的根因：事实由 RAG 检索 context 约束，14B 只需读懂上下文复述，跨景区泛化稳。

## 三、实时性（赛题示例 <5s "说完→开口"）

测「请求 → 第一句下发（=数字人开口时刻）」墙钟，桥接 `/live/ask_stream`，warm 模型，每问 2 次：

| 指标 | 数值 |
|---|---|
| 首句延迟（14B 首句 + TTS 首音，新生成） | **0.7–1.5s** |
| 首句延迟（L1 FAQ 缓存命中） | ~0.1s |
| 整段生成（全句，仅供参考，与"开口"无关） | 中位 4.1s / 均值 4.4s / max 9.5s |

- 首句 0.7–1.5s **远低于 5s**；甚至比云端 localhost（~1.3–2s）略快。
- **诚实口径**：快的那点**主要来自省掉到 DashScope 的网络往返**（本地同机推理），
  **不是 14B 更快**——整段生成本地反而更慢（4.1s vs 云端更快），因量化 14B 逐 token 吞吐低于云端大模型；
  只是"开口"只看第一句、第一句短，占了"无网络"的便宜。
- 本测试为 localhost（不含 ASR/公网/手机渲染下游）；真机端到端再叠加 ASR~1.1s + 网络 + 渲染 ≈ **总 3–4s，仍 <5s**。

## 四、结论

| 维度 | 本地 14B | 判定 |
|---|---|---|
| 准确率 ≥90% | 44/44=100%（同口径） | ✅ 达标 |
| 实时性 <5s（首句开口） | 0.7–1.5s | ✅ 达标 |
| 答案质量上限 / 省心度 | 不及云端大模型、且占 GPU+显存+磁盘 | ⚠️ 云端更优 |

**本地 14B = 真·离线模式，不是"文字降级兜底"，但也不是"吊打云端"**。它够格守住两项硬指标，
价值在**资源可控**（断网 / 无 API 配额 / 数据不出境也能跑）+ **答辩自主可控亮点**。
故方案不变：**云端 qwen-plus 做默认**（质量上限高、零运维），**本地 14B 做兜底**。

## 五、复现

```bash
# AutoDL：起 ollama（模型已就绪，无需重下）
OLLAMA_MODELS=/root/autodl-tmp/ollama OLLAMA_HOST=127.0.0.1:11434 ollama serve &
curl -s localhost:11434/api/generate -d '{"model":"qwen2.5-14b","prompt":"hi","keep_alive":-1,"options":{"num_predict":1}}'  # 固化常驻防卸载
# RAG 切本地后端重启
DEPLOY_MODE=cloud LLM_BACKEND=local LOCAL_LLM_MODEL=qwen2.5-14b LOCAL_LLM_BASE=http://127.0.0.1:11434/v1 \
  python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
# 测准确率(HTTP 打已跑服务，勿 in-process 双开 pipeline) + 首句延迟
python tests/acc_http.py            # 全 4 景区准确率
python tests/lat_test.py            # 首句延迟
```

> 坑：① ollama 默认 keepalive 短，会中途卸载 14B → 测前 `keep_alive:-1` 固化常驻；
> ② in-process 跑 `test_accuracy.py` 会与已运行服务双开 pipeline、抢 GPU 卡死 → 一律 HTTP 打已跑服务。
