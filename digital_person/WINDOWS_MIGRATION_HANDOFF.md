# Windows / AI_Local 迁移接手说明

更新时间：2026-07-11  
源目录：`/home/jiale/Desktop/Digital_Person`  
目标目录：`/media/jiale/AI_Local/Digital_Person`（Windows 下打开 AI_Local 分区里的 `Digital_Person` 文件夹）

## 迁移目标

这次迁移不是 `git clone`，而是复制当前工作区快照。原因是项目里有大量未提交改动、未跟踪交付材料、图片资源、`.env`、Claude Code/Codex 交接记忆，单纯 clone 会丢失当前进度。

## 必须保留的上下文入口

Windows / WSL 上打开项目后，Claude Code 和 Codex 都应先读这些文件：

1. `CLAUDE.md`：Claude Code 主记忆和多窗口协作公告板。
2. `CODEX_HANDOFF.md`：Codex 接手笔记，包含代码结构、坑点、部署与测试规则。
3. `WINDOWS_MIGRATION_HANDOFF.md`：本迁移说明。
4. `backend/CLAUDE.md`、`docs/CLAUDE.md`、`webapp/CLAUDE.md`：对应目录的局部规则。
5. `.claude/settings.local.json`：Claude Code 本项目权限配置。
6. `.mcp.json`：MCP 服务配置。注意其中有 Linux 绝对路径和本机代理配置，Windows 原生使用时需要改路径；如果在 WSL 里运行，则按 WSL 环境重新安装 node/uvx/Playwright 后调整。

`.codex/` 和 `.agents/` 当前为空目录，但仍会随项目复制，用于保留 Codex/agent 本地约定入口。

## Windows / WSL 开发建议

- 优先在 WSL 中打开项目根目录，避免 Python 依赖、shell 脚本、软链接和路径语义在 Windows 原生环境下不一致。
- `.venv` 是 Linux 环境快照，迁移时会复制，但不应作为 Windows 原生 Python 环境直接使用。建议在 Windows/WSL 重新创建 Python 3.11 环境。
- Python 依赖入口：`requirements.txt`，云端轻量环境可参考 `requirements.cloud.txt`。
- 前端依赖入口：`webapp/package.json` + `webapp/package-lock.json`。
- 打开项目后先运行 `git status --short`，确认当前脏工作区仍完整存在。

## 远端开发注意

- AutoDL 当前记忆路径：`/root/autodl-tmp/Digital_Person`，入口别名通常为 `ssh autodl`。
- AutoDL 服务由 supervisor 管理，演示前需确认当前 seetacloud 公网 token，因为 token 会轮换。
- 旧记忆中提到阿里云 ECS `116.62.136.211` 已被标记为弃用；如果后续重新启用 ECS，需要先确认新的 ECS 地址、部署路径和 systemd/supervisor 管理方式，再更新本文件和 `CLAUDE.md`。

## 迁移校验口径

迁移完成后至少确认：

- 目标目录存在 `.git`、`.env`、`.claude/`、`.mcp.json`、`CLAUDE.md`、`CODEX_HANDOFF.md`。
- 目标目录 `git status --short` 能看到与源目录一致的大量未提交/未跟踪改动。
- `du -sh` 体积接近源目录。源目录当前约 7.4G，其中 `.venv` 约 6.1G。
- 不要在确认迁移成功前删除或清理源目录。

## 本次执行结果

2026-07-11 已完成整目录迁移到 `AI_Local`：

- 复制命令：`rsync -aH --no-owner --no-group --modify-window=1 ./ /media/jiale/AI_Local/Digital_Person/`。
- `rsync` 退出码：0。
- 源目录与目标目录体积：均为约 7.4G。
- 文件结构计数一致：6650 个目录、69369 个普通文件、31 个软链接。
- 关键记忆文件均存在于目标目录：`.git`、`.env`、`.claude/settings.local.json`、`.mcp.json`、`CLAUDE.md`、`CODEX_HANDOFF.md`、`WINDOWS_MIGRATION_HANDOFF.md`、各子目录 `CLAUDE.md`。
- 源目录与目标目录 `git status --short` 均为 99 条，说明未提交/未跟踪工作区状态已保留。
- `rsync --dry-run --itemize-changes` 只提示 `.agents/`、`.codex/` 两个空目录的时间/权限元数据差异；内容没有缺失。
