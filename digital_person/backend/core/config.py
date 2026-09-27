from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # DashScope (通义千问)
    dashscope_api_key: str = ""
    # qa（事实问答）用模型。qwen-plus 比 qwen-max 生成快 ~2 倍（48 vs 20 字/s），
    # 流式首句从 ~3s 降到 ~1.2s，是压住语音端到端 <5s 的关键；44 题准确率 100%
    # （keyword 自测），事实由 RAG context 约束，质量足够。生成性意图另走 fast_model。
    llm_model: str = "qwen-plus"
    # 生成性意图/改写/意图分类用快模型。qwen-flash = qwen-turbo 的同代继任（更快更省）。
    # ⚠️ qwen-turbo 与 qwen-vl-max 均于 2026-07-13 下线 → 已迁至 qwen-flash / qwen3-vl-plus
    # （本 key 实测可直连 200；-latest 及带日期版仍 403，故用滚动稳定别名）。
    fast_model: str = "qwen-flash"
    vl_model: str = "qwen3-vl-plus"

    # 文本 LLM 后端：cloud（DashScope，默认）| local（本地模型，离线兜底 + 自主可控答辩亮点）。
    # local 走 OpenAI 兼容端点（Ollama :11434/v1 或 vLLM）；qa 事实由 RAG context 约束，
    # 本地 7-14B 即可。云端路径不受影响（仅 llm_backend=local 时切走）。VL 多模态仍走云。
    llm_backend: str = "cloud"          # cloud | local
    local_llm_base: str = "http://localhost:11434/v1"
    local_llm_model: str = "qwen2.5:7b-instruct"

    # 部署模式：local（本地GPU）或 cloud（阿里云，用DashScope Embedding）
    deploy_mode: str = "local"

    # 本地模型（deploy_mode=local 时使用）
    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"

    # ASR（本地 faster-whisper；CPU 运行不抢数字人显存）
    asr_provider: str = "auto"      # auto=云端qwen3-asr优先失败落本地 / cloud=仅云端 / local=仅本地
    asr_cloud_model: str = "qwen3-asr-flash"   # 口音普通话/方言/多语种识别大模型（0显存，与LLM共用Key）
    asr_cloud_timeout: float = 4.5  # 云端超时(秒)：超过即落回本地whisper，保住语音链路时延预算
    asr_model: str = "small"        # 实测 small CPU ~1.1s 达标；medium 在本机 RTF≈2 太慢
    asr_device: str = "cpu"         # cpu：0 显存占用，把 4080 整块显存留给数字人(MuseTalk)
    asr_compute: str = "int8"       # int8：CPU 上最快
    asr_cpu_threads: int = 4        # 实测本机 4 线程最快（大小核架构，过多线程反增调度开销）
    asr_beam_size: int = 1          # 贪心解码；短问答足够，比 beam=5 快约 30%

    # RAG 参数
    chunk_size: int = 512
    chunk_overlap: int = 128
    dense_top_k: int = 10
    sparse_top_k: int = 10
    rerank_top_k: int = 4

    # EA-RAG 自研检索算法（Entity-Anchored Adaptive RAG）三机制开关
    # 全部可经环境变量覆盖，供消融实验逐项开关
    ea_entity_anchor: bool = True      # ① 实体锚定：query 命中景点名 → 该景点 chunk 加权
    ea_adaptive_fusion: bool = True    # ② 自适应融合：按 query 特征动态调 dense/sparse 权重的加权 RRF
    ea_confidence_gate: bool = True    # ③ 置信度门控：reranker top1 低于阈值 → 判定知识库无此信息
    # 门控阈值：经 105 正常题 + 库外陷阱题标定（tests/ea_rag_stress.json），
    # 0.2 = 库外拒答 60% 且正常题误拒 0% 的最优工作点（0.3 起出现 1% 误拒）
    ea_gate_threshold: float = 0.2

    # 路径
    vector_store_dir: Path = BASE_DIR / "vector_store"
    knowledge_base_dir: Path = BASE_DIR / "knowledge_base"

    class Config:
        env_file = BASE_DIR / ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
