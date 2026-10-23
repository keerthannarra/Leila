@echo off
echo Starting Leila IT Help Desk...
echo.

REM Check for .env file
if not exist backend\.env (
    echo [SETUP] Creating backend\.env from example...
    copy backend\.env.example backend\.env
    echo [WARN]  Add your ANTHROPIC_API_KEY to backend\.env before using the AI features.
    echo.
)

REM Start backend in new terminal
echo [1/2] Starting FastAPI backend on http://localhost:8000
start "Leila Backend" cmd /k "cd /d %~dp0backend && pip install -r requirements.txt -q && uvicorn main:app --reload --port 8000"

REM Wait briefly then start frontend
timeout /t 3 /nobreak >nul

echo [2/2] Starting React frontend on http://localhost:5173
start "Leila Frontend" cmd /k "cd /d %~dp0frontend && npm install --silent && npm run dev"

echo.
echo Both services starting. Open http://localhost:5173 in your browser.
echo API docs: http://localhost:8000/docs
echo.
pause
