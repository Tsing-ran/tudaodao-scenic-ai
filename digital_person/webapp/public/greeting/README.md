# 含手势欢迎片（连接时先播，再切实时问答）

实时数字人引擎 Ditto 驱动静态肖像、**出不了手**；手势只能走离线预渲染片。
连接成功后 `useGuide.greet()` 查本清单：命中 `scenic×group` → 舞台播该成片（自带语音+挥手），
`onEnded` 回归实时问答；未命中 → 回退实时数字人开口迎宾（无手势）。

## manifest.json 结构
```json
{
  "scenics": {
    "lingshan": {
      "adult":       { "clip": "/greeting/lingshan_adult.mp4",  "text": "迎宾词…", "emotion": "happy" },
      "family_kids": { "clip": "/greeting/lingshan_family.mp4", "text": "…" }
    }
  }
}
```
- `group` 缺省回落 `adult`。`text` 用于字幕/气泡展示（成片音频才是真声）。
- 成片渲染：EchoMimicV2（半身手势+音频驱动说话，AutoDL 24G）。源图=InstantID 半身露手 face16，
  取景贴近灵山实时胸像以减小 clip→live 跳切。音频=Qwen-TTS 迎宾词 wav。
- 大文件不进 git，随 dist 部署到 autodl/hz（仿 L1 FAQ 真片）。
