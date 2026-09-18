#!/usr/bin/env bash
cd "$(dirname "$0")"
(cd backend && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
BACK=$!
sleep 3
(cd frontend && npm run dev) &
FRONT=$!
trap "kill $BACK $FRONT 2>/dev/null" EXIT
echo "MarketMitra AI: backend http://127.0.0.1:8000, UI http://localhost:5173"
wait
