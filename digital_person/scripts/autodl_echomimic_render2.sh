#!/bin/bash
# 补 sd-image-variations 的 unet/（infer 需要 subfolder=unet）。
# 巧法：base unet 权重会被 reference_unet.pth/denoising_unet.pth 完全覆盖（都是完整 SD1.5-arch state_dict），
# 故只下 tiny config.json，权重文件用 reference_unet.pth 自身充当 → 省掉 3.4GB 慢下载。然后渲染。
cd /root/autodl-tmp/phase0/echomimic_v2 || exit 9
ENV_DIR=/root/autodl-tmp/envs/echomimic
export PIP_CACHE_DIR=/root/autodl-tmp/pipcache TMPDIR=/root/autodl-tmp/tmp HF_ENDPOINT=https://hf-mirror.com
PY="$ENV_DIR/bin/python"
UD=pretrained_weights/sd-image-variations-diffusers/unet
echo "=== fetch unet/config.json ==="
$PY -c "
from huggingface_hub import hf_hub_download
import shutil,os
p=hf_hub_download('lambdalabs/sd-image-variations-diffusers','unet/config.json',local_dir='/tmp/sdiv')
d='$UD'; os.makedirs(d,exist_ok=True); shutil.copy(p, d+'/config.json'); print('config.json ok ->',d)
"
if [ ! -f "$UD/diffusion_pytorch_model.bin" ] && [ ! -f "$UD/diffusion_pytorch_model.safetensors" ]; then
  cp pretrained_weights/reference_unet.pth "$UD/diffusion_pytorch_model.bin" && echo "seeded unet weights from reference_unet.pth"
fi
ls -la "$UD"
echo "=== RENDER START ==="; date
export FFMPEG_PATH=/usr/bin PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
$PY infer.py --config configs/prompts/infer.yaml -W 768 -H 768 -L 144 --steps 30 --cfg 2.5 --fps 24 \
  --refimg_name natural_bk_openhand/0035.png --audio_name chinese/phase0_short.wav --pose_name 01
echo "=== RENDER EXIT=$? ==="; date
find outputs -name "*.mp4" -printf "%T+ %s %p\n" 2>/dev/null | sort | tail -3
echo "=== RENDER2 DONE ==="
