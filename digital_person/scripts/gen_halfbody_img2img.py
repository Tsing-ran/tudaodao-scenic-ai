"""半身 sweet_bob（img2img 法）：以 EchoMimic 张开双手半身底图为构图，img2img + InstantID 换脸。

纯文生图 InstantID 老把构图拽成正脸胸像、出不了手；改 img2img——构图/手/双臂来自底图(可靠)，
脸来自 InstantID 锁 face16，服装/发型由提示词+denoise 控制。产物再合成到 16:9。
用法：.venv/bin/python scripts/gen_halfbody_img2img.py [denoise=0.65] [seed基=8000] [张数=2]
"""
import sys, time, uuid
from pathlib import Path
import httpx

COMFY = "http://127.0.0.1:8188"
FACE = "face16b.png"
BASE = "pose_base_0014.png"               # 张开双手半身底图（EchoMimic demo）
DENOISE = float(sys.argv[1]) if len(sys.argv) > 1 else 0.65
SEED0 = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
N = int(sys.argv[3]) if len(sys.argv) > 3 else 2
OUT = Path(__file__).resolve().parents[1] / "assets" / "avatar_facelock"

POS = (
    "a beautiful young Chinese female tour guide, short bob haircut, "
    "modern professional navy blazer with a small guide badge over a white top, "
    "standing front-facing, upper body with both arms open and both hands visible, "
    "welcoming open-hand gesture, gentle pleasant closed-mouth smile, "
    "flawless bright clean under-eye area, no eye bags, smooth radiant fair skin, "
    "small delicate refined nose, soft even lighting, plain soft-grey background, "
    "photorealistic, high detail, 8k"
)
NEG = (
    "hair over eyes, bangs covering eyes, hair covering face, dark band across face, "
    "blindfold, mask over eyes, censor bar, ponytail, tied hair, long hair, "
    "bad hands, deformed hands, extra fingers, missing fingers, fused fingers, mutated hands, "
    "eye bags, dark circles, big nose, large nostrils, "
    "deformed, lowres, bad anatomy, ugly, blurry, watermark, text, open mouth, laughing"
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
        "80": {"class_type": "LoadImage", "inputs": {"image": BASE}},
        "81": {"class_type": "VAEEncode", "inputs": {"pixels": ["80", 0], "vae": ["4", 2]}},
        "39": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["4", 1]}},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "60": {"class_type": "ApplyInstantID", "inputs": {
            "instantid": ["11", 0], "insightface": ["38", 0], "control_net": ["16", 0],
            "image": ["13", 0], "model": ["4", 0], "positive": ["39", 0], "negative": ["40", 0],
            "weight": 0.8, "start_at": 0.0, "end_at": 1.0}},
        "3":  {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 4.5, "sampler_name": "ddpm", "scheduler": "karras",
            "denoise": DENOISE, "model": ["60", 0], "positive": ["60", 1], "negative": ["60", 2],
            "latent_image": ["81", 0]}},
        "8":  {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "72": {"class_type": "CLIPTextEncode", "inputs": {"text": FACE_FIX, "clip": ["4", 1]}},
        "70": {"class_type": "UltralyticsDetectorProvider", "inputs": {"model_name": "bbox/face_yolov8m.pt"}},
        "71": {"class_type": "FaceDetailer", "inputs": {
            "image": ["8", 0], "model": ["4", 0], "clip": ["4", 1], "vae": ["4", 2],
            "positive": ["72", 0], "negative": ["40", 0], "bbox_detector": ["70", 0],
            "guide_size": 768, "guide_size_for": True, "max_size": 1024, "seed": seed + 7,
            "steps": 25, "cfg": 5.0, "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": 0.45, "feather": 5, "noise_mask": True, "force_inpaint": True,
            "bbox_threshold": 0.5, "bbox_dilation": 10, "bbox_crop_factor": 3.0,
            "sam_detection_hint": "center-1", "sam_dilation": 0, "sam_threshold": 0.93,
            "sam_bbox_expansion": 0, "sam_mask_hint_threshold": 0.7,
            "sam_mask_hint_use_negative": "False", "drop_size": 10, "wildcard": "", "cycle": 1}},
        "9":  {"class_type": "SaveImage", "inputs": {"filename_prefix": "hb_i2i", "images": ["71", 0]}},
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    comfy_out = Path.home() / "Desktop/ComfyUI/output"
    for i in range(N):
        seed = SEED0 + i * 131
        print(f"[{i+1}/{N}] seed={seed} denoise={DENOISE} 提交...", flush=True)
        pid = _C.post(f"{COMFY}/prompt", json={"prompt": graph(seed), "client_id": uuid.uuid4().hex}).json()["prompt_id"]
        t0 = time.time()
        while time.time() - t0 < 240:
            h = _C.get(f"{COMFY}/history/{pid}").json()
            if pid in h:
                st = h[pid].get("status", {})
                if st.get("status_str") == "error":
                    print("  ❌", st.get("messages", [])[-2:], flush=True); break
                imgs = [im for n in h[pid].get("outputs", {}).values() for im in n.get("images", [])]
                if imgs:
                    src = comfy_out / imgs[-1].get("subfolder", "") / imgs[-1]["filename"]
                    dst = OUT / f"hb_i2i_d{int(DENOISE*100)}_{i+1}.png"
                    dst.write_bytes(Path(src).read_bytes())
                    print(f"  ✅ {dst}", flush=True); break
            time.sleep(2)


if __name__ == "__main__":
    main()
