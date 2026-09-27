#!/bin/bash
# 防 OOM：T5 文本编码器(11GB)只在编码提示词时用一次，留 CPU 即可，省出 GPU 给 DiT 采样。
# patch1: pipeline 用 text_encoder 自身 device 跑（下一行本就把 embeds .to(device)）
# patch2: demo 在 pipe.to(cuda) 后把 text_encoder 移回 CPU
cd /root/autodl-tmp/phase0/LongCat-Video || exit 9
/root/autodl-tmp/envs/longcat/bin/python - <<'PY'
p1 = "longcat_video/pipeline_longcat_video_avatar.py"
s = open(p1).read()
old = "self.text_encoder(text_input_ids.to(device), mask.to(device))"
new = "self.text_encoder(text_input_ids.to(self.text_encoder.device), mask.to(self.text_encoder.device))"
if old in s:
    s = s.replace(old, new); open(p1, "w").write(s); print("patch1 OK")
else:
    print("patch1: not found / already")

p2 = "run_demo_avatar_single_audio_to_video.py"
s = open(p2).read()
old2 = "    pipe.to(local_rank)\n"
new2 = "    pipe.to(local_rank)\n    pipe.text_encoder.to('cpu')  # T5(11GB)留CPU省显存防OOM\n"
if "text_encoder.to('cpu')" not in s and old2 in s:
    s = s.replace(old2, new2, 1); open(p2, "w").write(s); print("patch2 OK")
else:
    print("patch2: not found / already")
PY
echo "=== verify ==="
grep -nc "self.text_encoder.device" longcat_video/pipeline_longcat_video_avatar.py
grep -n "text_encoder.to('cpu')" run_demo_avatar_single_audio_to_video.py
echo "=== OFFLOAD PATCH DONE ==="
