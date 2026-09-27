"""ComfyUI IC-Light fbc：把确定的 sweet_bob 本人按景区背景重打光、自然融入 → Ditto 横版底板。

为什么用 IC-Light（取代 InstantID 生成）：
  用户硬要求=**保住选定的那张 sweet_bob 本人本衣**（InstantID 会生成相似新人，作废）。
  IC-Light 不重画身份，只「重打光 + 融合」：输入 前景(确定的 sweet_bob 灰底主体) +
  背景(景区场景) → 按背景光照重打光主体并融入 → 身份/服装保留、光照统一、无抠图边。

链路（节点结构读自 ComfyUI-IC-Light/nodes.py）：
  CheckpointLoaderSimple(SD1.5 写实底模) → LoadAndApplyICLightUnet(打 fbc 补丁)
  前景图→VAEEncode→fg潜 ; 背景图→VAEEncode→bg潜
  ICLightConditioning(pos,neg,vae,foreground=fg潜,opt_background=bg潜) →(pos,neg,empty_latent)
  KSampler → VAEDecode → SaveImage

前置：ComfyUI 跑着且已加载 IC-Light 节点；ComfyUI/input/ 有 iclight_fg.png + iclight_bg_<scenic>.png
  （由 scripts/prep_iclight_fg.py 产）；models/unet/IC-Light/iclight_sd15_fbc.safetensors；SD1.5 ckpt。
用法：.venv/bin/python scripts/gen_avatar_iclight.py [scenic=lingshan] [seed]
"""
import sys
import time
import uuid
from pathlib import Path

import httpx
from PIL import Image

COMFY = "http://127.0.0.1:8188"
ROOT = Path(__file__).resolve().parents[1]
DITTO_DIR = Path.home() / "Desktop/LiveTalking/data/ditto_avatars"
REVIEW = ROOT / "assets" / "ui_shots"
SD15_CKPT = "realisticVision_v51.safetensors"
ICLIGHT_UNET = "IC-Light/iclight_sd15_fbc.safetensors"
LS_W, LS_H = 1280, 720

# 景区光照氛围（IC-Light 用 prompt 引导重打光的方向/色温）。
# 关键：强调"正面暖光、柔和均匀、脸被照亮"——治 fbc 只从背景(身后)打光导致正脸阴影发青。
LIGHT = {
    "lingshan":   "soft warm golden frontal light gently illuminating her face evenly, bright warm sunlight, flattering soft illumination, warm natural skin tone, no harsh shadows on the face, misty mountain atmosphere",
    "nihuawan":   "warm amber lantern glow at dusk, soft ambient evening light",
    "xihu":       "soft diffused grey-green misty daylight, gentle overcast light",
    "huangshan":  "bright golden sunrise glow above a sea of clouds, crisp natural light",
    "gugong":     "warm soft morning sunlight, golden hour palace ambiance",
    "zhangjiajie": "soft misty diffused daylight among stone peaks",
    "bingmayong": "warm amber museum spotlighting, indoor ambient glow",
    "mogaoku":    "warm golden desert dawn light, clear soft sunlight",
}
NEG = ("cyan skin, blue face, teal shadows, green face, color cast, harsh dark shadows on face, "
       "underexposed face, shadowed face, ghostly, transparent, faded, washed out, desaturated, "
       "cut out, sticker, pasted, harsh outline, deformed, lowres, bad anatomy, blurry, watermark, text")


def build_graph(scenic, seed):
    pos = (f"a beautiful young Chinese female tour guide, naturally standing in the scene, "
           f"{LIGHT[scenic]}, warm and clearly lit face, solid and vivid, "
           f"photorealistic, detailed, cinematic, best quality")
    return {
        "4":  {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": SD15_CKPT}},
        "20": {"class_type": "LoadAndApplyICLightUnet", "inputs": {"model": ["4", 0], "model_path": ICLIGHT_UNET}},
        "13": {"class_type": "LoadImage", "inputs": {"image": "iclight_fg.png"}},
        "14": {"class_type": "LoadImage", "inputs": {"image": f"iclight_bg_{scenic}.png"}},
        "15": {"class_type": "VAEEncode", "inputs": {"pixels": ["13", 0], "vae": ["4", 2]}},
        "16": {"class_type": "VAEEncode", "inputs": {"pixels": ["14", 0], "vae": ["4", 2]}},
        "39": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["4", 1]}},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "21": {"class_type": "ICLightConditioning", "inputs": {
            "positive": ["39", 0], "negative": ["40", 0], "vae": ["4", 2],
            "foreground": ["15", 0], "multiplier": 0.18215, "opt_background": ["16", 0]}},
        "3":  {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 3.5, "sampler_name": "dpmpp_2m_sde", "scheduler": "karras",
            "denoise": 1.0, "model": ["20", 0], "positive": ["21", 0], "negative": ["21", 1],
            "latent_image": ["21", 2]}},
        "8":  {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        # DetailTransfer：从原图 sweet_bob(node13) 提取高频纹理/细节贴回重打光结果(node8)
        # → 恢复实体清晰度、消除"发灰/鬼魂"，但只贴纹理不贴低频光照(不破坏重打光)
        "30": {"class_type": "DetailTransfer", "inputs": {
            "target": ["8", 0], "source": ["13", 0], "mode": "add",
            "blur_sigma": 1.0, "blend_factor": 1.0}},
        "9":  {"class_type": "SaveImage", "inputs": {"filename_prefix": "iclight", "images": ["30", 0]}},
    }


def main():
    scenic = sys.argv[1] if len(sys.argv) > 1 else "lingshan"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 20260613
    if scenic not in LIGHT:
        sys.exit(f"未知景区 {scenic}")
    c = httpx.Client(trust_env=False, timeout=30)
    print(f"[iclight] {scenic} 重打光融合中（保 sweet_bob 本人，按背景重打光）…")
    r = c.post(f"{COMFY}/prompt", json={"prompt": build_graph(scenic, seed), "client_id": uuid.uuid4().hex})
    if r.status_code != 200:
        sys.exit(f"❌ 提交失败 {r.status_code}: {r.text[:300]}")
    pid = r.json()["prompt_id"]
    t0 = time.time()
    imgs = []
    while time.time() - t0 < 300:
        h = c.get(f"{COMFY}/history/{pid}").json()
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                sys.exit(f"❌ 执行报错: {st}")
            for node in h[pid].get("outputs", {}).values():
                imgs += node.get("images", [])
            if imgs:
                break
        time.sleep(2)
    if not imgs:
        sys.exit("❌ 超时无输出（看 ComfyUI 日志 /tmp/comfyui.log）")
    im = imgs[-1]
    raw = c.get(f"{COMFY}/view", params={"filename": im["filename"],
                "subfolder": im.get("subfolder", ""), "type": im.get("type", "output")}).content
    REVIEW.mkdir(parents=True, exist_ok=True)
    review = REVIEW / f"iclight_{scenic}.png"
    review.write_bytes(raw)
    img = Image.open(review).convert("RGB").resize((LS_W, LS_H), Image.LANCZOS)
    img.save(review)
    DITTO_DIR.mkdir(parents=True, exist_ok=True)
    img.save(DITTO_DIR / f"sweet_bob_iclight_{scenic}.png")
    print(f"  ✅ 审图 {review}")
    print(f"  ✅ Ditto 底板 sweet_bob_iclight_{scenic}")


if __name__ == "__main__":
    main()
