$Root = $PSScriptRoot
$RunDir = Join-Path $Root '.run'
$PidFile = Join-Path $RunDir 'frontend.pid'
$FrontendDir = Join-Path $Root 'frontend'

if (-not (Test-Path $RunDir)) {
    New-Item -ItemType Directory -Path $RunDir | Out-Null
}

Set-Content -Path $PidFile -Value $PID
Set-Location $FrontendDir
npm.cmd run dev
