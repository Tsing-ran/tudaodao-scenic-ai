#!/bin/bash
# One-time setup — only touches /root/digital-human, nothing else
set -e

APP_DIR="/root/digital-human"
VENV="$APP_DIR/venv"

if [ ! -d "$APP_DIR" ]; then
  echo "ERROR: $APP_DIR not found. Upload the zip first."
  exit 1
fi

echo "Creating isolated venv at $VENV ..."
python3 -m venv "$VENV"

echo "Installing dependencies (isolated, won't affect other processes)..."
"$VENV/bin/pip" install -r "$APP_DIR/backend/requirements.txt" \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    --quiet

echo ""
echo "Done. Run:  bash $APP_DIR/deploy/start.sh"
