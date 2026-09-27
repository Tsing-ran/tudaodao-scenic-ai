"""
按景区解析 LiveTalking 启动用的 avatar_id（含场景背景变体）。

背景烘进 Ditto 源肖像 → 切背景 = 换 avatar 变体（进程级，下次启动生效）。
本脚本查后端配置并做变体存在性检查，供启动命令内联：

  ~/miniconda3/envs/livetalking/bin/python app.py --transport rtmp --model ditto \
      --avatar_id $(.venv/bin/python scripts/resolve_avatar.py --scenic lingshan) ...

stdout 只输出最终 avatar_id 一行；诊断信息走 stderr，不污染 $(...) 捕获。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# 复用桥接的映射与变体解析，避免双维护（导入只构建 app 对象，不启动服务）
from bridge.server import AVATAR_MAP, DEFAULT_AVATAR, _resolve_avatar_variant  # noqa: E402


def resolve(scenic_id: str, rag_base: str) -> str:
    import httpx
    try:
        with httpx.Client(trust_env=False, timeout=5) as client:
            cfg = client.get(f"{rag_base}/digital-human/config",
                             params={"scenic_id": scenic_id}).json()
    except Exception as e:
        print(f"⚠️ 取配置失败({type(e).__name__})，用默认 avatar", file=sys.stderr)
        cfg = {}
    base = AVATAR_MAP.get(cfg.get("avatar_id"), DEFAULT_AVATAR)
    avatar = _resolve_avatar_variant(base, cfg.get("background_id") or "")
    if avatar != base:
        print(f"✓ 景区 {scenic_id} 背景变体：{avatar}", file=sys.stderr)
    elif cfg.get("background_id"):
        print(f"⚠️ 背景 {cfg['background_id']} 的变体未烘出，回落 {base}"
              f"（先跑 scripts/gen_avatar_background.py compose）", file=sys.stderr)
    return avatar


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenic", default="lingshan")
    ap.add_argument("--rag", default="http://localhost:8000")
    args = ap.parse_args()
    print(resolve(args.scenic, args.rag.rstrip("/")))
