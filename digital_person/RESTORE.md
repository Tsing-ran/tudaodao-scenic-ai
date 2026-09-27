# 比赛作品·整套系统还原手册（方案A·开箱即跑）

> 适用：在一台**全新/重置的 AutoDL 实例**上，从网盘备份完整复现前后端系统。
> 备份脚本：`scripts/backup_to_netdisk.sh`（在旧实例上跑，产物落网盘 `competition_backup_<日期>/`）。

## 0. 前置
- **同款 AutoDL 镜像**（4090D / 同 CUDA 驱动）——conda 环境与 TRT 引擎依赖此一致性。
- 把网盘挂到新实例（控制台「文件存储」挂载），记挂载点 `$ND`。
- 准备好 `DASHSCOPE_API_KEY`（密钥不在备份里）。

## 1. 解包（各归原路径）
```bash
ND=<网盘挂载点>/competition_backup_<日期>
R=/root; A=/root/autodl-tmp
tar xzf $ND/conda_miniconda3.tgz   -C $R          # → /root/miniconda3 (base 跑 RAG + envs/lt 跑 LiveTalking)
tar xzf $ND/ditto_talkinghead.tgz  -C $A          # → ditto-talkinghead (Ditto 模型+TRT引擎)
tar xzf $ND/cudnn8.tgz             -C $A          # → cudnn8_extracted (TRT 必需)
tar xzf $ND/srs.tgz                -C $A          # → srs/trunk/objs/srs + conf
tar xzf $ND/livetalking.tgz        -C $A          # → LiveTalking (引擎+ditto_avatars 形象板)
tar xzf $ND/digital_person.tgz     -C $A          # → Digital_Person (后端代码+DB+向量库+dist)
tar xzf $ND/teammate_webs.tgz      -C $R          # → digital-human + visitor_web
tar xzf $ND/deploy_scripts.tgz     -C /          # → /root/*.sh + /root/autodl-tmp/*.sh
tar xzf $ND/sam3_sweep.tgz         -C $A          # → sam3_sweep
```

## 2. 还原密钥（不在备份内）
```bash
echo "DASHSCOPE_API_KEY=<你的key>" > /root/autodl-tmp/Digital_Person/.env
```

## 3. 队友前端依赖（如需重新构建）
dist 已在备份里、可直接被桥接服务；要改源码再 build 时：
```bash
cd /root/digital-human/frontend && npm install   # 同理 /root/visitor_web
```

## 4. 起服务
```bash
bash /root/start_all.sh        # 拉起 RAG(:8000) + LiveTalking(16:9 :8010 / 9:16 :8011) + SRS + 桥接(:6006)
```
- LiveTalking 启动需 `LD_LIBRARY_PATH=/root/autodl-tmp/cudnn8_extracted/...`（TRT 要 cuDNN8）——已在 `lt_run*.sh` 内。
- 进程**非常驻**：实例重启后都要重跑 `start_all.sh`。

## 5. 验证
```bash
curl -s localhost:8000/health                                   # RAG
curl -s localhost:6006/live/health                              # 桥接(rag+livetalking)
curl -s localhost:1985/api/v1/streams/                          # SRS 推流 active
# 公网网关 https://<实例>:8443/  游客端、/admin 管理端、/rag/* 后端
```
- 形象热切：`curl -X POST localhost:6006/live/avatar -d '{"avatar_id":"dh_lingshan","scenic_id":"lingshan","sessionid":"0","screen":"main"}'`
- 景区默认形象在 `conversations.db`（已随备份还原）。

## 备份里有什么 / 没什么
- **有**：conda 运行环境(base+lt) / Ditto 模型+TRT引擎 / cudnn8 / SRS / 全部代码 / DB+向量库 / 形象板(256+) / 队友前端 / 部署脚本 / SAM。
- **没有（需另处理）**：`.env` 密钥（手动写）；ComfyUI/models 31G（仅形象生成需要，官方可重下）；echomimic/longcat/infinitetalk 环境（仅生成/已弃用）；node_modules（npm install 重建）。

详细启动命令/踩坑见根 `CLAUDE.md` 与 `livetalking_engine/README.md`。
