"""向上 outpaint 补出被切的发冠（生成圆顶头发，非补灰非平切）。
用法: outpaint_crown.py <in basename in ComfyUI/input/> <out.png> [pad_top=300]
ComfyUI/input/ 需有该图；用 RealVisXL inpaint 在扩出的顶部区域生成头发+灰背景。
"""
import sys, time, uuid
from pathlib import Path
import httpx

COMFY = "http://127.0.0.1:8188"
IN = sys.argv[1] if len(sys.argv) > 1 else "portrait_down3.png"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp/tune/crown_fixed.png")
PAD = int(sys.argv[3]) if len(sys.argv) > 3 else 300
_C = httpx.Client(trust_env=False, timeout=30)

POS = ("a beautiful young Chinese woman, short brown bob hairstyle, "
       "the top of her head fully covered with smooth brown hair, natural rounded hairline, "
       "plain light grey studio background, photorealistic, high detail")
NEG = ("crown, tiara, headpiece, jewelry, headband, hat, ornament, accessory, "
       "flat top hair, cut off hair, hard horizontal edge, line, seam, band, "
       "deformed, blurry, lowres, text, watermark")


def graph():
    return {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealVisXL_V5.0_fp16.safetensors"}},
        "13": {"class_type": "LoadImage", "inputs": {"image": IN}},
        # 向上扩 PAD 像素，feather 让接缝柔和
        "20": {"class_type": "ImagePadForOutpaint", "inputs": {
            "image": ["13", 0], "left": 0, "top": PAD, "right": 0, "bottom": 0, "feathering": 48}},
        "39": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["4", 1]}},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "21": {"class_type": "VAEEncodeForInpaint", "inputs": {
            "pixels": ["20", 0], "vae": ["4", 2], "mask": ["20", 1], "grow_mask_by": 16}},
        "3": {"class_type": "KSampler", "inputs": {
            "seed": 12345, "steps": 28, "cfg": 5.0, "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": 1.0, "model": ["4", 0], "positive": ["39", 0], "negative": ["40", 0],
            "latent_image": ["21", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "crown", "images": ["8", 0]}},
    }


pid = _C.post(f"{COMFY}/prompt", json={"prompt": graph(), "client_id": uuid.uuid4().hex}).json()["prompt_id"]
print(f"提交 {pid} pad_top={PAD}")
t0 = time.time()
while time.time() - t0 < 300:
    h = _C.get(f"{COMFY}/history/{pid}").json()
    if pid in h:
        imgs = [im for node in h[pid].get("outputs", {}).values() for im in node.get("images", [])]
        if imgs:
            im = imgs[0]
            r = _C.get(f"{COMFY}/view", params={"filename": im["filename"], "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")})
            OUT.write_bytes(r.content)
            print(f"✅ {OUT}")
            break
    time.sleep(2)
print("DONE")
