#!/bin/bash
cd /root/digital-human/backend
exec /root/digital-human/venv/bin/uvicorn main:app --host 0.0.0.0 --port 6008 >> /root/digital-human/app.log 2>&1
