/**
 * 全局配置 —— 演示前只改这一处。
 *
 * LAN_HOST：跑后端/桥接/SRS 的那台 4080 机器的局域网 IP。
 *   - 本机 DevTools 模拟器调试：用 'localhost'
 *   - 手机真机（同一 WiFi）：用 `hostname -I` 查到的 IP，例如 '192.168.1.23'
 *
 * 端口与现有全栈一致（见 CLAUDE.md「本地全栈启动顺序」）：
 *   8000 = RAG 后端   9000 = 桥接层   8080 = SRS 的 HTTP-FLV/HLS
 */
const LAN_HOST = '192.168.43.152';  // 4080 电脑局域网 IP（真机预览用）；本机模拟器调试改回 'localhost'

module.exports = {
  LAN_HOST,
  BACKEND: `http://${LAN_HOST}:8000`,       // /trip/* /chat/image /digital-human/config
  BRIDGE: `http://${LAN_HOST}:9000`,        // /live/ask /live/say /live/health
  TTS_BACKEND: `http://${LAN_HOST}:8001`,   // 队友语音服务：/api/speech/asr（Paraformer）/api/speech/tts
  // SRS 的 HLS 直播地址（数字人连续画面）。
  // ⚠️ iOS ATS 禁止 AVPlayer 走 http 加载 HLS 媒体切片（微信 <video> 底层是 AVPlayer，
  //   且无法改微信 App 的 Info.plist）。故必须 https。用 cloudflared 快速隧道把本地
  //   SRS:8080 暴露成可信证书的 https 域名，满足 ATS。
  //   ⚠️ trycloudflare 域名每次重启隧道会变，重启后需同步更新这里。
  //   隧道启动：/tmp/cloudflared tunnel --url http://localhost:8080 --no-autoupdate
  // ⚠️ 用 livestream_ios（ffmpeg 中继把 16kHz 音频重采样到 48kHz，符合 Apple HLS 规范，
  //   否则 iOS AVPlayer 报 MEDIA_ERR_SRC_NOT_SUPPORTED）。中继命令见 CLAUDE.md。
  HLS: 'https://corporations-advisor-strap-activity.trycloudflare.com/live/livestream_ios.m3u8',
  // 本地 http 地址（仅本机模拟器可用，iOS 真机被 ATS 拦）：
  // HLS: `http://${LAN_HOST}:8080/live/livestream.m3u8`,
  // LiveTalking RTMP 单路固定会话 ID（与 app.html 一致）
  SESSION_ID: '0',
};
