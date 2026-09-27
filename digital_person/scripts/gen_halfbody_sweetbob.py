"""InstantID 锁 face16 甜美脸 → 生成「半身露手」sweet_bob（给 EchoMimicV2 当手势参考图）。

EchoMimicV2 驱动参考图的身体+手，故参考必须是半身、双手可见、正脸。复用 comfy_face_swap
的 InstantID+FaceDetailer 工作流，只改构图提示词为 waist-up + hands visible，weight 0.85 锁身份。
用法：.venv/bin/python scripts/gen_halfbody_sweetbob.py [张数=4]
前置：ComfyUI 在 127.0.0.1:8188；face16b.png 在 ComfyUI/input。
"""
import sys, time, uuid
from pathlib import Path
import httpx

COMFY = "http://127.0.0.1:8188"
FACE = "face16b.png"
OUT = Path(__file__).resolve().parents[1] / "assets" / "avatar_facelock"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 4

# 对标 EchoMimicV2 demo 构图：近方形、头到腰、双手张开可见、人物小留边
POS = (
    "three-quarter body shot from head to mid-thigh of a beautiful young Chinese female "
    "tour guide standing and presenting, the whole figure small and fully inside the frame "
    "with clear empty space above her head and below, "
    "complete head with full short bob haircut, modern professional navy blazer with a small "
    "guide badge, both arms relaxed and fully visible, both hands resting at waist height "
    "with relaxed open fingers clearly visible, front-facing, looking straight at camera, "
    "gentle pleasant closed-mouth smile, flawless bright clean under-eye area, no eye bags, "
    "smooth radiant fair skin, small delicate refined nose, soft even lighting, "
    "plain soft-grey studio background, photorealistic, high detail, 8k"
)
NEG = (
    "cropped hair, top of head cut off, cropped arms, arms out of frame, hands out of frame, "
    "bad hands, deformed hands, extra fingers, missing fingers, fused fingers, mutated hands, "
    "eye bags, dark circles, big nose, large nostrils, close-up, head only portrait, "
    "deformed, lowres, bad anatomy, ugly, blurry, extra limbs, watermark, text, open mouth, laughing"
)
FACE_FIX = (
    "a beautiful young Chinese woman face, flawless clean smooth bright under-eye area, "
    "no eye bags, no dark circles, small delicate refined nose, small nostrils, "
    "bright clear eyes, smooth radiant fair skin, gentle closed-mouth smile, ultra-detailed face"
)

_C = httpx.Client(trust_env=False, timeout=30)


def graph(seed):
    return {
        "4":  {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealVisXL_V5.0_fp16.safetensors"}},
        "11": {"class_type": "InstantIDModelLoader", "inputs": {"instantid_file": "ip-adapter.bin"}},
        "38": {"class_type": "InstantIDFaceAnalysis", "inputs": {"provider": "CPU"}},
        "16": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "instantid_controlnet.safetensors"}},
        "13": {"class_type": "LoadImage", "inputs": {"image": FACE}},
        "39": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["4", 1]}},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        # end_at=0.5：InstantID 只在前半程锁身份，后半程放开构图（否则人脸 controlnet 强拽成正脸 portrait、裁掉手）
        "60": {"class_type": "ApplyInstantID", "inputs": {
            "instantid": ["11", 0], "insightface": ["38", 0], "control_net": ["16", 0],
            "image": ["13", 0], "model": ["4", 0], "positive": ["39", 0], "negative": ["40", 0],
            "weight": 0.8, "start_at": 0.0, "end_at": 0.5}},
        "5":  {"class_type": "EmptyLatentImage", "inputs": {"width": 832, "height": 1216, "batch_size": 1}},
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
        "9":  {"class_type": "SaveImage", "inputs": {"filename_prefix": "halfbody_sweetbob", "images": ["71", 0]}},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    comfy_out = Path.home() / "Desktop/ComfyUI/output"
    for i in range(N):
        seed = 7000 + i * 137
        print(f"[{i+1}/{N}] seed={seed} 提交...")
        pid = _C.post(f"{COMFY}/prompt", json={"prompt": graph(seed), "client_id": uuid.uuid4().hex}).json()["prompt_id"]
        t0 = time.time()
        while time.time() - t0 < 240:
            h = _C.get(f"{COMFY}/history/{pid}").json()
            if pid in h:
                st = h[pid].get("status", {})
                if st.get("status_str") == "error":
                    print("  ❌ 报错:", st.get("messages", [])[-2:]); break
                outs = h[pid].get("outputs", {})
                imgs = [im for n in outs.values() for im in n.get("images", [])]
                if imgs:
                    src = comfy_out / imgs[-1].get("subfolder", "") / imgs[-1]["filename"]
                    dst = OUT / f"halfbody_sweetbob_{i+1}.png"
                    dst.write_bytes(Path(src).read_bytes())
                    print(f"  ✅ {dst}")
                    break
            time.sleep(2)


if __name__ == "__main__":
    main()
