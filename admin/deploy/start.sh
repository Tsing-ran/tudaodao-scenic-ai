#!/bin/bash
# Start admin backend on port 6008 only — port 6006 (RAG) is not touched
APP_DIR="/root/digital-human"
VENV="$APP_DIR/venv"

if [ ! -f "$VENV/bin/uvicorn" ]; then
  echo "ERROR: venv not found. Run setup.sh first."
  exit 1
fi

# Safety check: refuse to start if 6008 is already occupied
if ss -tlnp 2>/dev/null | grep -q ':6008 '; then
  echo "ERROR: port 6008 is already in use. Kill that process first."
  exit 1
fi

echo "Starting on port 6008 (RAG on 6006 is untouched)..."
echo "Admin URL: https://uu891802-x4xd-7f8146e7.bjb2.seetacloud.com:8443/admin/"

cd "$APP_DIR/backend"
exec "$VENV/bin/uvicorn" main:app --host 0.0.0.0 --port 6008
