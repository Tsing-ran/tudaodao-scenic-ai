#!/bin/bash
# 阶段0 收尾：装 infer.py 真正需要的最小依赖（剔除 onnxruntime-gpu/mediapipe 等仅姿态提取用的重包）
# → 验证 infer 导入链 → 直接渲染第一条样片。一条龙后台跑。
cd /root/autodl-tmp/phase0/echomimic_v2 || exit 9
ENV_DIR=/root/autodl-tmp/envs/echomimic
export PIP_CACHE_DIR=/root/autodl-tmp/pipcache TMPDIR=/root/autodl-tmp/tmp
PY="$ENV_DIR/bin/python"; PIP="$ENV_DIR/bin/pip"
TS="https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
# 剔除 infer.py 不需要、且会触发 pip 回溯地狱/超大下载的包：
#  gradio(仅app.py UI,回溯灾区) / onnxruntime-gpu+mediapipe(仅姿态提取) /
#  mlflow(实验跟踪) / scenedetect+controlnet-aux(预处理) / opencv-contrib(已有opencv-python)
grep -vE "onnxruntime-gpu|mediapipe|^mlflow|scenedetect|controlnet-aux|^gradio|opencv-contrib-python" /root/autodl-tmp/phase0/req_noclip.txt > /root/autodl-tmp/phase0/req_min.txt
echo "=== install minimal reqs (tsinghua) ==="
$PIP install -r /root/autodl-tmp/phase0/req_min.txt -i "$TS" --trusted-host mirrors.tuna.tsinghua.edu.cn
$PIP install --no-deps facenet_pytorch==2.6.0 -i "$TS" --trusted-host mirrors.tuna.tsinghua.edu.cn
# matplotlib 是 dwpose_util.py 的未声明依赖（requirements.txt 漏了）
$PIP install matplotlib -i "$TS" --trusted-host mirrors.tuna.tsinghua.edu.cn
echo "=== verify infer import chain ==="
$PY -c "
import numpy,torch
from diffusers import AutoencoderKL, DDIMScheduler
from einops import repeat
from omegaconf import OmegaConf
from PIL import Image
from src.models.unet_2d_condition import UNet2DConditionModel
from src.models.unet_3d_emo import EMOUNet3DConditionModel
from src.models.whisper.audio2feature import load_audio_model
from src.pipelines.pipeline_echomimicv2 import EchoMimicV2Pipeline
from src.utils.util import save_videos_grid
from src.models.pose_encoder import PoseEncoder
from src.utils.dwpose_util import draw_pose_select_v2
from decord import VideoReader
from moviepy.editor import VideoFileClip, AudioFileClip
print('INFER_IMPORTS_OK cuda', torch.cuda.is_available())
"
VOK=$?; echo "VERIFY_EXIT=$VOK"
if [ $VOK -ne 0 ]; then echo "=== VERIFY FAILED, abort render ==="; exit 1; fi
echo "=== RENDER START ==="; date
export FFMPEG_PATH=/usr/bin PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
mkdir -p assets/halfbody_demo/audio/chinese
cp -f /root/autodl-tmp/phase0/phase0_short.wav assets/halfbody_demo/audio/chinese/phase0_short.wav
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
$PY infer.py --config configs/prompts/infer.yaml -W 768 -H 768 -L 144 --steps 30 --cfg 2.5 --fps 24 \
  --refimg_name natural_bk_openhand/0035.png --audio_name chinese/phase0_short.wav --pose_name 01
echo "=== RENDER EXIT=$? ==="; date
find outputs -name "*.mp4" -printf "%T+ %s %p\n" 2>/dev/null | sort | tail -3
echo "=== PHASE0 DONE ==="
