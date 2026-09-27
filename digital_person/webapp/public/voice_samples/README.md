# 音色试听样音（窗口① 异步交付）

AvatarSheet「形象工坊」的音色试听键，按 `manifest.json` 列出的 voice id 显示。

## 交付契约
1. 各音色预渲染一段 2–3s 短样音（一句导览口播即可），命名 `<voice_id>.mp3`，放本目录：
   - `voice_gentle_f.mp3` 知性温柔（默认）
   - `voice_lively_f.mp3` 活泼甜美
   - `voice_wu_f.mp3` 吴侬软语（江南）
   - `voice_calm_m.mp3` 沉稳大气
   - `voice_bright_m.mp3` 京腔青年
2. 把已就位的 id 填进 `manifest.json`（JSON 数组），例：
   `["voice_gentle_f","voice_lively_f","voice_wu_f","voice_calm_m","voice_bright_m"]`
3. 前端读 manifest 决定显隐播放键——未列出的不显示，零 404、无死按钮。

样音可用 CosyVoice（队友 :8001 各景区专属音色）或 Qwen-TTS 渲染。
