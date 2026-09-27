"""原生生成「导游在景区背景里」16:9 底图——人和景一起生成(coherent,非合成,无贴图/抠图问题)。
延续形象库 #4 的好看景区感,换不同人物风格 + 不同景区氛围。为 Ditto 优化:正脸柔光、嘴清晰、完整。
用法：.venv/bin/python scripts/gen_avatar_scenic.py [only_id]
"""
import sys, time, uuid, io
from pathlib import Path
import httpx
from PIL import Image

COMFY = "http://127.0.0.1:8188"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "avatar_library_scenic"
CKPT = "RealVisXL_V5.0_fp16.safetensors"
GW, GH = 1344, 768
LW, LH = 1280, 720

# 颜值强化：对标用户审美「甜美清纯高颜值」——精致五官/大眼/无瑕肌肤/上镜，但自然不假
BEAUTY = ("extremely beautiful and pretty, stunning gorgeous delicate face, exquisite refined facial features, "
          "big bright clear sparkling almond eyes, high nose bridge, fair flawless radiant porcelain skin, "
          "sweet pure gentle lovely expression, cute and charming, photogenic idol-level beauty, ")
COMMON = ("medium shot from the waist up, centered with headroom, looking straight at the camera, "
          "head level and straight, gentle pleasant closed-mouth smile, "
          "face softly and evenly lit by warm natural light, no harsh shadows, "
          "shallow depth of field, soft bokeh scenic background behind her, naturally part of the scene, "
          "photorealistic, ultra detailed, sharp focus, cinematic, natural color, 8k")
NEG = ("ugly, plain face, average looking, unattractive, homely, asymmetric face, masculine face, "
       "old, wrinkles, small eyes, dull eyes, bad skin, blemishes, "
       "harsh shadows, cyan face, dark face, backlit, cut off arms, cropped body, "
       "deformed, extra limbs, lowres, bad anatomy, blurry, watermark, text, open mouth, laughing, "
       "looking away, tilted head, 3d render, cgi, plastic skin")

# 人物风格 × 景区氛围（人和景一起生成）
CHARS = {
    "bob_mountain":   ("a beautiful young Chinese female tour guide, short chin-length bob haircut, "
                       "modern light professional guide outfit, standing among misty green Buddhist mountains "
                       "with a distant pagoda softly veiled in morning fog, warm golden sunrise glow"),
    "sweet_garden":   ("a sweet approachable young Chinese woman guide, soft shoulder-length wavy hair, "
                       "light beige knit top, standing in a classical Chinese garden with a pavilion and "
                       "willow trees softly blurred behind, gentle warm daylight"),
    "guofeng_temple": ("a graceful Chinese woman guide in an elegant modern hanfu-inspired dress, soft updo "
                       "with a delicate hairpin, standing before a misty mountain temple, warm soft light, serene"),
    "youthful_view":  ("a youthful energetic Chinese female guide, neat ponytail, light blue guide uniform shirt, "
                       "standing at a bright scenic mountain overlook with rolling green peaks behind, fresh clear light"),
    "mature_palace":  ("a beautiful sweet young Chinese woman tour guide, neat shoulder-length hair, elegant blazer, "
                       "standing in front of golden palace eaves and red walls softly blurred, warm morning light"),
    "lake_misty":     ("a beautiful young Chinese woman guide, shoulder-length hair, soft light blouse, "
                       "standing by a misty calm lake with a distant pagoda and arched bridge, soft grey-green haze"),
}


def graph(prompt, seed):
    return {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": GW, "height": GH, "batch_size": 1}},
        "39": {"class_type": "CLIPTextEncode", "inputs": {"text": f"{BEAUTY}{prompt}, {COMMON}", "clip": ["4", 1]}},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "3": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 32, "cfg": 5.0, "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": 1.0, "model": ["4", 0], "positive": ["39", 0], "negative": ["40", 0],
            "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "72": {"class_type": "CLIPTextEncode", "inputs": {"text": "an extremely beautiful pretty young Chinese woman face, exquisite delicate refined features, big bright clear sparkling almond eyes, high nose bridge, small delicate nose, fair flawless radiant porcelain skin, no eye bags, sweet pure lovely gentle closed-mouth smile, idol-level beauty, softly evenly lit, ultra detailed, photorealistic", "clip": ["4", 1]}},
        "70": {"class_type": "UltralyticsDetectorProvider", "inputs": {"model_name": "bbox/face_yolov8m.pt"}},
        "71": {"class_type": "FaceDetailer", "inputs": {
            "image": ["8", 0], "model": ["4", 0], "clip": ["4", 1], "vae": ["4", 2],
            "positive": ["72", 0], "negative": ["40", 0], "bbox_detector": ["70", 0],
            "guide_size": 768, "guide_size_for": True, "max_size": 1024, "seed": seed + 3,
            "steps": 22, "cfg": 5.0, "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": 0.22, "feather": 5, "noise_mask": True, "force_inpaint": True,
            "bbox_threshold": 0.5, "bbox_dilation": 10, "bbox_crop_factor": 3.0,
            "sam_detection_hint": "center-1", "sam_dilation": 0, "sam_threshold": 0.93,
            "sam_bbox_expansion": 0, "sam_mask_hint_threshold": 0.7,
            "sam_mask_hint_use_negative": "False", "drop_size": 10, "wildcard": "", "cycle": 1}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "scenic", "images": ["71", 0]}},
    }


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    items = [(only, CHARS[only])] if only in CHARS else list(CHARS.items())
    OUT.mkdir(parents=True, exist_ok=True)
    c = httpx.Client(trust_env=False, timeout=30)
    for i, (cid, prompt) in enumerate(items):
        seed = 9100 + i * 37
        print(f"[{i+1}/{len(items)}] {cid} …")
        r = c.post(f"{COMFY}/prompt", json={"prompt": graph(prompt, seed), "client_id": uuid.uuid4().hex})
        if r.status_code != 200:
            print(f"  ❌ {r.text[:200]}"); continue
        pid = r.json()["prompt_id"]; t0 = time.time(); imgs = []
        while time.time() - t0 < 240:
            h = c.get(f"{COMFY}/history/{pid}").json()
            if pid in h:
                if h[pid].get("status", {}).get("status_str") == "error":
                    print(f"  ❌ {h[pid]['status']}"); break
                for n in h[pid].get("outputs", {}).values():
                    imgs += n.get("images", [])
                if imgs: break
            time.sleep(2)
        if not imgs:
            print("  ❌ 超时"); continue
        im = imgs[-1]
        raw = c.get(f"{COMFY}/view", params={"filename": im["filename"],
                    "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")}).content
        p = OUT / f"{cid}.png"
        Image.open(io.BytesIO(raw)).convert("RGB").resize((LW, LH), Image.LANCZOS).save(p)
        print(f"  ✅ {p}")
    print(f"\n→ {OUT}")


if __name__ == "__main__":
    main()
