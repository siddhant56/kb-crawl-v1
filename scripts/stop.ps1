# Stop all services started by scripts/start.ps1
$RootDir = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path $RootDir ".pids"

if (-not (Test-Path $PidFile)) {
    Write-Host "No .pids file found -- nothing to stop." -ForegroundColor Yellow
    exit 0
}

Write-Host "Stopping services..."
Get-Content $PidFile | Where-Object { $_ -match '^\d+$' } | ForEach-Object {
    try {
        Stop-Process -Id $_ -Force -ErrorAction Stop
        Write-Host "OK Stopped PID $_" -ForegroundColor Green
    } catch {
        Write-Host "   PID $_ already stopped"
    }
}
Remove-Item $PidFile -Force
Write-Host "Done." -ForegroundColor Green
