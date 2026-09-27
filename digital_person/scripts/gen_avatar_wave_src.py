#!/usr/bin/env python
"""InstantID 生成数字人「半身露手 + 灵山背景」源图（供 EchoMimicV2 挥手欢迎片用）。
区别于 gen_avatar_inscene.py：竖版构图、画到上腿、双手自然垂在身侧清晰可见（挥手需要手在画面里）。
在 AutoDL ComfyUI(:8188) 跑（COMFY=localhost）。参考脸 ComfyUI/input/face16b.png。
用法: python gen_avatar_wave_src.py [seed]  → 出图存 ComfyUI/output/wavesrc_*.png，再 scp 回本地挑选。
"""
import sys, time, httpx, uuid

COMFY = "http://127.0.0.1:8188"
FACE = "face16b.png"
GEN_W, GEN_H = 832, 1216             # 竖版半身，容下上身+垂手
SCENE = ("standing outdoors in the misty green mountains of a Chinese Buddhist holy land, "
         "a distant giant buddha statue and temple pagoda silhouette softly veiled in morning fog, "
         "warm golden sunrise light, incense haze")

POS = (
    "a beautiful young Chinese female tour guide, short chin-length bob haircut with side-swept bangs, "
    "modern professional light-blue guide outfit with a small badge, "
    "gentle pleasant closed-mouth smile, flawless clean bright under-eye area, absolutely no eye bags, "
    "smooth radiant fair skin, small delicate refined nose, head level looking directly at the camera, "
    "standing relaxed and upright with a confident open posture, both arms hanging straight down at her sides, "
    "hands open and apart resting near her thighs, arms and hands clearly separated away from her body, "
    "natural well-formed hands with five fingers, "
    "full natural hair with complete soft bob hairstyle, ample headroom with empty space above her head, "
    "the top of her head and all her hair are fully inside the frame and not cropped, "
    "natural realistic head-to-body proportion, "
    f"{SCENE}, "
    "very wide full half-body environmental shot, strongly zoomed out, the camera is far away, "
    "she appears small and centered occupying only the middle of the frame with generous empty space "
    "on all sides, framed from well above her head all the way down to below her hips, "
    "her whole upper body with both arms straight down and both hands fully visible at her sides, "
    "naturally lit by the warm environment light, shallow depth of field, cinematic atmospheric bokeh, "
    "photorealistic, highly detailed, natural color grading, 8k"
)
NEG = (
    "cut out, cutout, sticker, pasted, collage, floating, flat even lighting, studio backdrop, plain background, "
    "hard outline, eye bags, dark circles, puffy eyes, big nose, large nostrils, "
    "clasped hands, praying hands, folded hands, hands together, hands touching, interlocked fingers, "
    "hands in front of chest, crossed arms, arms folded, close-up, tight crop, "
    "big head, oversized head, large head, head too big, head cropped, hair cropped, cropped at the top, "
    "missing hands, hidden hands, hands behind back, cropped hands, hands out of frame, "
    "deformed hands, malformed hands, extra fingers, fused fingers, too many fingers, mutated hands, "
    "deformed, lowres, bad anatomy, ugly, blurry, extra limbs, watermark, text, open mouth, laughing"
)
FACE_FIX = (
    "a beautiful young Chinese woman face, flawless clean smooth bright under-eye area, absolutely no eye bags, "
    "smaller delicate refined nose, bright clear eyes, smooth radiant fair skin, gentle closed-mouth smile, ultra-detailed face"
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
        # 治「头大/头发被割」：weight 0.85→0.70(脸不过度主导)、end_at 1.0→0.45(controlnet 只在前半锁脸，
        # 后半让 SDXL 自然长出头发/身体/比例)。来源:InstantID 调参社区共识
        "60": {"class_type": "ApplyInstantID", "inputs": {
            "instantid": ["11", 0], "insightface": ["38", 0], "control_net": ["16", 0],
            "image": ["13", 0], "model": ["4", 0], "positive": ["39", 0], "negative": ["40", 0],
            "weight": 0.65, "start_at": 0.0, "end_at": 0.45}},
        "5":  {"class_type": "EmptyLatentImage", "inputs": {"width": GEN_W, "height": GEN_H, "batch_size": 1}},
        "3":  {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 4.5, "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": 1.0, "model": ["60", 0], "positive": ["60", 1], "negative": ["60", 2], "latent_image": ["5", 0]}},
        "8":  {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        # FaceDetailer(Impact-Pack) 暂不可用 → 直接存 InstantID 原出（RealVisXL+InstantID 脸已不错；后续 polish 可再过 FaceDetailer）
        "9":  {"class_type": "SaveImage", "inputs": {"filename_prefix": "wavesrc", "images": ["8", 0]}},
    }

if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 12345
    C = httpx.Client(trust_env=False, timeout=60)
    cid = uuid.uuid4().hex
    r = C.post(f"{COMFY}/prompt", json={"prompt": graph(seed), "client_id": cid})
    r.raise_for_status()
    pid = r.json()["prompt_id"]
    print(f"[wavesrc] seed={seed} prompt_id={pid} 生成中…")
    for _ in range(300):
        time.sleep(2)
        h = C.get(f"{COMFY}/history/{pid}").json()
        if pid in h:
            outs = h[pid]["outputs"]
            for node in outs.values():
                for im in node.get("images", []):
                    print("[wavesrc] saved:", im["filename"])
            break
    else:
        print("[wavesrc] timeout")
