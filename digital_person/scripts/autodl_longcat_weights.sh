#!/bin/bash
# LongCat-Video-Avatar-1.5 选择性下载（int8 路线，~45GB）。避开 31GB fp16 base + 54GB base dit + 冗余 whisper 格式。
# 目录布局须 weights/LongCat-Video-Avatar-1.5 + weights/LongCat-Video（脚本按 ../LongCat-Video 取 t5/vae/tokenizer）。
set +e
export HF_ENDPOINT=https://hf-mirror.com
cd /root/autodl-tmp/phase0/LongCat-Video || exit 9
mkdir -p weights
PY=/root/miniconda3/bin/python
$PY -m pip install -q -U "huggingface_hub" >/dev/null 2>&1

echo "=== 1) avatar repo (int8 DiT + lora + whisper fp16 + vocal_separator) ==="
$PY - <<'EOF'
from huggingface_hub import snapshot_download
snapshot_download('meituan-longcat/LongCat-Video-Avatar-1.5',
  local_dir='weights/LongCat-Video-Avatar-1.5',
  allow_patterns=[
    'base_model_int8/*','lora/dmd_lora.safetensors','vocal_separator/*',
    'scheduler/*','config.json','model_index.json',
    'whisper-large-v3/config.json','whisper-large-v3/model.safetensors',
    'whisper-large-v3/tokenizer.json','whisper-large-v3/tokenizer_config.json',
    'whisper-large-v3/vocab.json','whisper-large-v3/merges.txt',
    'whisper-large-v3/added_tokens.json','whisper-large-v3/normalizer.json',
    'whisper-large-v3/special_tokens_map.json','whisper-large-v3/preprocessor_config.json',
    'whisper-large-v3/generation_config.json'])
print('AVATAR_REPO_DONE', flush=True)
EOF

echo "=== 2) base repo (UMT5 text_encoder + vae + tokenizer + scheduler), 跳过 54GB dit ==="
$PY - <<'EOF'
from huggingface_hub import snapshot_download
snapshot_download('meituan-longcat/LongCat-Video',
  local_dir='weights/LongCat-Video',
  allow_patterns=['text_encoder/*','vae/*','tokenizer/*','scheduler/*','model_index.json','config.json'])
print('BASE_REPO_DONE', flush=True)
EOF

echo "=== LONGCAT WEIGHTS DONE ==="
du -sh weights/LongCat-Video-Avatar-1.5 weights/LongCat-Video 2>/dev/null
