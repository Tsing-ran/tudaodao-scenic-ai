"""ComfyUI InstantID「同脸换装·人景一体」：锁 face16 甜美脸身份，把【该脸 + 指定服装 + 景区场景】
一次性协调生成成一张图（非抠图合成）。供「换装衣橱」用——同一个人换 6 套衣服。

为什么不用万相：万相 t2i 每次是不同的脸，锁不住"还是这张脸只换了衣服"。InstantID 锁身份后
人与场景一体生成 → 同脸、不抠图、自然在景中。

前置：ComfyUI 127.0.0.1:8188；参考脸 ComfyUI/input/face16b.png；RealVisXL + InstantID + FaceDetailer。
用法：.venv/bin/python scripts/gen_avatar_outfit_inscene.py [scenic=lingshan] [outfit ...]
产物：assets/avatar_outfit_inscene/sweet_outfit_<outfit>__<scenic>__{16x9,9x16}.png（验观感后部署进 ditto_avatars/）
"""
import sys
import time
import uuid
from pathlib import Path

import httpx
from PIL import Image

COMFY = "http://127.0.0.1:8188"
FACE = "face16b.png"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "avatar_outfit_inscene"

# 输出比例 → (SDXL 生成分桶 GEN, 最终底板尺寸 FINAL)
ASPECTS = {
    "16x9": ((1344, 768), (1280, 720)),
    "9x16": ((768, 1344), (720, 1280)),
}

# 复用 gen_avatar_inscene.py 的 8 景区场景描述
SCENES = {
    "lingshan":   "standing outdoors in the misty green mountains of a Chinese Buddhist holy land, a distant giant buddha statue and temple pagoda silhouette softly veiled in morning fog, warm golden sunrise light, incense haze",
    "nihuawan":   "standing in a Tang-dynasty style Zen water town at dusk, white walls and dark-tiled wooden eaves behind, warm glowing lanterns, soft cherry blossom bokeh",
    "xihu":       "standing by misty West Lake, distant Leifeng pagoda and arched bridge over calm misty water, soft grey-green atmospheric haze",
    "huangshan":  "standing on a Huangshan mountain platform above a rolling sea of clouds, distant granite peaks and a welcoming pine silhouette, golden glow",
    "gugong":     "standing in the Forbidden City, golden glazed-tile palace eaves and red walls behind, golden ginkgo leaves, soft morning light",
    "zhangjiajie": "standing among the towering quartz sandstone pillars of Zhangjiajie shrouded in drifting mist, lush green, ethereal",
    "bingmayong": "standing in the warm amber-lit Terracotta Army museum hall, blurred terracotta warrior pit deep behind in soft bokeh",
    "mogaoku":    "standing before the golden Mingsha sand dunes and Crescent Lake of Dunhuang, warm sand tones, clear dawn sky",
}

# 6 套服装描述（同一张 face16 甜美脸，只换衣服）
OUTFITS = {
    "qipao":  "wearing an elegant fitted traditional Chinese cheongsam qipao dress",
    "hanfu":  "wearing a graceful flowing traditional Chinese hanfu robe",
    "blazer": "wearing a smart navy-blue professional blazer suit with a small guide badge",
    "ethnic": "wearing an ornate colorful Chinese ethnic-minority costume with a delicate silver headdress",
    "vest":   "wearing a tidy scenic-area guide vest uniform over a light shirt",
    "coat":   "wearing a warm elegant winter coat with a soft scarf",
}

POS_TMPL = (
    "a beautiful young Chinese female tour guide, short chin-length bob haircut with side-swept bangs, "
    "{outfit}, "
    "gentle pleasant closed-mouth smile, flawless clean bright under-eye area, absolutely no eye bags, "
    "smooth radiant fair skin, small delicate refined nose, "
    "head level and straight, chin slightly tucked, looking directly at the camera, "
    "{scene}, "
    "medium shot from the waist up, the whole head and face clearly visible with headroom above, "
    "she is naturally lit by the warm environment light, "
    "shallow depth of field, cinematic atmospheric bokeh background, "
    "photorealistic, highly detailed, natural color grading, 8k"
)
NEG = (
    "cropped head, head out of frame, top of head cut off, face cut off, headless, faceless, low angle, "
    "cut out, cutout, sticker, pasted, collage, floating, flat even lighting, studio backdrop, "
    "plain background, hard outline, eye bags, dark circles, puffy eyes, big nose, large nostrils, "
    "deformed, lowres, bad anatomy, ugly, blurry, extra limbs, watermark, text, open mouth, laughing"
)
FACE_FIX_POS = (
    "a beautiful young Chinese woman face, flawless clean smooth bright under-eye area, "
    "absolutely no eye bags, no dark circles, smaller delicate refined nose, small narrow nostrils, "
    "bright clear eyes, smooth radiant fair skin, gentle closed-mouth smile, ultra-detailed face"
)

_C = httpx.Client(trust_env=False, timeout=30)


def build_graph(positive, seed, gen_w, gen_h):
    return {
        "4":  {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": "RealVisXL_V5.0_fp16.safetensors"}},
        "11": {"class_type": "InstantIDModelLoader", "inputs": {"instantid_file": "ip-adapter.bin"}},
        "38": {"class_type": "InstantIDFaceAnalysis", "inputs": {"provider": "CPU"}},
        "16": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": "instantid_controlnet.safetensors"}},
        "13": {"class_type": "LoadImage", "inputs": {"image": FACE}},
        "39": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["4", 1]}},
        "40": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
        "60": {"class_type": "ApplyInstantID", "inputs": {
            "instantid": ["11", 0], "insightface": ["38", 0], "control_net": ["16", 0],
            "image": ["13", 0], "model": ["4", 0], "positive": ["39", 0], "negative": ["40", 0],
            "weight": 0.85, "start_at": 0.0, "end_at": 1.0}},
        "5":  {"class_type": "EmptyLatentImage", "inputs": {"width": gen_w, "height": gen_h, "batch_size": 1}},
        "3":  {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": 30, "cfg": 4.5, "sampler_name": "dpmpp_2m", "scheduler": "karras",
            "denoise": 1.0, "model": ["60", 0], "positive": ["60", 1], "negative": ["60", 2],
            "latent_image": ["5", 0]}},
        "8":  {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "72": {"class_type": "CLIPTextEncode", "inputs": {"text": FACE_FIX_POS, "clip": ["4", 1]}},
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
        "9":  {"class_type": "SaveImage", "inputs": {"filename_prefix": "outfit_inscene", "images": ["71", 0]}},
    }


def gen_one(outfit, scenic, asp):
    (gen_w, gen_h), (fw, fh) = ASPECTS[asp]
    pos = POS_TMPL.format(outfit=OUTFITS[outfit], scene=SCENES[scenic])
    seed = (abs(hash(f"{outfit}{scenic}{asp}")) % 2_000_000_000)
    cid = uuid.uuid4().hex
    print(f"[{outfit}__{scenic}__{asp}] InstantID 生成中（{gen_w}x{gen_h}）…", flush=True)
    r = _C.post(f"{COMFY}/prompt", json={"prompt": build_graph(pos, seed, gen_w, gen_h), "client_id": cid})
    if r.status_code != 200:
        print(f"  ❌ 提交失败 {r.status_code} {r.text[:200]}", flush=True); return
    pid = r.json()["prompt_id"]
    img_info = None
    for _ in range(120):
        time.sleep(2)
        h = _C.get(f"{COMFY}/history/{pid}").json()
        if pid in h:
            outs = h[pid]["outputs"]
            if "9" in outs and outs["9"].get("images"):
                img_info = outs["9"]["images"][0]; break
    if not img_info:
        print("  ❌ 超时未出图", flush=True); return
    data = _C.get(f"{COMFY}/view", params={"filename": img_info["filename"],
                  "subfolder": img_info.get("subfolder", ""), "type": "output"}).content
    OUT.mkdir(parents=True, exist_ok=True)
    raw = OUT / f"sweet_outfit_{outfit}__{scenic}__{asp}.raw.png"
    raw.write_bytes(data)
    img = Image.open(raw).convert("RGB").resize((fw, fh), Image.LANCZOS)
    final = OUT / f"sweet_outfit_{outfit}__{scenic}__{asp}.png"
    img.save(final)
    raw.unlink(missing_ok=True)
    print(f"  ✅ {final}", flush=True)


def main():
    scenic = sys.argv[1] if len(sys.argv) > 1 else "lingshan"
    if scenic not in SCENES:
        sys.exit(f"未知景区 {scenic}")
    outfits = sys.argv[2:] or list(OUTFITS)
    for o in outfits:
        if o not in OUTFITS:
            print(f"  跳过未知服装 {o}", flush=True); continue
        for asp in ASPECTS:
            gen_one(o, scenic, asp)
    print("完成 →", OUT)


if __name__ == "__main__":
    main()
