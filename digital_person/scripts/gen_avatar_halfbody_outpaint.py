#!/usr/bin/env python
"""SDXL outpaint：把实时数字人半身头像(sweet_bob+灵山背景)向下+两侧拓展，长出躯干/手臂/垂手，
得到 EchoMimicV2 挥手欢迎片要的「半身露手」源图。身份与背景与实时形象完全一致(同一张图拓出来)。
用内置 ImagePadForOutpaint 自动生成画布+遮罩，SDXL RealVisXL 重绘补全。在 AutoDL ComfyUI(:8188) 跑。
源图 ComfyUI/input/sweet_bob_bust.png。用法: python gen_avatar_halfbody_outpaint.py [seed]
"""
import sys, time, httpx, uuid

COMFY = "http://127.0.0.1:8188"
BUST = "sweet_bob_bust.png"
PAD_BOTTOM, PAD_SIDE = 744, 96
POS = (
    "a beautiful young Chinese female tour guide with short chin-length bob haircut, "
    "wearing a cream high-neck knit top, her full upper body and torso, "
    "both arms hanging straight down relaxed at her sides, both hands open and visible resting near her thighs, "
    "natural well-formed hands with five fingers, "
    "standing in the misty green mountains of lingshan, warm soft morning light, "
    "photorealistic, highly detailed, natural color grading, seamless continuation, consistent body and clothing"
)
NEG = (
    "deformed hands, malformed hands, extra fingers, fused fingers, too many fingers, mutated hands, "
    "missing hands, hands behind back, clasped hands, hands on hips, crossed arms, hands at waist, hands together, extra limbs, extra arms, "
    "duplicate body, second person, deformed, lowres, bad anatomy, ugly, blurry, watermark, text, "
    "seam, visible seam, discontinuity, color mismatch"
)

def graph(seed):
    return {
        "4":  {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealVisXL_V5.0_fp16.safetensors"}},
        "13": {"class_type": "LoadImage", "inputs": {"image": BUST}},
        "20": {"class_type": "ImagePadForOutpaint", "inputs": {
            "image": ["13", 0], "left": PAD_SIDE, "top": 0, "right": PAD_SIDE, "bottom": PAD_BOTTOM, "feathering": 40}},
        "21": {"class_type": "VAEEncodeForInpaint", "inputs": {
            "pixels": ["20", 0], "vae": ["4", 2], "mask": ["20", 1], "grow_mask_by": 16}},
        "39": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["4", 1]}},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "3":  {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 5.0, "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": 1.0, "model": ["4", 0], "positive": ["39", 0], "negative": ["40", 0], "latent_image": ["21", 0]}},
        "8":  {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9":  {"class_type": "SaveImage", "inputs": {"filename_prefix": "hbout", "images": ["8", 0]}},
    }

if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 12345
    C = httpx.Client(trust_env=False, timeout=60)
    r = C.post(f"{COMFY}/prompt", json={"prompt": graph(seed), "client_id": uuid.uuid4().hex})
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    print(f"[hbout] seed={seed} 生成中…")
    for _ in range(300):
        time.sleep(2)
        h = C.get(f"{COMFY}/history/{pid}").json()
        if pid in h:
            for node in h[pid]["outputs"].values():
                for im in node.get("images", []):
                    print("[hbout] saved:", im["filename"])
            break
    else:
        print("[hbout] timeout")
