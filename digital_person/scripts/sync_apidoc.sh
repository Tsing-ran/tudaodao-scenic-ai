#!/bin/bash
# 把最新 API_DOC.md 推到 AutoDL，前端队友刷新 https://<autodl>:8443/api-doc 即见最新。
# 用法：bash scripts/sync_apidoc.sh   （依赖 ~/.ssh/config 里的 autodl 别名）
cd "$(dirname "$0")/.." || exit 1
scp API_DOC.md autodl:/root/autodl-tmp/Digital_Person/API_DOC.md \
  && echo "✅ API_DOC.md 已同步到 AutoDL，队友刷新 /api-doc 即最新" \
  || echo "❌ 同步失败（确认 ssh autodl 通、AutoDL 在线）"
