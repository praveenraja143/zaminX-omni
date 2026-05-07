@echo off
echo =======================================
echo     Starting Zamin X Platform...
echo =======================================

echo Starting Backend API Server (with auto-reload)...
start "Zamin X Backend" cmd /k "cd backend && python main.py server --reload"

echo Starting Frontend React App...
start "Zamin X Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Both servers are starting up!
echo The Frontend will be available at http://localhost:5173
echo The Backend API will be available at http://localhost:8000
echo.
