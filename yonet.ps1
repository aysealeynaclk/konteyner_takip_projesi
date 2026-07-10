param(
    [ValidateSet('start', 'stop', 'status')]
    [string]$Action = 'start'
)

$Root = $PSScriptRoot
$BackendDir = Join-Path $Root 'backend'
$FrontendDir = Join-Path $Root 'frontend'
$RunDir = Join-Path $Root '.run'
$BackendPidFile = Join-Path $RunDir 'backend.pid'
$FrontendPidFile = Join-Path $RunDir 'frontend.pid'

function Test-PidAlive {
    param([int]$ProcessId)
    try {
        Get-Process -Id $ProcessId -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

function Read-PidFile {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return $null
    }

    try {
        return [int](Get-Content $Path -Raw)
    } catch {
        return $null
    }
}

function Write-PidFile {
    param(
        [string]$Path,
        [int]$Pid
    )

    if (-not (Test-Path $RunDir)) {
        New-Item -ItemType Directory -Path $RunDir | Out-Null
    }

    Set-Content -Path $Path -Value $Pid
}

function Start-App {
    $backendPid = Read-PidFile $BackendPidFile
    $frontendPid = Read-PidFile $FrontendPidFile

    if ($backendPid -and $frontendPid -and (Test-PidAlive $backendPid) -and (Test-PidAlive $frontendPid)) {
        Write-Host "Backend ve frontend zaten calisiyor."
        Write-Host "Backend PID: $backendPid"
        Write-Host "Frontend PID: $frontendPid"
        return
    }

    $backendStarter = Join-Path $Root 'backend-runner.ps1'
    $frontendStarter = Join-Path $Root 'frontend-runner.ps1'

    cmd /c start "" /b powershell -NoProfile -ExecutionPolicy Bypass -File "$backendStarter"
    cmd /c start "" /b powershell -NoProfile -ExecutionPolicy Bypass -File "$frontendStarter"

    Write-Host "Backend ve frontend baslatma komutu verildi."
    Write-Host "Backend: http://127.0.0.1:8001"
    Write-Host "Frontend: http://localhost:5173"
}

function Show-Status {
    $backendPid = Read-PidFile $BackendPidFile
    $frontendPid = Read-PidFile $FrontendPidFile

    if (-not $backendPid -and -not $frontendPid) {
        Write-Host "Kayitli calisma bilgisi yok."
        return
    }

    $backendState = if ($backendPid -and (Test-PidAlive $backendPid)) { 'calisiyor' } else { 'kapali' }
    $frontendState = if ($frontendPid -and (Test-PidAlive $frontendPid)) { 'calisiyor' } else { 'kapali' }

    Write-Host "Backend: $backendState (PID $backendPid)"
    Write-Host "Frontend: $frontendState (PID $frontendPid)"
}

function Stop-App {
    $backendPid = Read-PidFile $BackendPidFile
    $frontendPid = Read-PidFile $FrontendPidFile

    if (-not $backendPid -and -not $frontendPid) {
        Write-Host "Calisan PID kaydi bulunamadi."
        return
    }

    foreach ($processId in @($backendPid, $frontendPid)) {
        if ($processId -and (Test-PidAlive $processId)) {
            taskkill /PID $processId /T /F | Out-Null
        }
    }

    Remove-Item $BackendPidFile -ErrorAction SilentlyContinue
    Remove-Item $FrontendPidFile -ErrorAction SilentlyContinue
    Write-Host "Backend ve frontend durduruldu."
}

switch ($Action) {
    'start' { Start-App }
    'stop' { Stop-App }
    'status' { Show-Status }
}