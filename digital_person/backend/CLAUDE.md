# 后端域规范（backend/ bridge/ scripts/）——窗口①全栈主力的主场

> 窗口划分见根 CLAUDE.md「多窗口协作协议」：窗口①是**唯一服务/GPU 管理者**，且默认兼管前端
> （除非进度日志有 `【前端窗口启用中】` 登记）。进度日志只追加不改写，干完一块立刻写。
> 启动/部署命令的权威版本在根 CLAUDE.md，勿在此重复维护。

## 边界

- ✅ 本域：`backend/`、`bridge/`、`scripts/`、`tests/`、`deploy/`、`~/Desktop/LiveTalking`（引擎改造）
- ✅ 前端 `webapp/ miniprogram/` 默认也可动（动时遵守 `webapp/CLAUDE.md` 域规范）；
  若进度日志有 `【前端窗口启用中】`，则前端交给窗口③、本窗口不碰
- ❌ 不碰：`docs/`（窗口②文档交付的地盘）
- ✅ **服务唯一管理权在此**：RAG :8000、桥接 :9000、LiveTalking :8010、SRS docker、
  ComfyUI :8188 的启停只在这里做。**GPU 任务必须串行**（11.6G：跑烘录/EchoMimic/ComfyUI 前
  先确认 LiveTalking 已停，反之亦然；进程清零再启下一个）。

## 环境铁律

- Python 一律 `.venv/bin/python`（uv 管理、**没有 pip 可执行文件**，装包用
  `~/.local/bin/uv pip install X --python .venv/bin/python -i https://pypi.tuna.tsinghua.edu.cn/simple`）。
- 调外网（DashScope/wttr）前 `unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy`。
- DashScope 模型用稳定版（`qwen-max`/`qwen-plus`/`qwen-vl-max`），`-latest` 全 403。
- 本地起 RAG 用 `DEPLOY_MODE=cloud`（DashScope 嵌入 0 显存，把 GPU 留给数字人）。
- LiveTalking Ditto 引擎必须 `LD_LIBRARY_PATH=~/Desktop/cudnn8/nvidia/cudnn/lib`（TRT 要 cuDNN8）。

## 改动纪律

- 改 SQLite 表结构：用 `backend/db/database.py` 的 `_ensure_columns` 幂等迁移，**不许手写裸 ALTER**
  （ECS 上有存量库）。
- 改对外接口（/chat、/digital-human/*、/live/*…）：同步更新 `API_DOC.md` 对应章节——这是
  与前端窗口的契约文件，前端只认它。
- 测试是 `tests/` 下的**独立脚本**（非 pytest），跑法 `.venv/bin/python tests/test_xxx.py`；
  新接口至少配一个 roundtrip 脚本。
- 语音/TTS 链路的验证必须落到**可听见的声音**（ffmpeg volumedetect 查 dB），只看日志会漏静音故障。
- 改动可能影响准确率（RAG/prompt/检索参数）时，提交前跑 `tests/test_accuracy.py lingshan` 抽测。

## 部署提醒

ECS 按时长计费——部署/验证 ECS 前先问用户要不要开机；本地演示全栈不需要 ECS。
部署命令见根 CLAUDE.md「云端服务维护手册」。
