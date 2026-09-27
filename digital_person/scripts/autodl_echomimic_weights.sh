#!/bin/bash
# 阶段0：下载 EchoMimicV2 标准 infer.py 所需权重（只下需要的，省盘省时）。
# 走 hf-mirror；whisper tiny.pt 多源兜底。不占 GPU。
set -e
export HF_ENDPOINT=https://hf-mirror.com
cd /root/autodl-tmp/phase0/echomimic_v2
mkdir -p pretrained_weights/audio_processor
PY=/root/miniconda3/bin/python
$PY -m pip install -q -U "huggingface_hub[hf_transfer]" >/dev/null 2>&1 || true
export HF_HUB_ENABLE_HF_TRANSFER=1

echo "=== 1) EchoMimicV2 核心 4 权重 ==="
$PY - <<'PYEOF'
from huggingface_hub import hf_hub_download
for f in ['denoising_unet.pth','reference_unet.pth','pose_encoder.pth','motion_module.pth']:
    p = hf_hub_download('BadToBest/EchoMimicV2', f, local_dir='pretrained_weights')
    print('OK', f, flush=True)
PYEOF

echo "=== 2) sd-vae-ft-mse ==="
$PY - <<'PYEOF'
from huggingface_hub import snapshot_download
snapshot_download('stabilityai/sd-vae-ft-mse',
    local_dir='pretrained_weights/sd-vae-ft-mse',
    allow_patterns=['config.json','diffusion_pytorch_model.safetensors','diffusion_pytorch_model.bin'])
print('OK vae', flush=True)
PYEOF

echo "=== 3) sd-image-variations (image_encoder 等) ==="
$PY - <<'PYEOF'
from huggingface_hub import snapshot_download
snapshot_download('lambdalabs/sd-image-variations-diffusers',
    local_dir='pretrained_weights/sd-image-variations-diffusers',
    allow_patterns=['model_index.json','image_encoder/*','feature_extractor/*','scheduler/*'])
print('OK sd-image-variations', flush=True)
PYEOF

echo "=== 4) whisper tiny.pt (多源兜底) ==="
TPT=pretrained_weights/audio_processor/tiny.pt
if [ ! -s "$TPT" ]; then
  $PY - <<'PYEOF' || true
from huggingface_hub import hf_hub_download
import shutil
for repo, fn in [('BadToBest/EchoMimic','audio_processor/tiny.pt'),
                 ('Codys12/whisper-tiny-pt','tiny.pt')]:
    try:
        p = hf_hub_download(repo, fn, local_dir='/tmp/whisp')
        shutil.copy(p, 'pretrained_weights/audio_processor/tiny.pt')
        print('OK whisper from', repo, flush=True); break
    except Exception as e:
        print('miss', repo, str(e)[:80], flush=True)
PYEOF
fi
if [ ! -s "$TPT" ]; then
  source /etc/network_turbo 2>/dev/null || true
  wget -q -O "$TPT" "https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt" && echo "OK whisper azureedge" || echo "WHISPER_FAIL"
fi

echo "=== WEIGHTS SUMMARY ==="
du -sh pretrained_weights 2>/dev/null
ls -la pretrained_weights/*.pth pretrained_weights/audio_processor/tiny.pt 2>/dev/null
ls pretrained_weights/sd-vae-ft-mse pretrained_weights/sd-image-variations-diffusers 2>/dev/null
echo "=== WEIGHTS ALL DONE ==="
