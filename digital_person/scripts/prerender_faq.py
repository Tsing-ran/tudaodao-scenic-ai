"""L1 高频问答视频缓存 · 预渲染脚本（在 GPU box 上跑，需数字人全栈在线）。

为 manifest 里每条高频问答渲染一段「数字人说出该答案」的成品视频片段，存到
webapp/public/faq/<id>.mp4 并回写 clip 路径。命中时前端直接播这段成品 → 0 GPU·0 LLM·<0.5s。

原理（复用既有 录对比片 流水线）：
  ffmpeg 抓 SRS 的 HTTP-FLV 直播流  ←  桥接 /live/say 驱动数字人说出答案
  按估算说话时长截取 → 转 mp4 → 存盘 → 回写 manifest → 调 /live/faq/reload 热生效

前置（与演示同一套，见 CLAUDE.md「本地全栈启动顺序」）：
  SRS(docker) + LiveTalking(--avatar sweet_bob --batch_size 4) + 桥接(:9000)

用法：
  python scripts/prerender_faq.py --scenic lingshan            # 渲染该景区全部 FAQ
  python scripts/prerender_faq.py --scenic lingshan --only ticket   # 只渲染某条
  python scripts/prerender_faq.py --regen-answer               # 答案改从 RAG 实时取(否则用清单里写好的)
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
FAQ_DIR = ROOT / "webapp" / "public" / "faq"
MANIFEST = FAQ_DIR / "manifest.json"
BRIDGE = "http://localhost:9000"
SRS_FLV = "http://localhost:8080/live/livestream.flv"
SPEAK_CPS = 3.8      # 说话速率字/秒（Qwen-TTS rate 0.9~0.93 实测偏慢，保守估计防截断）
LEAD = 1.2           # ffmpeg 先连上 SRS 的提前量（capture-first）
TAIL = 2.5           # 尾缓冲，吸收 TTS 首音延迟与收尾


def estimate_window(text: str) -> float:
    return max(4.0, LEAD + len(text) / SPEAK_CPS + TAIL)


# trust_env=False：全调 localhost，绕开系统 SOCKS 代理（clash :12334，httpx 不支持 socks scheme→报错）
_HX = dict(trust_env=False)


def rag_answer(scenic: str, question: str) -> str:
    """从 RAG 取一版答案（--regen-answer 时用）。"""
    r = httpx.post(f"http://localhost:8000/chat",
                   json={"session_id": "prerender", "message": question, "scenic_id": scenic},
                   timeout=60, **_HX)
    return r.json().get("reply", "")


def _say(text: str, emotion: str, scenic: str) -> bool:
    try:
        httpx.post(f"{BRIDGE}/live/say",
                   json={"sessionid": "0", "text": text, "scenic_id": scenic,
                         "emotion": emotion, "interrupt": True}, timeout=15, **_HX)
        return True
    except Exception as e:
        print(f"    ✗ 驱动失败: {e}"); return False


def render_clip(text: str, emotion: str, scenic: str, out_mp4: Path) -> bool:
    """录一段数字人说 text 的成品片。capture-first：先起 ffmpeg 抓流（垫 LEAD 秒让它连上
    SRS 并留入场静默），再驱动说话 → 避免"先驱动后抓"漏掉开头（TTS 重连/首音延迟时尤甚）。"""
    dur = estimate_window(text)
    tmp = out_mp4.with_suffix(".rec.ts")
    # 1) ffmpeg 先抓 FLV，录满整窗
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", SRS_FLV, "-t", f"{dur:.1f}",
         "-c", "copy", str(tmp)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # 2) 等 ffmpeg 连上 SRS（LEAD 秒），再驱动开口
    time.sleep(LEAD)
    if not _say(text, emotion, scenic):
        ff.terminate(); return False
    # 3) 等捕获完
    try:
        ff.wait(timeout=dur + 15)
    except subprocess.TimeoutExpired:
        ff.terminate()
    if not tmp.exists() or tmp.stat().st_size < 10_000:
        print("    ✗ 录制为空（数字人未在推流？）"); tmp.unlink(missing_ok=True); return False
    # 4) 转 mp4（faststart，移动端秒开）
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp),
                    "-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart", str(out_mp4)],
                   check=True)
    tmp.unlink(missing_ok=True)
    # 5) 校验有声（mean_volume，-80dB 以下判无声让用户知道）
    vol = subprocess.run(["ffmpeg", "-i", str(out_mp4), "-af", "volumedetect", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    silent = "mean_volume: -9" in vol or "mean_volume: -8" in vol
    print(f"    {'⚠️无声' if silent else '✓'} {out_mp4.name}  ({dur:.1f}s, {out_mp4.stat().st_size//1024}KB)")
    return not silent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenic", default="lingshan")
    ap.add_argument("--only", default=None, help="只渲染该 id")
    ap.add_argument("--regen-answer", action="store_true")
    args = ap.parse_args()

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items = data.get("scenics", {}).get(args.scenic, [])
    if not items:
        print(f"清单中无景区 {args.scenic}"); sys.exit(1)

    # 预热：先驱动一句（触发死连接重连/换景区音色），使后续定时渲染无重连延迟、时序稳定
    print("预热连接…")
    _say("您好，导览准备就绪。", "happy", args.scenic)
    time.sleep(4)

    done = 0
    for it in items:
        if args.only and it["id"] != args.only:
            continue
        print(f"[{args.scenic}/{it['id']}] {it['answer'][:24]}…")
        answer = rag_answer(args.scenic, it["match"][0]) if args.regen_answer else it["answer"]
        if args.regen_answer and answer:
            it["answer"] = answer
        out = FAQ_DIR / f"{args.scenic}_{it['id']}.mp4"
        # 重试至多 3 次：首条常因流水线未 settle 录到空，重录必成
        ok = False
        for attempt in range(3):
            if attempt:
                print(f"    ↻ 重试 {attempt}（上次录到空）")
                time.sleep(3)
            if render_clip(answer, it.get("emotion", "happy"), args.scenic, out):
                ok = True; break
        if ok:
            it["clip"] = f"/faq/{out.name}"
            done += 1
        time.sleep(1)

    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完成 {done} 条 → 已回写 manifest。重建 webapp 或拷 public/faq 到 dist 后，调用：")
    print("  curl -X POST http://localhost:9000/live/faq/reload")
    try:
        r = httpx.post(f"{BRIDGE}/live/faq/reload", timeout=5, **_HX)
        print("  已热重载:", r.json())
    except Exception:
        pass


if __name__ == "__main__":
    main()
