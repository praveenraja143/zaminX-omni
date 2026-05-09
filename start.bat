@echo off
echo ===========================================
echo       Zamin X - Land Intelligence
echo ===========================================
echo.

echo [1/3] Installing dependencies...
cd backend
pip install -r requirements.txt --quiet 2>nul
cd ..

echo [2/3] Starting Backend API...
start "Zamin X Backend" cmd /k "cd /d %~dp0backend & python main.py server --reload"

echo [3/3] Starting Frontend...
start "Zamin X Frontend" cmd /k "cd /d %~dp0frontend & npm run dev"

echo.
echo ===========================================
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo ===========================================
pause
