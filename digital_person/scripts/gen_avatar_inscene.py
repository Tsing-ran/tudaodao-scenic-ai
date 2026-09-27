"""ComfyUI InstantID「人在景中」生成：锁甜美脸身份，把导游和景区场景**一起生成成一张图**。

为什么换这个思路（取代抠像合成）：
  抠图(rembg)把人物贴到单独生成的背景上 → 光照/景深不统一、边缘是抠的 → 永远"贴上去"。
  本脚本让 InstantID 锁住 face16 身份后，**人与场景由扩散模型一次性协调生成** →
  人物完整、光照统一、无抠图边、天然在场景里。产物直接当 Ditto 横版底板（Ditto 驱原图）。

代价：对灵山大佛等具体地标的精度不如 万相 专门出图（可后续加 ControlNet 引导结构）。

前置：ComfyUI 在 127.0.0.1:8188 跑；参考脸 ComfyUI/input/face16b.png；RealVisXL + InstantID + FaceDetailer。
用法：.venv/bin/python scripts/gen_avatar_inscene.py [scenic]   # 默认 lingshan
"""
import sys
import time
import uuid
from pathlib import Path

import httpx
from PIL import Image

COMFY = "http://127.0.0.1:8188"
FACE = "face16b.png"
ROOT = Path(__file__).resolve().parents[1]
DITTO_DIR = Path.home() / "Desktop/LiveTalking/data/ditto_avatars"
REVIEW = ROOT / "assets" / "ui_shots"
LS_W, LS_H = 1280, 720
GEN_W, GEN_H = 1344, 768            # SDXL 友好的 16:9 分桶，出图后缩到 1280×720

# 每景区「人站在其中」的场景描述（人物部分公共，场景部分按景区换）
SCENES = {
    "lingshan":   "standing outdoors in the misty green mountains of a Chinese Buddhist holy land, a distant giant buddha statue and temple pagoda silhouette softly veiled in morning fog, warm golden sunrise light, incense haze",
    "nihuawan":   "standing in a Tang-dynasty style Zen water town at dusk, white walls and dark-tiled wooden eaves behind, warm glowing lanterns, soft cherry blossom bokeh",
    "xihu":       "standing by misty West Lake, distant Leifeng pagoda and arched bridge over calm misty water, soft grey-green atmospheric haze",
    "huangshan":  "standing on a Huangshan mountain platform above a rolling sea of clouds, distant granite peaks and a welcoming pine silhouette, golden glow",
    "gugong":     "standing in the Forbidden City, golden glazed-tile palace eaves and red walls behind, golden ginkgo leaves, soft morning light",
    "zhangjiajie": "standing among the towering quartz sandstone pillars of Zhangjiajie shrouded in drifting mist, lush green, ethereal",
    "bingmayong": "standing in the warm amber-lit Terracotta Army museum hall, blurred terracotta warrior pit deep behind in soft bokeh",
    "mogaoku":    "standing before the golden Mingsha sand dunes and Crescent Lake of Dunhuang, warm sand tones, clear dawn sky",
}

POS_TMPL = (
    "a beautiful young Chinese female tour guide, short chin-length bob haircut with side-swept bangs, "
    "modern professional guide outfit with a small badge, "
    "gentle pleasant closed-mouth smile, flawless clean bright under-eye area, absolutely no eye bags, "
    "smooth radiant fair skin, small delicate refined nose, "
    "head level and straight, chin slightly tucked, looking directly at the camera, "
    "{scene}, "
    "medium shot from the waist up, she is naturally lit by the warm environment light, "
    "shallow depth of field, cinematic atmospheric bokeh background, "
    "photorealistic, highly detailed, natural color grading, 8k"
)
NEG = (
    "cut out, cutout, sticker, pasted, collage, floating, flat even lighting, studio backdrop, "
    "plain background, hard outline, eye bags, dark circles, puffy eyes, big nose, large nostrils, "
    "deformed, lowres, bad anatomy, ugly, blurry, extra limbs, watermark, text, open mouth, laughing"
)
FACE_FIX_POS = (
    "a beautiful young Chinese woman face, flawless clean smooth bright under-eye area, "
    "absolutely no eye bags, no dark circles, smaller delicate refined nose, small narrow nostrils, "
    "bright clear eyes, smooth radiant fair skin, gentle closed-mouth smile, ultra-detailed face"
)

_C = httpx.Client(trust_env=False, timeout=30)


def build_graph(positive, seed):
    return {
        "4":  {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealVisXL_V5.0_fp16.safetensors"}},
        "11": {"class_type": "InstantIDModelLoader", "inputs": {"instantid_file": "ip-adapter.bin"}},
        "38": {"class_type": "InstantIDFaceAnalysis", "inputs": {"provider": "CPU"}},
        "16": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "instantid_controlnet.safetensors"}},
        "13": {"class_type": "LoadImage", "inputs": {"image": FACE}},
        "39": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["4", 1]}},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        # weight 0.85：锁紧身份(确保还是 sweet_bob 同一人)；场景融合靠 prompt+低 cfg 已足够
        "60": {"class_type": "ApplyInstantID", "inputs": {
            "instantid": ["11", 0], "insightface": ["38", 0], "control_net": ["16", 0],
            "image": ["13", 0], "model": ["4", 0], "positive": ["39", 0], "negative": ["40", 0],
            "weight": 0.85, "start_at": 0.0, "end_at": 1.0}},
        "5":  {"class_type": "EmptyLatentImage", "inputs": {"width": GEN_W, "height": GEN_H, "batch_size": 1}},
        "3":  {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 4.5, "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": 1.0, "model": ["60", 0], "positive": ["60", 1], "negative": ["60", 2],
            "latent_image": ["5", 0]}},
        "8":  {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
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
        "9":  {"class_type": "SaveImage", "inputs": {"filename_prefix": "inscene", "images": ["71", 0]}},
    }


def main():
    scenic = sys.argv[1] if len(sys.argv) > 1 else "lingshan"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20260613
    if scenic not in SCENES:
        sys.exit(f"未知景区 {scenic}（可选：{','.join(SCENES)}）")
    pos = POS_TMPL.format(scene=SCENES[scenic])
    cid = uuid.uuid4().hex
    print(f"[inscene] {scenic} 生成中（InstantID 锁脸 + 场景一体生成，{GEN_W}x{GEN_H}）…")
    r = _C.post(f"{COMFY}/prompt", json={"prompt": build_graph(pos, seed), "client_id": cid})
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    t0 = time.time()
    imgs = []
    while time.time() - t0 < 300:
        h = _C.get(f"{COMFY}/history/{pid}").json()
        if pid in h:
            for node in h[pid].get("outputs", {}).values():
                imgs += node.get("images", [])
            if imgs:
                break
        time.sleep(2)
    if not imgs:
        sys.exit("❌ 超时无输出")
    im = imgs[-1]
    raw = _C.get(f"{COMFY}/view", params={"filename": im["filename"],
                 "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")}).content
    # 缩到 1280×720 当 Ditto 横版底板
    tmp = REVIEW / f"inscene_{scenic}_raw.png"
    REVIEW.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(raw)
    img = Image.open(tmp).convert("RGB").resize((LS_W, LS_H), Image.LANCZOS)
    review = REVIEW / f"inscene_{scenic}.png"
    img.save(review)
    DITTO_DIR.mkdir(parents=True, exist_ok=True)
    avatar = DITTO_DIR / f"sweet_bob_inscene_{scenic}.png"
    img.save(avatar)
    print(f"  ✅ 审图 {review}")
    print(f"  ✅ Ditto 底板 {avatar}")
    print(f"  验证驱动：--avatar_id sweet_bob_inscene_{scenic}")


if __name__ == "__main__":
    main()
