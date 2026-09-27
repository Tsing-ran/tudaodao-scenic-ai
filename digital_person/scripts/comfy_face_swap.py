"""ComfyUI InstantID 锁脸换装：锁定一张参考脸 → 换不同服装 + 去眼袋 → 批量出图。

这是本项目的「自研形象生成引擎」：本地 ComfyUI + RealVisXL + InstantID。
- 锁脸：InstantID 从参考图提取人脸身份，保证换装后还是同一张脸
- 换装：只改服装提示词
- 去眼袋/提颜值：提示词 + 负向词控制
用途：① 给用户批量出"同脸不同装"选 ② 后接管理端「AI生成新形象」按钮（赛题形象可配置）

前置：ComfyUI 已在 127.0.0.1:8188 运行；参考脸放在 ComfyUI/input/。
用法：.venv/bin/python scripts/comfy_face_swap.py
"""
import json
import time
import uuid
from pathlib import Path

import httpx

COMFY = "http://127.0.0.1:8188"
FACE = "face16b.png"               # 美图修好的新参考脸（眼袋淡、鼻孔小）
OUT = Path(__file__).resolve().parents[1] / "assets" / "avatar_facelock"

# 去眼袋(强化) + 小鼻孔 + 高颜值 + MuseTalk 选材（正脸、纯背景、嘴清晰）
BASE_POS = (
    "a beautiful young Chinese female tour guide, {outfit}, "
    "gentle pleasant smile, flawless bright clean under-eye area, absolutely no eye bags, "
    "no dark circles, smooth healthy radiant fair skin, "
    "small delicate refined nose with small nostrils, delicate pretty face, "
    "head level and straight, chin slightly tucked down, looking straight at camera, "
    "high-detail portrait, upper body, soft studio lighting, "
    "plain light-grey background, photorealistic, 8k"
)
NEG = (
    "eye bags, dark circles, under-eye bags, puffy eyes, tired eyes, "
    "big nose, large nostrils, wide nose, flared nostrils, "
    "deformed, lowres, bad anatomy, ugly, blurry, extra limbs, watermark, text, open mouth, laughing"
)

# FaceDetailer 专用脸部提示词（只渲染脸那一块，重点去眼袋+缩小鼻孔+干净皮肤，保持年轻漂亮）
FACE_FIX_POS = (
    "a beautiful young Chinese woman face, flawless clean smooth bright under-eye area, "
    "absolutely no eye bags, no dark circles, no under-eye shadow, "
    "noticeably smaller delicate refined nose, small narrow nostrils, nose tip slightly downward, "
    "bright clear eyes, smooth radiant flawless fair skin, gentle closed-mouth smile, "
    "pretty and pleasant, ultra-detailed high quality face"
)

# 换装不换脸：同一张脸的不同服装
OUTFITS = {
    "blazer":  "modern professional navy blazer with a guide badge",
    "hanfu":   "elegant traditional Chinese hanfu dress",
    "vest":    "casual scenic-area guide vest uniform",
    "qipao":   "graceful improved silk qipao",
    "ethnic":  "colorful Chinese ethnic minority costume with silver headwear",
    "coat":    "warm beige winter coat with scarf",
}


# trust_env=False：localhost 直连，绕开环境里的 socks 代理（httpx 不认 socks scheme）
_C = httpx.Client(trust_env=False, timeout=30)


def submit(graph: dict, client_id: str) -> str:
    r = _C.post(f"{COMFY}/prompt", json={"prompt": graph, "client_id": client_id})
    r.raise_for_status()
    return r.json()["prompt_id"]


def wait_images(prompt_id: str, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = _C.get(f"{COMFY}/history/{prompt_id}").json()
        if prompt_id in h:
            outs = h[prompt_id].get("outputs", {})
            imgs = []
            for node in outs.values():
                for im in node.get("images", []):
                    imgs.append(im)
            if imgs:
                return imgs
        time.sleep(2)
    return []


def build_graph(positive, seed):
    return {
        "4":  {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealVisXL_V5.0_fp16.safetensors"}},
        "11": {"class_type": "InstantIDModelLoader", "inputs": {"instantid_file": "ip-adapter.bin"}},
        "38": {"class_type": "InstantIDFaceAnalysis", "inputs": {"provider": "CPU"}},
        "16": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "instantid_controlnet.safetensors"}},
        "13": {"class_type": "LoadImage", "inputs": {"image": FACE}},
        "39": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["4", 1]}},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "60": {"class_type": "ApplyInstantID", "inputs": {
            "instantid": ["11", 0], "insightface": ["38", 0], "control_net": ["16", 0],
            "image": ["13", 0], "model": ["4", 0], "positive": ["39", 0], "negative": ["40", 0],
            "weight": 0.8, "start_at": 0.0, "end_at": 1.0}},
        "5":  {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
        "3":  {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 4.5, "sampler_name": "ddpm", "scheduler": "karras",
            "denoise": 1.0, "model": ["60", 0], "positive": ["60", 1], "negative": ["60", 2],
            "latent_image": ["5", 0]}},
        "8":  {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        # —— FaceDetailer 人脸精修：检测脸→只重渲脸部去眼袋缩鼻孔→贴回 ——
        "72": {"class_type": "CLIPTextEncode", "inputs": {"text": FACE_FIX_POS, "clip": ["4", 1]}},
        "70": {"class_type": "UltralyticsDetectorProvider", "inputs": {"model_name": "bbox/face_yolov8m.pt"}},
        "71": {"class_type": "FaceDetailer", "inputs": {
            "image": ["8", 0], "model": ["4", 0], "clip": ["4", 1], "vae": ["4", 2],
            "positive": ["72", 0], "negative": ["40", 0], "bbox_detector": ["70", 0],
            "guide_size": 768, "guide_size_for": True, "max_size": 1024, "seed": seed + 7,
            "steps": 25, "cfg": 5.0, "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": 0.25, "feather": 5, "noise_mask": True, "force_inpaint": True,
            "bbox_threshold": 0.5, "bbox_dilation": 10, "bbox_crop_factor": 3.0,
            "sam_detection_hint": "center-1", "sam_dilation": 0, "sam_threshold": 0.93,
            "sam_bbox_expansion": 0, "sam_mask_hint_threshold": 0.7,
            "sam_mask_hint_use_negative": "False", "drop_size": 10, "wildcard": "", "cycle": 1}},
        "9":  {"class_type": "SaveImage", "inputs": {"filename_prefix": "facelock", "images": ["71", 0]}},
    }


def _next_path(tag: str) -> Path:
    """版本自增：face16_<tag>.png / _v2 / _v3 …"""
    base = OUT / f"face16_{tag}.png"
    if not base.exists():
        return base
    v = 2
    while (OUT / f"face16_{tag}_v{v}.png").exists():
        v += 1
    return OUT / f"face16_{tag}_v{v}.png"


def main():
    import sys
    OUT.mkdir(parents=True, exist_ok=True)
    only = sys.argv[1] if len(sys.argv) > 1 else None   # 只跑指定服装，如 coat
    items = [(only, OUTFITS[only])] if only in OUTFITS else list(OUTFITS.items())
    cid = uuid.uuid4().hex
    for i, (tag, outfit) in enumerate(items):
        pos = BASE_POS.format(outfit=outfit)
        print(f"[{i+1}/{len(items)}] 换装 {tag}（含FaceDetailer修脸）…")
        pid = submit(build_graph(pos, seed=1000 + list(OUTFITS).index(tag)), cid)
        imgs = wait_images(pid, timeout=300)
        if not imgs:
            print(f"  ❌ {tag} 超时无输出"); continue
        im = imgs[0]
        r = _C.get(f"{COMFY}/view", params={"filename": im["filename"], "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")})
        dst = _next_path(tag)
        dst.write_bytes(r.content)
        print(f"  ✅ {dst}")
    print("完成 ->", OUT)


if __name__ == "__main__":
    main()
