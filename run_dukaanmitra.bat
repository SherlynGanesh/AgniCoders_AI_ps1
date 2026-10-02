@echo off
title DukaanMitra Launcher
echo ======================================================================
echo          DUKAANMITRA - "Aap Bolo, DukaanMitra Sambhale."
echo ======================================================================
echo [1/3] Starting FastAPI Backend on http://localhost:8000 ...
start "DukaanMitra Backend (FastAPI)" cmd /k "python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/3] Starting React Vite Frontend on http://localhost:5173 ...
start "DukaanMitra Frontend (Vite UI)" cmd /k "npm.cmd run dev -- --host 0.0.0.0 --port 5173"

echo [3/3] Opening DukaanMitra in your default browser...
timeout /t 3 >nul
start http://localhost:5173

echo ======================================================================
echo Both Backend (Port 8000) and Frontend (Port 5173) are running!
echo Web Application:   http://localhost:5173
echo Swagger API Docs:  http://localhost:8000/docs
echo Database Health:   http://localhost:8000/health
echo ======================================================================
echo Keep this window and the terminal windows open while using the app.
pause
