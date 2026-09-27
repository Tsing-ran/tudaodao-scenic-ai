#!/usr/bin/env python
"""InstantID 锁脸出「干净 studio 半身像」：复刻主形象 sweet_bob(face16) 的灰底奶白高领标准像，
但镜头更远、露完整上半身+完整头发(留头顶空间)。供 InfiniteTalk 等当源图。在 AutoDL ComfyUI(:8188) 跑。
参考脸 ComfyUI/input/face16b.png。用法: python gen_avatar_studio.py [seed]
"""
import sys, time, httpx, uuid

COMFY = "http://127.0.0.1:8188"
FACE = "face16b.png"
GEN_W, GEN_H = 832, 1216
POS = (
    "studio portrait of a beautiful young Chinese woman, short chin-length soft bob haircut with side-swept bangs, "
    "wearing a cream beige high-neck ribbed knit top, gentle pleasant closed-mouth smile, "
    "flawless clean bright under-eye area, absolutely no eye bags, smooth radiant fair skin, "
    "small delicate refined nose, head level looking directly at the camera, "
    "full complete bob hair fully visible with ample headroom and empty space above her head, "
    "natural realistic head-to-body proportion, "
    "clean smooth light grey seamless studio background, soft even professional studio lighting, "
    "medium upper-body shot framed from above her head down to her waist, her whole upper body visible, "
    "photorealistic, highly detailed, sharp focus, natural color grading, 8k"
)
NEG = (
    "big head, oversized head, large head, head cropped, hair cropped, cropped at the top, close-up, tight crop, "
    "eye bags, dark circles, puffy eyes, big nose, large nostrils, open mouth, laughing, "
    "busy background, outdoor, landscape, cluttered, deformed, lowres, bad anatomy, ugly, blurry, "
    "extra limbs, watermark, text"
)

def graph(seed):
    return {
        "4":  {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealVisXL_V5.0_fp16.safetensors"}},
        "11": {"class_type": "InstantIDModelLoader", "inputs": {"instantid_file": "ip-adapter.bin"}},
        "38": {"class_type": "InstantIDFaceAnalysis", "inputs": {"provider": "CPU"}},
        "16": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "instantid_controlnet.safetensors"}},
        "13": {"class_type": "LoadImage", "inputs": {"image": FACE}},
        "39": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["4", 1]}},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "60": {"class_type": "ApplyInstantID", "inputs": {
            "instantid": ["11", 0], "insightface": ["38", 0], "control_net": ["16", 0],
            "image": ["13", 0], "model": ["4", 0], "positive": ["39", 0], "negative": ["40", 0],
            "weight": 0.70, "start_at": 0.0, "end_at": 0.45}},
        "5":  {"class_type": "EmptyLatentImage", "inputs": {"width": GEN_W, "height": GEN_H, "batch_size": 1}},
        "3":  {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 4.5, "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": 1.0, "model": ["60", 0], "positive": ["60", 1], "negative": ["60", 2], "latent_image": ["5", 0]}},
        "8":  {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9":  {"class_type": "SaveImage", "inputs": {"filename_prefix": "studio", "images": ["8", 0]}},
    }

if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 12345
    C = httpx.Client(trust_env=False, timeout=60)
    r = C.post(f"{COMFY}/prompt", json={"prompt": graph(seed), "client_id": uuid.uuid4().hex})
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    print(f"[studio] seed={seed} 生成中…")
    for _ in range(300):
        time.sleep(2)
        h = C.get(f"{COMFY}/history/{pid}").json()
        if pid in h:
            for node in h[pid]["outputs"].values():
                for im in node.get("images", []):
                    print("[studio] saved:", im["filename"])
            break
    else:
        print("[studio] timeout")
