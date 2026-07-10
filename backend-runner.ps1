$Root = $PSScriptRoot
$RunDir = Join-Path $Root '.run'
$PidFile = Join-Path $RunDir 'backend.pid'
$BackendDir = Join-Path $Root 'backend'

if (-not (Test-Path $RunDir)) {
    New-Item -ItemType Directory -Path $RunDir | Out-Null
}

Set-Content -Path $PidFile -Value $PID
Set-Location $BackendDir
& "$BackendDir\venv\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8001
