#!/usr/bin/env bash
set -euo pipefail

uvicorn horizonte.api.main:app --port 8000 --log-level warning &
APP_PID=$!
trap "kill $APP_PID" EXIT
sleep 2

python - <<'PY'
import json
import time
import urllib.request

base = "http://127.0.0.1:8000"

with urllib.request.urlopen(f"{base}/health") as resp:
    assert resp.status == 200

req = urllib.request.Request(
    f"{base}/inferencia",
    data=json.dumps({"query": "Prueba de humo"}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as resp:
    assert resp.status == 200
    data = json.loads(resp.read())
    assert "hash" in data

time.sleep(0.5)
with urllib.request.urlopen(f"{base}/auditoria") as resp:
    assert resp.status == 200
PY

echo "Smoke test completado."
