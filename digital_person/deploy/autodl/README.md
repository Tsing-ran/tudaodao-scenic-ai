# AutoDL 全栈进程守护与运维

用 supervisor 托管 AutoDL 上的六个常驻服务，进程死了自动重启；配一键启停与演示前体检。
背景与设计见 `docs/服务稳定性与运维设计.md`。

## 文件

| 文件 | 作用 |
|---|---|
| `supervisord.conf` | supervisor 配置，托管 SRS / RAG / LiveTalking×2 / 桥接 / 中继，`autorestart=true` |
| `dp_up.sh` | 启动 supervisor 并拉起全栈（开机后跑这一条，GPU 服务显式拉起，不抢训练 GPU） |
| `dp_down.sh` | 全停 + 释放 GPU（`supervisorctl shutdown`，让 GPU 给训练/ComfyUI） |
| `preflight.sh` | 演示前体检：进程/端口/健康/双流/GPU/公网，`--audio` 加测语音 dB |

部署位置：四个文件均放在 AutoDL 的 `/root/autodl-tmp/`。

## 常用命令（在 AutoDL 上）

```bash
# 开机后拉起全栈（约 90s 后两路数字人出流）
bash /root/autodl-tmp/dp_up.sh

# 演示前体检（关键项全绿才开录）
bash /root/autodl-tmp/preflight.sh           # 快检（~10s）
bash /root/autodl-tmp/preflight.sh --audio   # 加测数字人出声 dB（~15s，占 GPU）

# 看状态 / 看某服务日志 / 重启某服务
SUP="/root/miniconda3/bin/supervisorctl -c /root/autodl-tmp/supervisord.conf"
$SUP status
$SUP tail -f rag           # rag / bridge / srs / livetalking_main / livetalking_portrait / relay_hz
$SUP restart livetalking_main

# 全停，把 GPU 让给训练
bash /root/autodl-tmp/dp_down.sh
```

## 同步（本地改了脚本后推到 AutoDL）

```bash
scp deploy/autodl/*.conf deploy/autodl/*.sh autodl:/root/autodl-tmp/
# 改了 supervisord.conf 后让其生效：
ssh autodl '/root/miniconda3/bin/supervisorctl -c /root/autodl-tmp/supervisord.conf reread && \
            /root/miniconda3/bin/supervisorctl -c /root/autodl-tmp/supervisord.conf update'
```

## 注意

- 本机为容器、无 systemd，故用 supervisor；实例重启后需手动跑一次 `dp_up.sh`，之后由 supervisor 保活。
- GPU 与训练/ComfyUI 共用：本栈只在跑 `dp_up.sh` 时占 GPU，`dp_down.sh` 释放。
- 动 GPU 进程前务必先 `ps -o cmd= -p <PID>` 验明 cmdline，不要误杀训练进程。
