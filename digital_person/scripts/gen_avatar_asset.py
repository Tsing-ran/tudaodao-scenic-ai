"""
数字人形象素材一键生成（通义万相 / DashScope）

用你已有的 DashScope key，文生图 → 图生视频，产出 MuseTalk 底座素材：
  1) 文生图 wanx2.1-t2i  : 写实古风导游竖版肖像（720x1280，适配手机 9:16）
  2) 图生视频 wanx2.1-i2v: 把肖像变成 5s 微动待机视频（眨眼/轻微头动，自然度远胜静态图）

为什么走这条链：MuseTalk「只重生成嘴部、贴回原帧」，自然度=底座自然度，
∴ 底座必须写实真人风格 + 有微动的视频。本脚本一次出一套，可换 prompt 批量出多套
（古风女/男/不同景区），正好演示赛题「数字人形象可配置」。

用法：
  .venv/bin/python scripts/gen_avatar_asset.py --avatar-id guofeng_female
  .venv/bin/python scripts/gen_avatar_asset.py --avatar-id guofeng_male \
      --prompt "一位儒雅的中国古风男性导游，宋代文士长衫..."
  # 只要肖像、不生成视频（更快，省额度）：
  .venv/bin/python scripts/gen_avatar_asset.py --avatar-id x --no-video

产物落在 assets/avatar_src/<avatar-id>/，并打印下一步「烘成 MuseTalk avatar」的命令。
"""
import argparse
import os
import sys
from pathlib import Path

import dashscope
import httpx
from dashscope import ImageSynthesis, VideoSynthesis
from dotenv import load_dotenv

# 默认：写实古风女导游（正脸、嘴部无遮挡、影棚柔光、纯背景 —— 都是 MuseTalk 的选材要求）
DEFAULT_T2I_PROMPT = (
    "一位温婉知性的中国古风女性导游，唐代襦裙，发髻簪花，面容清秀写实，"
    "正面半身肖像，直视镜头，自然微笑，嘴部清晰无遮挡，柔和影棚光，"
    "纯色浅灰背景，超写实人像摄影，电影质感，8k，竖版构图"
)
# 图生视频：只要「微动待机」，幅度要小，否则嘴部偏移 MuseTalk 贴不准
DEFAULT_I2V_PROMPT = (
    "人物自然地缓慢眨眼，头部极轻微晃动，保持微笑与正脸，"
    "镜头固定，背景静止，动作幅度小而自然"
)

T2I_MODEL = "wanx2.1-t2i-plus"      # plus 质量更好；要快可换 wanx2.1-t2i-turbo
I2V_MODEL = "wanx2.1-i2v-turbo"     # 图生视频


def _download(url: str, dst: Path):
    """下载 OSS 临时链接到本地。

    trust_env=False：绕开环境里的 socks 代理（httpx 不支持 socks scheme 会报错；
    且阿里云 OSS 是公网 CDN，国内直连可达，不需要代理）。
    """
    with httpx.Client(trust_env=False, timeout=120, follow_redirects=True) as client:
        with client.stream("GET", url) as r:
            r.raise_for_status()
            with open(dst, "wb") as f:
                for chunk in r.iter_bytes():
                    f.write(chunk)


def gen_image(prompt: str, out: Path) -> str:
    print(f"[1/2] 文生图 {T2I_MODEL} …（约 30-60s）")
    rsp = ImageSynthesis.call(model=T2I_MODEL, prompt=prompt, n=1, size="720*1280")
    if rsp.status_code != 200:
        sys.exit(f"❌ 文生图失败 code={rsp.code} msg={rsp.message}")
    url = rsp.output.results[0].url
    _download(url, out)
    print(f"    ✅ 肖像已存：{out}")
    return url  # 返回 OSS url，直接喂图生视频，省一次上传


def gen_video(img_url: str, prompt: str, out: Path):
    print(f"[2/2] 图生视频 {I2V_MODEL} …（约 3-5 分钟，请耐心等）")
    rsp = VideoSynthesis.call(model=I2V_MODEL, prompt=prompt, img_url=img_url)
    if rsp.status_code != 200:
        sys.exit(f"❌ 图生视频失败 code={rsp.code} msg={rsp.message}")
    url = rsp.output.video_url
    _download(url, out)
    print(f"    ✅ 微动视频已存：{out}")


def main():
    ap = argparse.ArgumentParser(description="通义万相生成数字人形象素材")
    ap.add_argument("--avatar-id", required=True, help="形象 ID，如 guofeng_female")
    ap.add_argument("--prompt", default=DEFAULT_T2I_PROMPT, help="文生图 prompt（人物外观）")
    ap.add_argument("--motion", default=DEFAULT_I2V_PROMPT, help="图生视频 prompt（微动描述）")
    ap.add_argument("--no-video", action="store_true", help="只出肖像，不生成视频")
    ap.add_argument("--out-dir", default="assets/avatar_src", help="输出根目录")
    args = ap.parse_args()

    load_dotenv()
    key = os.getenv("DASHSCOPE_API_KEY")
    if not key:
        sys.exit("❌ .env 里没有 DASHSCOPE_API_KEY")
    dashscope.api_key = key

    out_dir = Path(args.out_dir) / args.avatar_id
    out_dir.mkdir(parents=True, exist_ok=True)
    img_path = out_dir / "portrait.png"
    vid_path = out_dir / "idle.mp4"

    img_url = gen_image(args.prompt, img_path)
    base_file = img_path
    if not args.no_video:
        gen_video(img_url, args.motion, vid_path)
        base_file = vid_path

    # 打印下一步：把素材烘成 MuseTalk avatar
    lt = Path.home() / "Desktop/LiveTalking"
    print("\n" + "=" * 60)
    print("素材就绪。下一步把它烘成 MuseTalk avatar：\n")
    print(f"  cd {lt}")
    print("  unset ALL_PROXY all_proxy HTTP_PROXY http_proxy HTTPS_PROXY https_proxy")
    print(f"  ~/miniconda3/envs/livetalking/bin/python avatars/musetalk/genavatar.py \\")
    print(f"      --file {base_file.resolve()} --avatar_id {args.avatar_id} --version v15\n")
    print(f"烘完重启数字人时加 --avatar_id {args.avatar_id} 即可换上这张脸。")
    print("=" * 60)


if __name__ == "__main__":
    main()
