#!/bin/bash
# 一键重部署「大屏游客端 kiosk（途叨叨）」到杭州网关公网 /kiosk/
#
# 流程：AutoDL 构建(base=/kiosk/) → tar → 杭州 :/var/www/kiosk/（原子替换）→ 公网验证
# 入口：https://114.55.178.51:8443/kiosk/（免隧道）
#
# 用法：bash scripts/deploy_kiosk.sh
# 依赖：本机 ~/.ssh/config 里的 autodl + hz 两个别名都通（kiosk 源码在 AutoDL /root/visitor_web）。
# 说明：公网这份是静态 dist（非 vite dev），改完 kiosk 代码必须跑本脚本才生效；
#       vite dev :5173 是开发热更新用、走隧道，与本脚本互不影响。
set -euo pipefail

KIOSK_DIR=/root/visitor_web
GATEWAY=https://114.55.178.51:8443

echo "[1/3] AutoDL 构建 kiosk（base=/kiosk/，直接 vite build 跳过类型门）..."
# 远端开 pipefail，vite 失败能透回本机 set -e（否则 | tail 吞掉退出码）
ssh autodl "set -o pipefail; cd $KIOSK_DIR && ./node_modules/.bin/vite build --base=/kiosk/ 2>&1 | tail -4"

echo "[2/3] 打包 → 推送杭州 /var/www/kiosk/（原子替换，零半成品窗口）..."
ssh autodl "tar czf /tmp/kiosk_dist.tgz -C $KIOSK_DIR/dist ."
ssh autodl 'cat /tmp/kiosk_dist.tgz' | ssh hz '
  rm -rf /var/www/kiosk.new && mkdir -p /var/www/kiosk.new &&
  tar xzf - -C /var/www/kiosk.new &&
  rm -rf /var/www/kiosk && mv /var/www/kiosk.new /var/www/kiosk &&
  echo "  已替换 /var/www/kiosk（$(ls /var/www/kiosk | wc -l) 个顶层条目）"'

echo "[3/3] 公网验证..."
page=$(curl -sk --noproxy '*' -o /dev/null -w '%{http_code}' "$GATEWAY/kiosk/")
asset=$(curl -sk --noproxy '*' "$GATEWAY/kiosk/" | grep -oE '/kiosk/assets/index-[^"]*\.js' | head -1)
acode=$(curl -sk --noproxy '*' -o /dev/null -w '%{http_code}' "$GATEWAY$asset")
echo "  page=$page  asset=$asset ($acode)"
if [ "$page" = "200" ] && [ "$acode" = "200" ]; then
  echo "✅ kiosk 已更新上线：$GATEWAY/kiosk/"
else
  echo "❌ 验证失败（page=$page asset=$acode），检查 nginx / dist"; exit 1
fi
