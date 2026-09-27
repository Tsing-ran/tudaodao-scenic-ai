#!/bin/bash
# 防 OOM 兜底：480p(480x832) 降到 384x640（面积 0.62x，省激活显存；也利于后期视频流防卡顿）。
# 384/16=24, 640/16=40，满足 patch_size/vae_scale 整除。
cd /root/autodl-tmp/phase0/LongCat-Video || exit 9
/root/autodl-tmp/envs/longcat/bin/python - <<'PY'
p = "run_demo_avatar_single_audio_to_video.py"
s = open(p).read()
if "height, width = 480, 832" in s:
    s = s.replace("height, width = 480, 832", "height, width = 384, 640")
    open(p, "w").write(s); print("LOWRES 480x832 -> 384x640 OK")
else:
    print("480p line:", [l for l in s.splitlines() if "height, width" in l][:3])
PY
grep -n "384, 640" run_demo_avatar_single_audio_to_video.py
echo "LOWRES PATCH DONE"
