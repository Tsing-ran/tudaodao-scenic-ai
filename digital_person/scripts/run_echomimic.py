"""驱动 ComfyUI 跑 EchoMimic V3 flash：单张肖像 + 音频 → 整脸会动的说话头（演示视频英雄镜头）。
用法: python run_echomimic.py <portrait.png> <audio.wav> <out.mp4> [partial_video_length]
前置: ComfyUI 在 127.0.0.1:8188 运行，肖像/音频已在 ComfyUI/input/。
"""
import json, os, sys, time, uuid, random
from pathlib import Path
import httpx

COMFY = "http://127.0.0.1:8188"
# 驱动姿态模板（可选 pose_01~04 等）；治眼神上飘时可扫不同 pose 找平视的那个
POSE_DIR = os.getenv("ECHO_POSE_DIR", "pose_01")
C = httpx.Client(trust_env=False, timeout=60)

PORTRAIT = sys.argv[1] if len(sys.argv) > 1 else "sweet_bob_portrait.png"
AUDIO    = sys.argv[2] if len(sys.argv) > 2 else "hero_short.wav"
OUT      = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("/tmp/echomimic_hero.mp4")
PVL      = int(sys.argv[4]) if len(sys.argv) > 4 else 65   # 11.6G 用 65；够则升 97
LENGTH   = int(sys.argv[5]) if len(sys.argv) > 5 else 251  # 生成帧数上限（25fps）→ ≥ 音频时长*25

# 神态对标：端庄女主播、温和浅笑、稳稳对视镜头。
# 眼神：强约束"直视镜头/瞳孔居中/下巴略收"以治 EchoMimic 的眼球上翻+抬头偏置；
# 删掉"eyes move naturally"（易诱发 gaze 漂移）。
PROMPT = ("A professional female news anchor speaking directly to the camera, calm and warm. "
          "Her eyes look straight into the camera lens with steady gentle eye contact, "
          "pupils centered and level, iris in the middle of the eyes, gaze meeting the viewer. "
          "Chin slightly lowered, head level and facing forward, not tilted back. "
          "Gentle pleasant closed-to-slightly-open mouth while talking, natural facial "
          "expressions, elegant and dignified.")
NEG = ("looking up, eyes rolled upward, eyes looking at the ceiling, sclera visible under the iris, "
       "gaze drifting up, chin raised, head tilted back, googly eyes, 眼睛向上看, 翻白眼, 抬头, "
       "Gesture is bad. Strange and twisted hands. Bad hands. Bad fingers. blurry, "
       "distorted face, frozen stiff face, 夸张表情, 头部剧烈摇晃, 闭眼, 鬼脸.")


def build_graph(seed):
    return {
        "5":  {"class_type": "CLIPLoader", "inputs": {
                 "clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "15": {"class_type": "CLIPVisionLoader", "inputs": {"clip_name": "clip_vision_h.safetensors"}},
        "8":  {"class_type": "LoadImage", "inputs": {"image": PORTRAIT}},
        "9":  {"class_type": "LoadAudio", "inputs": {"audio": AUDIO}},
        "20": {"class_type": "Echo_LoadModel", "inputs": {
                 "vae": "Wan2.1_VAE.pth", "lora": "None", "denoising": True,
                 "infer_mode": "audio_drived", "lowvram": True, "teacache_offload": False,
                 "block_offload": True, "use_mmgp": "None", "version": "V3_flash"}},
        "23": {"class_type": "Echo_Predata", "inputs": {
                 "info": ["20", 1], "image": ["8", 0], "audio": ["9", 0],
                 "prompt": PROMPT, "negative_prompt": NEG, "pose_dir": POSE_DIR,
                 # facecrop_ratio=1.0 → 不裁切（放大系数=1/ratio，0.8 会 1.25× 放大削头顶）。
                 # 配套：肖像须预裁成 2:3（如 720×1080）匹配 512×768，避免拉伸畸变。
                 "width": 512, "height": 768, "fps": 25.0,
                 "facemask_ratio": 0.1, "facecrop_ratio": 1.0, "length": LENGTH,
                 "partial_video_length": PVL, "draw_mouse": False, "motion_sync_": False,
                 "clip": ["5", 0], "clip_vision": ["15", 0]}},
        "21": {"class_type": "Echo_Sampler", "inputs": {
                 "model": ["20", 0], "emb": ["23", 0], "seed": seed, "cfg": 6.0,
                 "steps": 8, "sample_rate": 16000, "context_frames": 12,
                 "context_overlap": 3, "save_video": False}},
        "24": {"class_type": "CreateVideo", "inputs": {"images": ["21", 0], "fps": 25.0, "audio": ["9", 0]}},
        "25": {"class_type": "SaveVideo", "inputs": {
                 "video": ["24", 0], "filename_prefix": "echomimic_hero",
                 "format": "auto", "codec": "auto"}},
    }


def main():
    cid = uuid.uuid4().hex
    seed = random.randint(0, 2**31)
    g = build_graph(seed)
    r = C.post(f"{COMFY}/prompt", json={"prompt": g, "client_id": cid})
    if r.status_code != 200:
        print("❌ 提交失败:", r.status_code, r.text[:2000]); sys.exit(1)
    pid = r.json()["prompt_id"]
    print(f"已提交 prompt_id={pid} seed={seed} PVL={PVL}，开始轮询（首跑要加载~15G模型，耐心）…")
    t0 = time.time()
    while time.time() - t0 < 1800:
        h = C.get(f"{COMFY}/history/{pid}").json()
        if pid in h:
            entry = h[pid]
            outs = entry.get("outputs", {})
            # 找视频输出
            for node in outs.values():
                for key in ("videos", "images", "gifs"):
                    for f in node.get(key, []):
                        if f.get("filename", "").endswith((".mp4", ".webm", ".mkv")) or key == "videos":
                            rv = C.get(f"{COMFY}/view", params={
                                "filename": f["filename"], "subfolder": f.get("subfolder", ""),
                                "type": f.get("type", "output")})
                            OUT.write_bytes(rv.content)
                            print(f"✅ 视频已存: {OUT}  ({len(rv.content)} bytes)  用时 {time.time()-t0:.0f}s")
                            return
            status = entry.get("status", {})
            if status.get("status_str") == "error" or status.get("completed") is False:
                print("❌ 执行出错:", json.dumps(status, ensure_ascii=False)[:2000]); return
            # 完成但没找到视频
            print("⚠️ 完成但未找到视频输出，outputs=", json.dumps(outs, ensure_ascii=False)[:1500]); return
        time.sleep(3)
    print("❌ 超时")


if __name__ == "__main__":
    main()
