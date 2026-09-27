"""EchoMimicV2 半身+手势：参考半身图 + 音频 + 手势姿态模板 → 说话带肢体语言的视频。
节点：Echo_LoadModel(V2,pose_normal_dwpose) → Echo_Predata(image+audio+pose_dir) → Echo_Sampler → VHS_VideoCombine
用法：.venv/bin/python scripts/gen_echo_v2.py <ref.png> <audio.wav> [pose_dir=pose_01] [max_sec=6]
"""
import sys, time, uuid, wave, contextlib
from pathlib import Path
import httpx

COMFY = "http://127.0.0.1:8188"
C = httpx.Client(trust_env=False, timeout=30)
REF = sys.argv[1] if len(sys.argv) > 1 else "echo_demo_ref.png"
AUD = sys.argv[2] if len(sys.argv) > 2 else "echo_demo_audio.wav"
POSE = sys.argv[3] if len(sys.argv) > 3 else "pose_01"
MAX_SEC = float(sys.argv[4]) if len(sys.argv) > 4 else 6.0

# 估音频时长 → 帧数(25fps)，首测限 MAX_SEC 加速
audp = Path.home() / "Desktop/ComfyUI/input" / AUD
sec = MAX_SEC
try:
    with contextlib.closing(wave.open(str(audp), 'r')) as w:
        sec = min(MAX_SEC, w.getnframes() / w.getframerate())
except Exception:
    pass
length = max(24, int(sec * 25))

GEST = ("The female guide stands front-facing, upper body visible, speaking warmly to the camera. "
        "Her hands gesture naturally and gently while talking, open friendly hand movements, "
        "relaxed shoulders, gentle closed-to-open mouth, looking at the camera, slight natural head motion.")
NEG = ("Gesture is bad. Unclear twisted hands. Bad hands. Bad fingers. Blurry hands. "
       "夸张手势, 手指抽搐, 重复机械动作.")

GRAPH = {
    "20": {"class_type": "Echo_LoadModel", "inputs": {
        "vae": "sd-vae-ft-mse.safetensors", "lora": "None", "denoising": True,
        "infer_mode": "pose_normal_dwpose", "lowvram": False, "teacache_offload": False,
        "block_offload": True, "use_mmgp": "None", "version": "V2"}},
    "8": {"class_type": "LoadImage", "inputs": {"image": REF}},
    "9": {"class_type": "LoadAudio", "inputs": {"audio": AUD}},
    "23": {"class_type": "Echo_Predata", "inputs": {
        "info": ["20", 1], "image": ["8", 0], "audio": ["9", 0],
        "prompt": GEST, "negative_prompt": NEG, "pose_dir": POSE,
        "width": 384, "height": 576, "fps": 25.0, "facemask_ratio": 0.1, "facecrop_ratio": 0.8,
        "length": length, "partial_video_length": 65, "draw_mouse": False, "motion_sync_": False}},
    "21": {"class_type": "Echo_Sampler", "inputs": {
        "model": ["20", 0], "emb": ["23", 0], "seed": 42, "cfg": 2.5, "steps": 20,
        "sample_rate": 16000, "context_frames": 12, "context_overlap": 3, "save_video": False}},
    "10": {"class_type": "VHS_VideoCombine", "inputs": {
        "images": ["21", 0], "frame_rate": ["21", 1], "audio": ["9", 0],
        "loop_count": 0, "filename_prefix": "echov2", "format": "video/h264-mp4",
        "pix_fmt": "yuv420p", "crf": 19, "save_metadata": True, "pingpong": False, "save_output": True}},
}


def main():
    print(f"[echo_v2] ref={REF} audio={AUD} pose={POSE} length={length}帧(~{sec:.1f}s)")
    r = C.post(f"{COMFY}/prompt", json={"prompt": GRAPH, "client_id": uuid.uuid4().hex})
    if r.status_code != 200:
        sys.exit(f"❌ 提交失败 {r.status_code}: {r.text[:500]}")
    pid = r.json()["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < 1200:
        h = C.get(f"{COMFY}/history/{pid}").json()
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                msgs = [m for m in st.get("messages", [])]
                sys.exit(f"❌ 执行报错: {msgs}")
            outs = h[pid].get("outputs", {})
            vids = []
            for n in outs.values():
                vids += n.get("gifs", []) + n.get("videos", [])
            if vids:
                v = vids[-1]
                print(f"  ✅ 视频: ~/Desktop/ComfyUI/output/{v.get('subfolder','')}/{v['filename']}")
                return
            if outs:
                print("  完成(无 video 输出?):", outs); return
        time.sleep(3)
    print("❌ 超时(看 /tmp/comfyui.log)")


if __name__ == "__main__":
    main()
