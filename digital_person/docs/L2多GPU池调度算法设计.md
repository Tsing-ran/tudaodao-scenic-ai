# L2 多 GPU 池调度算法设计

> 规模化方案 L2 层（GPU 池按发话共享）的算法详细设计。本文界定问题特征 → 横评算法族 →
> 给出分层调度器 → 用排队论做容量规划（带算例）→ 弹性伸缩 → 诚实边界。对标工业界
> （Triton / vLLM / Ray Serve）与学术界成果，并映射到本系统已落地的 `AvatarPool` 抽象。

---

## 1 问题界定：我们的调度为何不能照搬通用负载均衡

把"实时数字人渲染"的调度问题与常见的无状态 Web / LLM 推理对比，有四个使它**特殊**的特征：

| 特征 | 本系统 | 对调度的影响 |
|---|---|---|
| **任务粒度** | 一次"发话"渲染 ≈ 10–20s 实时 MuseTalk（长任务，非毫秒级）| 单任务久 → 队列等待对尾延迟敏感，需排队论精算 |
| **到达过程** | 稀疏 + 突发（游客问→沉默 1–2min）| 高变异性 → Erlang-C 告诉我们要留远超均值的余量 |
| **SLA** | 首帧开口 <5s | 调度目标 = 最小化"分配到空闲 GPU"的等待 |
| **状态/亲和** | GPU 装载某 avatar 有冷启动成本；不同景区用不同 avatar | **亲和 vs 均衡的经典张力**——同景区请求该粘到已热 GPU |

此外本系统已有**准入前置**：L1 命中→不进 GPU、池满→L3 降级。**故调度器只处理"必须实时渲染"的那一小撮请求**，问题规模已被前两层大幅削减。还有一个别人没有的优势——**我们有真实客流数据**（`analytics` 行为数据 + 时段模型），可做**预测式**伸缩。

---

## 2 算法族横评（工业界 + 学术界）

### 2.1 分发策略（请求 → 哪块 GPU）
| 算法 | 原理 | 用于本系统的取舍 |
|---|---|---|
| Round-Robin / 随机 | 轮流/随机派发 | 简单但忽略负载与 avatar 热度，长任务下尾延迟差 |
| **Join-Shortest-Queue (JSQ)** | 派给当前最短队列 | 近优，但要全局实时负载、协调开销大；且**无视 avatar 热度**（可能每次落到冷 GPU） |
| **Power-of-Two-Choices (Po2C)** | 随机选 2 个，派给较空者 | 最大负载从 Θ(log n) 降到 **Θ(log log n)**，协调开销极小；研究指出 **d=2 还能保住缓存局部性**（取更多反而打散热度）|
| **一致性哈希 + 有界负载 (CHBL)** | 按 key 哈希到固定 GPU（亲和），但单机负载封顶（如 ≤1.25×均值），超限溢出到下一个 | Google/Vimeo 生产算法；**同时拿到亲和与均衡**，正是 avatar 热度问题的解 |

> 学术界最新（DualMap：为分布式 LLM serving 同时做 **cache 亲和 + 负载均衡**）印证了这条路线——纯亲和会在热点景区下产生 hotspot，纯均衡会丢失 avatar 热度，**CHBL/Po2C 的组合是甜点**。

### 2.2 单机队列内调度
- **FIFO**：任务时长相近(~15s)且首帧已快速流式回传，FIFO 足够；准入层已削峰。
- **EDF（最早截止优先）**：当混合优先级（如"实时对话流" > "离线预渲染批作业"）时按 <5s 截止排序。

### 2.3 批处理（关键诚实点）
- LLM serving 的杀手锏是 **continuous batching**（vLLM/Orca：解码 token 级跨请求拼批，throughput↑24×）。
- **但实时数字人不适用跨用户拼批**：每个用户是独立的"音频→帧"流，不能像 LLM 解码那样合并。MuseTalk 的 batch 仅在**单用户帧内**（已用 `batch_size=4`）。
- **∴ L2 的增益来自"时分复用"（multiplexing）而非"拼批"**——这是与 LLM 调度最本质的不同，必须诚实写明，否则是外行。

### 2.4 自动伸缩
- **反应式**：按队列长度/等待时间阈值扩、低利用率缩、闭园**缩到 0**。
- **预测式**：按负载曲线提前预热（Aladdin 用 bin-packing 求满足 SLO 的最小成本配置，报告省 71% GPU）。
- **冷启动**：扩容慢（载 MuseTalk+avatar 数十秒）→ 留 N_min 热机 + 预载各景区默认 avatar（类 BLITZSCALE 的 O(1) 主机缓存思想）。

---

## 3 推荐调度器：分层设计

```
发话请求
  │
  ├─ L0 准入（已落地）：L1缓存命中→0 GPU返回 ; 池满→L3降级文字
  │      ↓ 仅"必须渲染"的请求进入
  ├─ L1 分发：CHBL(key=scenic/avatar_id) 选候选热机
  │           候选内若负载超界 → Po2C(d=2,取较空) 溢出
  │      ↓
  ├─ L2 单机队列：FIFO（混优先级时 EDF，<5s 截止）
  │      ↓
  ├─ L3 渲染：MuseTalk 单用户帧内 batch；首句抢跑流式回传(<5s开口)
  │      ↓ 说完估算时长后释放槽位（已落地 AvatarPool.release_after）
  └─ L4 伸缩：预测式(客流曲线预热) + 反应式(队列阈值) + 闲时缩零
```

**一句话策略**：**CHBL 保 avatar 亲和（省冷启动）、有界负载 + Po2C 防热点（保均衡）、FIFO/EDF 守 <5s、时分复用而非拼批、客流预测驱动弹性伸缩。**

---

## 4 容量规划：用排队论精算 GPU 数（带算例）

把 GPU 池建模为 **M/G/c 队列**：泊松到达率 λ（发话/秒）、服务时长 S（均值 ≈15s）、c 块 GPU。

**offered load（厄朗）**：
$$
a = \lambda \cdot \overline{S} \quad(\text{单位：Erlang}),\qquad \text{利用率 } \rho = a/c
$$

**Erlang-C** 给出"需排队的概率"与期望等待，据此反解满足 **p95 等待 < 1s**（叠加 ~3s 流水线 → 端到端 <5s）所需的最小 c。

### 算例（展示 L1 缓存如何直接砍 GPU 数）
设某景区高峰 **λ = 1 发话/秒**、S = 15s：
- **无 L1 缓存**：a = 15 Erlang → 要 p95 低等待，Erlang-C 需 **c ≈ 19–20 块 GPU**。
- **有 L1 缓存（命中率 50%）**：实际进 GPU 的 λ′ = 0.5/s → a = 7.5 Erlang → **c ≈ 10–11 块**。
- **再叠 L3 削峰**（极端高峰那 5% 降级文字）：峰值 λ 进一步下削，c 还可降。

> 结论量化了三层漏斗的价值：**L1 把所需 GPU 数砍掉约一半，L3 削掉峰值尾部**。

⚠️ **突发修正**：到达突发 + S 高变异时，M/M/c 会**低估尾延迟**，需用**两矩 M/G/c 近似**；研究指出极端突发负载可能要 **8× 于平滑负载**的容量。故实际按**峰值小时 λ + 变异系数**留余量，宁可弹性多备、闲时缩零。

---

## 5 弹性伸缩：预测式（我们的差异化优势）+ 反应式

1. **预测式（核心优势）**：用已有 `analytics` 客流数据（真实 14 万行行为 + 时段/季节模型）**预测每小时 λ** → Erlang-C 反解 c → **提前预热**对应数量 GPU，把冷启动（数十秒）藏在需求到来之前。这是通用系统没有的"先知"能力。
2. **反应式兜底**：队列等待 > 阈值即扩；利用率持续低即缩。
3. **缩到 0**：景区闭园时段池缩零，成本归零。
4. **冷启动缓解**：保 N_min 热机 + 每景区默认 avatar 常驻其亲和 GPU。

---

## 6 与已落地组件的对接

- 现有 `AvatarPool`（单节点 `in_use/size` 槽位 + `release_after` 按说话时长释放）是 **c=1 的特例**；多节点版只需把"本地计数"换成**池级状态**（Redis/etcd 记各 GPU 负载与 avatar 热度），分发层套 CHBL+Po2C。
- 现有 `GET /live/capacity` 即池级观测的雏形，扩展为每 GPU 负载/热度上报。
- 现有 `analytics/event`（发话埋点）正是预测式伸缩的 λ 数据源——**数据闭环已就位**。

---

## 7 诚实的边界

- 实时数字人**不能跨用户拼批**（§2.3），L2 增益来自时分复用，规模上限仍受单卡实时渲染吞吐约束。
- 多节点 CHBL/Po2C + 池级状态 + 预测伸缩属**规模化阶段工程**，当前落地的是单节点 `AvatarPool` 抽象 + 降级，已为多节点预留接口。
- Erlang-C 假设泊松到达，真实景区到达更突发，需用真实数据持续校准 λ 与 CV。

---

## 参考来源
- [Consistent Hashing with Bounded Loads (Mirrokni & Thorup, arXiv:1608.01350)](https://arxiv.org/pdf/1608.01350) — 亲和+有界负载
- [改进负载均衡的一致性哈希算法 (Vimeo Engineering)](https://medium.com/vimeo-engineering-blog/improving-load-balancing-with-a-new-consistent-hashing-algorithm-9f1bd75709ed)
- [DualMap: Cache Affinity + Load Balancing for Distributed LLM Serving (arXiv:2602.06502)](https://arxiv.org/pdf/2602.06502)
- [The Power of Two Choices with Simple Tabulation (arXiv:1407.6846)](https://arxiv.org/pdf/1407.6846)
- [inference-fleet-sim: Queueing-Theory Capacity Planner for LLM Inference (arXiv:2603.16054)](https://arxiv.org/pdf/2603.16054) — Erlang-C/M/G/c 容量规划
- [From Models to Operators: Rethinking Autoscaling Granularity (arXiv:2511.02248)](https://arxiv.org/pdf/2511.02248)
- [LLM Inference Scheduling: A Survey (techrxiv, 2025)](https://www.techrxiv.org/users/994660/articles/1355915) — 调度技术综述
- [Load Balancing for AI Inference (Introl)](https://introl.com/blog/load-balancing-ai-inference-distributing-requests-1000-gpus) — 动态批处理/调度工程实践
