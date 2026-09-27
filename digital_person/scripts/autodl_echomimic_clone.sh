#!/bin/bash
# 阶段0：克隆 EchoMimicV2 代码仓（用 AutoDL 学术加速）。仅克隆+打印配置，不下权重。
set -e
source /etc/network_turbo 2>/dev/null || true
cd /root/autodl-tmp/phase0
if [ ! -d echomimic_v2/.git ]; then
  rm -rf echomimic_v2
  git clone --depth 1 https://github.com/antgroup/echomimic_v2
fi
echo "=== CLONE DONE ==="
echo "=== infer_acc.yaml ==="
cat echomimic_v2/configs/prompts/infer_acc.yaml 2>/dev/null || echo "(no infer_acc.yaml)"
echo "=== configs dir ==="
ls echomimic_v2/configs/prompts/
echo "=== pose templates ==="
ls echomimic_v2/assets/halfbody_demo/pose/ 2>/dev/null | head
echo "=== refimag ==="
ls echomimic_v2/assets/halfbody_demo/refimag/ 2>/dev/null | head
echo "=== pretrained_weights paths referenced in code ==="
grep -rhoE "pretrained_weights/[A-Za-z0-9_./-]+" echomimic_v2/*.py echomimic_v2/configs/prompts/*.yaml 2>/dev/null | sort -u
echo "=== ALL DONE ==="
