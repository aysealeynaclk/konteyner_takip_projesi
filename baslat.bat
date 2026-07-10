@echo off
echo Konteyner Takip Sistemi baslatiliyor...

start "Backend" cmd /k "cd backend && venv\Scripts\activate && uvicorn main:app --reload"

timeout /t 3 /nobreak > nul

start "Frontend" cmd /k "cd frontend && npm run dev"

echo Her iki sunucu da baslatildi.
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:5173

