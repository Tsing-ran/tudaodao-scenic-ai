# LiveTalking 引擎自研改造归档

> 备份目的：我们对 LiveTalking 的 Ditto 实时数字人改造**只存在于本机/AutoDL 工作区，从未提交到任何 git**（上游是 lipku 的仓库，无法 push）。此目录把改动归档进本仓库，作为唯一的版本化备份。

## 上游
- 仓库：`https://github.com/lipku/LiveTalking.git`
- 基线 commit：`bf54b577a4ff4fc151ef07dbe325929673bbf09e`

## 本目录内容
按原相对路径存放的改造文件（覆盖式还原）：

| 文件 | 性质 | 说明 |
|---|---|---|
| `avatars/ditto_avatar.py` | **新增·核心** | 自研 Ditto avatar：`set_source()` 形象热切、`set_emotion()` 情绪热切、feeder/emitter 帧音配对推 RTMP、静音自驱动待机 |
| `streamout/rtmp.py` | 改 | 推流看门狗（SRS publish.active 轮询→自动重建 Streamer，不碰 TRT） |
| `tts/qwentts.py` | 改 | Qwen-TTS 接入 + 韵律随情绪 + 死连接重连（治静音/超时坑） |
| `server/routes.py` | 改 | `/set_avatar`、`/human` 的 emotion→set_emotion 分发 |
| `server/rtc_manager.py` | 改 | — |
| `avatars/musetalk_avatar.py` | 改 | MuseTalk 多情绪底座热切（旧引擎，保留） |
| `app.py` | 改 | `--model ditto` 注册等 |
| `dl_models.py` | 新增 | 模型下载辅助 |
| `livetalking_ditto.patch` | — | 6 个 tracked 文件的 `git diff`，可 `git apply` 到基线 |

## 还原方法
```bash
git clone https://github.com/lipku/LiveTalking.git
cd LiveTalking && git checkout bf54b577
# 方式A：直接覆盖文件
cp -r <此目录>/{app.py,avatars,server,streamout,tts,dl_models.py} .
# 方式B：对 tracked 改动打 patch（新增文件仍需手动拷 ditto_avatar.py / dl_models.py）
git apply <此目录>/livetalking_ditto.patch
```
启动命令与踩坑见根 `CLAUDE.md`「本地全栈启动顺序」+ 记忆 [[ditto-engine]]。
