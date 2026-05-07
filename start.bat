@echo off
REM LMS Course Builder - Start Script (Windows)

echo ============================================
echo   LMS Course Builder v2.0.0
echo ============================================
echo.

cd /d "%~dp0backend"

echo Installing dependencies...
pip install -r requirements.txt -q

if not exist uploads mkdir uploads

if not exist .env (
    echo Creating .env from template...
    copy .env.example .env >nul 2>&1
)

echo.
echo Starting server on http://localhost:8000
echo Admin login: admin / LMSadmin2026!
echo API docs: http://localhost:8000/docs
echo Press Ctrl+C to stop
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
