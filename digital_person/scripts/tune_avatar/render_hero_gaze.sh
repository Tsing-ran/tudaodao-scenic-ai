#!/bin/bash
# 眼神修复版英雄镜头一键渲染（等 GPU 空了再跑）。
# 用 prompt 强对视约束治 EchoMimic 眼球上飘（几何改眼睛的土办法已废弃—会糊眼皮）。
# 前置：GPU 空闲；ComfyUI/input/ 已有 sweet_bob_portrait_23.png(干净源) + hero.wav。
set -e
cd /home/jiale/Desktop/ComfyUI
unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy

# ① ComfyUI 没起就起（精确判断 8188）
if ! curl -s -m3 http://127.0.0.1:8188/object_info >/dev/null 2>&1; then
  echo "启动 ComfyUI…"
  nohup /home/jiale/Desktop/comfy_venv/bin/python main.py --port 8188 > /tmp/tune/comfy_gaze.log 2>&1 &
  for i in $(seq 1 30); do curl -s -m3 http://127.0.0.1:8188/object_info >/dev/null 2>&1 && break; sleep 2; done
fi
echo "ComfyUI 就绪，开始渲染眼神修复版…"

# ② 渲染（眼神预补偿参考图 + 修订 prompt 已在 run_echomimic.py 里）
cd /home/jiale/Desktop/Digital_Person
.venv/bin/python scripts/run_echomimic.py sweet_bob_portrait_23.png hero.wav /tmp/tune/echomimic_hero_gaze.mp4 33 300
echo "完成 → /tmp/tune/echomimic_hero_gaze.mp4"
