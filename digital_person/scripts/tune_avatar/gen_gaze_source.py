"""InstantID 锁脸16 → 生成"头略低、视线向下看镜头"的源图（治 EchoMimic 眼神上飘）。
自然重绘(非像素挪移)，匹配同款 波波头/米色高领/灰背景 保持与直播形象一致。
用法: gen_gaze_source.py <face_ref.png in input/> [n_seeds=3]
"""
import sys, time, uuid
from pathlib import Path
import httpx

COMFY = "http://127.0.0.1:8188"
FACE = sys.argv[1] if len(sys.argv) > 1 else "face_ref.png"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 3
OUT = Path("/tmp/tune")
_C = httpx.Client(trust_env=False, timeout=30)

# 强拉远全身/长镜 + 人物明显压低（头更小、头顶大片留白）+ 下视；纯生成不做后处理
POS = ("a full body long shot of a beautiful young Chinese female tour guide standing, "
       "the entire figure small and positioned in the lower portion of the frame, "
       "her whole head and full short bob hairstyle completely visible, "
       "a very large area of empty plain grey space above her head, abundant generous headroom, "
       "wide shot with the head occupying only the upper-middle area, "
       "wearing a warm cozy soft camel-beige chunky knitted turtleneck sweater, "
       "warm inviting cozy knitwear, soft warm tones, heartwarming gentle vibe, "
       "gentle pleasant closed-mouth smile, "
       "flawless bright under-eye area, absolutely no eye bags, smooth radiant fair skin, "
       "small delicate refined nose, "
       "head tilted distinctly downward and gently bowed, chin lowered toward the chest, "
       "eyes gazing softly downward toward the camera lens, demure lowered gaze looking down, "
       "plain light-grey studio background, soft lighting, photorealistic, 8k")
NEG = ("cropped head, cut off hair, head cut at the top, hair touching the top edge, "
       "flat top hair, top of head out of frame, close-up, "
       "looking up, eyes rolled upward, chin raised, head tilted back, gazing at ceiling, "
       "eye bags, dark circles, big nose, large nostrils, deformed, lowres, bad anatomy, "
       "ugly, blurry, watermark, text, open mouth, laughing")
FACE_FIX = ("a beautiful young Chinese woman face, flawless clean bright under-eye area, "
            "no eye bags, small refined nose, eyes gazing gently downward, smooth fair skin, "
            "gentle closed-mouth smile, ultra-detailed high quality face")


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
            "weight": 0.8, "start_at": 0.0, "end_at": 1.0}},
        "5":  {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1344, "batch_size": 1}},
        "3":  {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 4.5, "sampler_name": "ddpm", "scheduler": "karras",
            "denoise": 1.0, "model": ["60", 0], "positive": ["60", 1], "negative": ["60", 2],
            "latent_image": ["5", 0]}},
        "8":  {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "72": {"class_type": "CLIPTextEncode", "inputs": {"text": FACE_FIX, "clip": ["4", 1]}},
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
        "9":  {"class_type": "SaveImage", "inputs": {"filename_prefix": "gazesrc", "images": ["71", 0]}},
    }


cid = uuid.uuid4().hex
for k in range(N):
    seed = 2000 + k * 13
    pid = _C.post(f"{COMFY}/prompt", json={"prompt": graph(seed), "client_id": cid}).json()["prompt_id"]
    print(f"[{k+1}/{N}] seed={seed} 提交 {pid}")
    t0 = time.time()
    while time.time() - t0 < 300:
        h = _C.get(f"{COMFY}/history/{pid}").json()
        if pid in h:
            imgs = [im for node in h[pid].get("outputs", {}).values() for im in node.get("images", [])]
            if imgs:
                im = imgs[0]
                r = _C.get(f"{COMFY}/view", params={"filename": im["filename"], "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")})
                dst = OUT / f"gaze_src_{k}.png"
                dst.write_bytes(r.content)
                print(f"  ✅ {dst}")
                break
        time.sleep(2)
print("DONE_GEN")
