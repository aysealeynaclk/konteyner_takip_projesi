@echo off
setlocal

set "ROOT=%~dp0"
set "RUN_DIR=%ROOT%.run"
set "BACKEND_PID_FILE=%RUN_DIR%\backend.pid"
set "FRONTEND_PID_FILE=%RUN_DIR%\frontend.pid"

if exist "%BACKEND_PID_FILE%" (
    for /f "usebackq delims=" %%P in ("%BACKEND_PID_FILE%") do taskkill /PID %%P /T /F >nul 2>nul
)

if exist "%FRONTEND_PID_FILE%" (
    for /f "usebackq delims=" %%P in ("%FRONTEND_PID_FILE%") do taskkill /PID %%P /T /F >nul 2>nul
)

if exist "%BACKEND_PID_FILE%" del /f /q "%BACKEND_PID_FILE%" >nul 2>nul
if exist "%FRONTEND_PID_FILE%" del /f /q "%FRONTEND_PID_FILE%" >nul 2>nul

echo Backend ve frontend durduruldu.
endlocal
