# 灵境·导览 — 游客端微信小程序

个人号原生小程序（无第三方框架、**零构建**），数字人画面走 HLS `<video>`，问答/语音/拍照接现有后端+桥接。

## 一、准备工具（Linux 跑微信开发者工具）

本机用社区移植版（官方只出 Win/Mac）：
- 仓库：`github.com/msojocs/wechat-web-devtools-linux`，按其 README 安装（依赖 libssh2 等）。
- 启动后用微信扫码登录。

## 二、导入项目

1. 微信开发者工具 → 导入项目 → 目录选 **本 `miniprogram/` 文件夹**。
2. **AppID**：填你的**个人号小程序 AppID**（`mp.weixin.qq.com` 注册的个人小程序）。
   - ⚠️ `project.config.json` 里现在是占位 `touristappid`，**真机预览 + 录音必须换成你自己的 AppID**。
3. 不需要「构建 npm」（本项目没用 npm 依赖）。

## 三、改这一处配置

`config.js` 里 `LAN_HOST`：
- **DevTools 模拟器调试**：`'localhost'`
- **手机真机（同一 WiFi）**：4080 机器的局域网 IP（终端 `hostname -I` 查，如 `192.168.1.23`）

## 四、关掉域名校验（开发版必做）

DevTools 右上角 **详情 → 本地设置** → 勾：
- ☑ 不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书

（个人号没有「业务域名」配置，靠这个开关让开发版直连 `http://<LAN>:端口`。）

## 五、起后端全栈（在 4080 机器）

按 `CLAUDE.md`「本地全栈启动顺序」，但 **SRS 要用带 HLS 的新配置**：

```bash
# ① SRS（带 HLS，一次性重建容器）
docker rm -f srs
docker run -d --name srs -p 1935:1935 -p 1985:1985 -p 8080:8080 \
  -v /home/jiale/Desktop/Digital_Person/deploy/srs.conf:/usr/local/srs/conf/docker.conf \
  registry.cn-hangzhou.aliyuncs.com/ossrs/srs:5 ./objs/srs -c conf/docker.conf

# ② LiveTalking（RTMP 推流，主形象 sweet_bob + Qwen-TTS Serena，batch4 防 OOM）
# ③ RAG 后端（DEPLOY_MODE=cloud，0 显存）
# ④ 桥接层 :9000
# 三条命令见 CLAUDE.md
```

验证：
```bash
curl localhost:1985/api/v1/streams/         # 看 active:true（LiveTalking 已推流）
curl -I localhost:8080/live/livestream.m3u8 # 200 = HLS 切片就绪
curl localhost:9000/live/health             # rag/livetalking 双 true
```

## 六、跑起来

- **模拟器**：`LAN_HOST='localhost'`，点「开始游览」→ 看数字人画面 → 迎宾开口 → 打字提问。
  （模拟器对 HLS 支持有限，画面可能不动，但问答/字幕/接口逻辑可验证；画面以真机为准。）
- **真机**：DevTools「预览」生成二维码 → 手机扫码（开发版）→ 体验：
  开始游览 → 数字人 HLS 画面 → 迎宾 → **打字 / 按住麦克风说话 / 拍照定位** 三种提问 → 数字人开口 + 字幕。

## 功能清单（对标赛题游客端）

| 功能 | 实现 |
|---|---|
| 智能问答（语音/文字） | 文字 `/live/ask`；按住说话 `wx.getRecorderManager`→`/asr`→`/live/ask` |
| 数字人 语音/表情/口型同步 | HLS `<video>` + 桥接逐句驱动 + `[情绪]` 切表情底座 |
| 个性化路线推荐 | 同行人 `group_type` 选择器 + recommend 意图 |
| 多模态（拍照定位指路） | `wx.chooseMedia`→`/chat/image`→`/live/say` |
| 主动迎宾 | 连接后 `/trip/greeting`→`/live/say` |
| 多景区切换 | 顶部景区选择器（5 景区） |
| 电子游记 | 行程游记弹层 `/trip/summary` |

## 设计说明（答辩可用）

- **自研精致 UI**，严格遵循微信官方《小程序设计指南》：统一设计 token（`app.wxss`）、自定义沉浸式导航栏、
  骨架屏 + 三态降级、触感反馈、安全区适配、统一过渡动效、字幕打字机。线性 SVG 图标（非 emoji）。
- **个人号约束下的工程取舍**：web-view/live-player 个人号禁用 → 数字人画面选 HLS `<video>`（唯一可用直播路径），
  复用现有 LiveTalking→SRS 链路，后端仅加一段 HLS 输出。
