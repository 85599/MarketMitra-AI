@echo off
cd /d "%~dp0"
start "MarketMitra-backend" cmd /k "cd backend && .venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
timeout /t 3 /nobreak > nul
start "MarketMitra-frontend" cmd /k "cd frontend && npm run dev"
echo MarketMitra AI starting: backend http://127.0.0.1:8000, UI http://localhost:5173
