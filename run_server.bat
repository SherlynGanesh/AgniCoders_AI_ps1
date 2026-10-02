@echo off
echo ==================================================
echo Starting DUKAANMITRA Backend Server...
echo Tagline: "Aap Bolo, DukaanMitra Sambhale."
echo ==================================================
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
pause
