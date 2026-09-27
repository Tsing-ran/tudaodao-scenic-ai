#!/usr/bin/env bash

set -u

BASE="/root/autodl-tmp"
CONF="$BASE/supervisord.conf"
CTL="/root/miniconda3/bin/supervisorctl"
DAEMON="/root/miniconda3/bin/supervisord"

PIDFILE="$BASE/supervisord.pid"
SOCKET="$BASE/supervisor.sock"
LOGFILE="$BASE/boot_services.log"

exec >>"$LOGFILE" 2>&1

echo
echo "=================================================="
echo "[$(date '+%F %T')] project startup check"

# 项目 Supervisor 已正常运行
if "$CTL" -c "$CONF" pid >/dev/null 2>&1; then
    echo "Project supervisord is already running."
    "$CTL" -c "$CONF" status
    exit 0
fi

STAMP="$(date '+%Y%m%d_%H%M%S')"

# 处理失效的 PID 文件
if [ -f "$PIDFILE" ]; then
    OLD_PID="$(cat "$PIDFILE" 2>/dev/null || true)"

    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "PID $OLD_PID is still alive; startup cancelled."
        exit 1
    fi

    mv "$PIDFILE" "${PIDFILE}.stale_${STAMP}"
    echo "Moved stale PID file."
fi

# 处理无人占用的旧 Socket
if [ -S "$SOCKET" ]; then
    if command -v fuser >/dev/null 2>&1 &&
       fuser "$SOCKET" >/dev/null 2>&1; then
        echo "Supervisor socket is still in use; startup cancelled."
        exit 1
    fi

    mv "$SOCKET" "${SOCKET}.stale_${STAMP}"
    echo "Moved stale supervisor socket."
fi

echo "Starting project supervisord..."
"$DAEMON" -c "$CONF"

# 最长等待 30 秒
for i in $(seq 1 30); do
    sleep 1

    if "$CTL" -c "$CONF" pid >/dev/null 2>&1; then
        echo "Project supervisord started successfully."
        "$CTL" -c "$CONF" status

        echo "Local port checks:"
        for PORT in 6006 6008 8000; do
            CODE="$(curl -sS --max-time 5 \
                -o /dev/null \
                -w '%{http_code}' \
                "http://127.0.0.1:${PORT}/" 2>/dev/null || true)"

            if [ -z "$CODE" ] || [ "$CODE" = "000" ]; then
                echo "$PORT: unavailable"
            else
                echo "$PORT: HTTP $CODE"
            fi
        done

        exit 0
    fi
done

echo "Project supervisord failed to start."
exit 1
