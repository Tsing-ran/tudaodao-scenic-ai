"""ComfyUI 局部重绘补全 sweet_bob 被切的肩臂 → 完整 16:9 人像（保脸/衣/光不变）。
输入：scripts/prep_outpaint.py 产的 画布(原图人物在空灵底) + 遮罩(白=待补全肩臂+背景)。
仅遮罩白区重绘 → 她的脸/中央躯干原样保留，外缘补成完整自然肩臂 + 空灵背景。
用法：.venv/bin/python scripts/gen_avatar_outpaint.py [seed]
"""
import sys, time, uuid
from pathlib import Path
import httpx
from PIL import Image

COMFY = "http://127.0.0.1:8188"
ROOT = Path(__file__).resolve().parents[1]
DITTO_DIR = Path.home() / "Desktop/LiveTalking/data/ditto_avatars"
REVIEW = ROOT / "assets/ui_shots"
CKPT = "realisticVision_v51.safetensors"   # 复用已下的写实底模

POS = ("a beautiful young Chinese woman wearing a cream-colored turtleneck sweater, "
       "complete natural rounded shoulders and arms, full upper body, well lit, "
       "soft bright light grey ethereal studio background, photorealistic, soft even lighting, high quality")
NEG = ("cut off arms, amputated arms, cropped shoulders, harsh vertical edge, missing limbs, "
       "deformed, extra limbs, dark shadows, lowres, bad anatomy, blurry, watermark, text")


def graph(seed):
    return {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "13": {"class_type": "LoadImage", "inputs": {"image": "outpaint_canvas.png"}},
        "14": {"class_type": "LoadImage", "inputs": {"image": "outpaint_mask.png"}},
        "15": {"class_type": "ImageToMask", "inputs": {"image": ["14", 0], "channel": "red"}},
        "16": {"class_type": "VAEEncodeForInpaint", "inputs": {
            "pixels": ["13", 0], "vae": ["4", 2], "mask": ["15", 0], "grow_mask_by": 12}},
        "39": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["4", 1]}},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "3": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 6.0, "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": 1.0, "model": ["4", 0], "positive": ["39", 0], "negative": ["40", 0],
            "latent_image": ["16", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "outpaint", "images": ["8", 0]}},
    }


def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    c = httpx.Client(trust_env=False, timeout=30)
    print("[outpaint] 补全肩臂中…")
    r = c.post(f"{COMFY}/prompt", json={"prompt": graph(seed), "client_id": uuid.uuid4().hex})
    if r.status_code != 200:
        sys.exit(f"❌ 提交失败 {r.status_code}: {r.text[:300]}")
    pid = r.json()["prompt_id"]
    t0 = time.time(); imgs = []
    while time.time() - t0 < 240:
        h = c.get(f"{COMFY}/history/{pid}").json()
        if pid in h:
            if h[pid].get("status", {}).get("status_str") == "error":
                sys.exit(f"❌ 执行报错: {h[pid]['status']}")
            for n in h[pid].get("outputs", {}).values():
                imgs += n.get("images", [])
            if imgs:
                break
        time.sleep(2)
    if not imgs:
        sys.exit("❌ 超时（看 /tmp/comfyui.log）")
    im = imgs[-1]
    raw = c.get(f"{COMFY}/view", params={"filename": im["filename"],
                "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")}).content
    REVIEW.mkdir(parents=True, exist_ok=True)
    out = REVIEW / "outpaint_result.png"
    out.write_bytes(raw)
    Image.open(out).convert("RGB").resize((1280, 720), Image.LANCZOS).save(DITTO_DIR / "sweet_bob_clean.png")
    print(f"  ✅ {out}")


if __name__ == "__main__":
    main()
