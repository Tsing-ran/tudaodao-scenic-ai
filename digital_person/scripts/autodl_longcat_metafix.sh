#!/bin/bash
# 加速核心：int8 loader 原本用真权重实例化 13.6B 模型(fp32 RNG 初始化~54GB,几十分钟),
# 而所有权重随即被 load_state_dict 覆盖 → 用 accelerate.init_empty_weights() 走 meta 设备
# (零分配、瞬时) + load_state_dict(assign=True)。失败则快速报错、回退慢路径。
echo "=== kill current render (literal PIDs) ==="
for pid in $(ps -eo pid,cmd | grep -E "run_demo_avatar|render_full.sh|autodl_longcat_render.sh|torchrun" | grep -v grep | awk '{print $1}'); do kill -9 "$pid" 2>/dev/null && echo "killed $pid"; done
sleep 4
cd /root/autodl-tmp/phase0/LongCat-Video || exit 9
cp -n longcat_video/modules/quantization.py longcat_video/modules/quantization.py.bak
/root/autodl-tmp/envs/longcat/bin/python - <<'PY'
p = "longcat_video/modules/quantization.py"
s = open(p).read()
if "init_empty_weights" not in s:
    s = s.replace("from safetensors.torch import save_file, load_file",
                  "from safetensors.torch import save_file, load_file\nfrom accelerate import init_empty_weights")
    s = s.replace("    model = LongCatVideoAvatarTransformer3DModel(**config)\n",
                  "    with init_empty_weights():\n        model = LongCatVideoAvatarTransformer3DModel(**config)\n")
    s = s.replace("model.load_state_dict(state_dict, strict=True)",
                  "model.load_state_dict(state_dict, strict=True, assign=True)")
    open(p, "w").write(s)
    print("PATCHED")
else:
    print("ALREADY PATCHED")
PY
echo "=== verify ==="; grep -nE "init_empty_weights|assign=True" longcat_video/modules/quantization.py
echo "=== METAFIX DONE ==="
