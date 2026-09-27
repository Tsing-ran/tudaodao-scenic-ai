#!/usr/bin/env bash
# 方案A·开箱即跑：把 AutoDL 上「完全顺利复现整套前后端」所需的一切备份到网盘。
# 含 conda 运行环境(base+lt) + Ditto模型/TRT引擎 + cudnn8 + SRS + 代码 + 数据 + 队友前端 + SAM。
# 不含：ComfyUI/models(31G 可重下)、echomimic/longcat/infinitetalk 环境(仅生成/已弃用)、.env(密钥手动还原)。
# 用法（在 AutoDL 上跑）: bash backup_to_netdisk.sh <网盘挂载点>
set -u
ND="${1:?用法: $0 <网盘挂载点路径>}"
[ -d "$ND" ] || { echo "挂载点不存在: $ND"; exit 1; }
OUT="$ND/competition_backup_$(date +%Y%m%d_%H%M)"
mkdir -p "$OUT"
R=/root; A=/root/autodl-tmp
TAR(){ echo "→ $1"; shift; tar czf "$@" && echo "  ✓ $(du -h "$1" 2>/dev/null | cut -f1)" || echo "  ✗ 失败"; }

# 1) conda 运行环境（base 跑 RAG + lt 跑 LiveTalking；去 pkgs 缓存 + 弃用 infinitetalk）★最大
TAR "1/9 conda 运行环境(base+lt, ~20G, 较慢)" "$OUT/conda_miniconda3.tgz" \
  --exclude='miniconda3/pkgs' --exclude='miniconda3/envs/infinitetalk' -C $R miniconda3
# 2) Ditto 模型 + TRT 引擎 + SDK（渲染运行时必需）
TAR "2/9 Ditto 模型/TRT引擎(ditto-talkinghead)" "$OUT/ditto_talkinghead.tgz" \
  --exclude='__pycache__' --exclude='*.pyc' -C $A ditto-talkinghead
# 3) cudnn8（TRT 的 LD_LIBRARY_PATH 必需）
TAR "3/9 cudnn8_extracted" "$OUT/cudnn8.tgz" -C $A cudnn8_extracted
# 4) SRS 二进制 + 配置
TAR "4/9 SRS(二进制+conf)" "$OUT/srs.tgz" -C $A srs/trunk/objs/srs srs/trunk/conf
# 5) LiveTalking（引擎代码 + ditto_avatars 形象板 + assets；去 log/缓存）
TAR "5/9 LiveTalking(引擎+形象板)" "$OUT/livetalking.tgz" \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='*.log' -C $A LiveTalking
# 6) Digital_Person（后端代码 + conversations.db + vector_store + dist；去 venv/缓存）
TAR "6/9 Digital_Person(代码+DB+向量库+dist)" "$OUT/digital_person.tgz" \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='.venv' -C $A Digital_Person
# 7) 队友前端（含 dist 可直接服务；去 node_modules 可 npm i 重建）
TAR "7/9 队友前端(digital-human+visitor_web)" "$OUT/teammate_webs.tgz" \
  --exclude='node_modules' -C $R digital-human visitor_web
# 8) 部署/启动脚本（编排胶水）
TAR "8/9 部署脚本(.sh)" "$OUT/deploy_scripts.tgz" $R/*.sh $A/*.sh
# 9) SAM 训练
TAR "9/9 SAM 训练" "$OUT/sam3_sweep.tgz" -C $A sam3_sweep

cp "$A/Digital_Person/RESTORE.md" "$OUT/RESTORE.md" 2>/dev/null
echo "=== 完成 ==="; ls -lah "$OUT"; echo "总计: $(du -sh "$OUT" | cut -f1)"
echo "⚠️ .env(密钥)未备——还原时手动写入 DASHSCOPE_API_KEY；见 RESTORE.md"
