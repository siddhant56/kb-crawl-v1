# Usage: .\scripts\start.ps1 [dev|staging|prod]
# Requires: PowerShell 5.1+ (built-in on Win10/11) or PowerShell 7+
param(
    [ValidateSet("dev", "staging", "prod")]
    [string]$Env = "dev"
)

$ErrorActionPreference = "Stop"
$RootDir  = Split-Path -Parent $PSScriptRoot
$PidFile  = Join-Path $RootDir ".pids"

function Log     { param($m) Write-Host "[$(Get-Date -f HH:mm:ss)] $m"      -ForegroundColor Cyan   }
function Success { param($m) Write-Host "[$(Get-Date -f HH:mm:ss)] OK $m"   -ForegroundColor Green  }
function Warn    { param($m) Write-Host "[$(Get-Date -f HH:mm:ss)] ! $m"    -ForegroundColor Yellow }
function Err     { param($m) Write-Host "[$(Get-Date -f HH:mm:ss)] ERR $m"  -ForegroundColor Red; exit 1 }

# ── Guard: already running? ───────────────────────────────────────
if (Test-Path $PidFile) {
    Warn "Found existing .pids -- services may already be running."
    Read-Host "Run stop.ps1 first, or press Enter to continue anyway" | Out-Null
}

Write-Host ""
Log "============================================================"
Log " Radixweb RAG  |  env: $Env"
Log "============================================================"
Write-Host ""

# ── Python env detection ──────────────────────────────────────────
$uvicorn = $null

if (Test-Path "$RootDir\.venv\Scripts\uvicorn.exe") {
    $uvicorn = "$RootDir\.venv\Scripts\uvicorn.exe"
    Log "Python env: .venv"
} elseif (Get-Command conda -ErrorAction SilentlyContinue) {
    $condaList = conda env list 2>$null | Out-String
    if ($condaList -match '(?m)^llms\s') {
        conda activate llms 2>$null
        $uvicorn = (Get-Command uvicorn -ErrorAction SilentlyContinue)?.Source
        Log "Python env: conda (llms)"
    }
}

if (-not $uvicorn) {
    $uvicorn = (Get-Command uvicorn -ErrorAction SilentlyContinue)?.Source
    if (-not $uvicorn) { Err "uvicorn not found. Activate a venv or conda env first." }
    Log "Python env: system"
}

# ── Cleanup helper ────────────────────────────────────────────────
function Stop-Services {
    Log "Shutting down..."
    if (Test-Path $PidFile) {
        Get-Content $PidFile | Where-Object { $_ -match '^\d+$' } | ForEach-Object {
            try { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue; Log "Stopped PID $_" }
            catch {}
        }
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    }
    Success "All services stopped."
}

# Clear PID file
Set-Content $PidFile ""

# ── Backend ───────────────────────────────────────────────────────
Set-Location $RootDir

$backendArgs = switch ($Env) {
    "dev"     { @("api:app", "--host", "0.0.0.0", "--port", "8000", "--reload") }
    "staging" { @("api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2") }
    "prod"    { @("api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4") }
}

Log "Starting backend ($Env)..."
$backend = Start-Process -FilePath $uvicorn -ArgumentList $backendArgs -PassThru -NoNewWindow
Add-Content $PidFile $backend.Id
Success "Backend PID $($backend.Id)  ->  http://localhost:8000"
Success "API docs                     ->  http://localhost:8000/docs"

# ── Frontend ──────────────────────────────────────────────────────
Set-Location "$RootDir\frontend"

if (-not (Test-Path "node_modules")) {
    Log "Installing frontend dependencies..."
    npm install
}

if ($Env -eq "dev") {
    Log "Starting frontend (next dev)..."
    $frontend = Start-Process "cmd.exe" -ArgumentList "/c npm run dev" -PassThru -NoNewWindow
} else {
    Log "Building frontend (next build)..."
    & npm run build
    Log "Starting frontend (next start)..."
    $frontend = Start-Process "cmd.exe" -ArgumentList "/c npm run start" -PassThru -NoNewWindow
}

Add-Content $PidFile $frontend.Id
Success "Frontend PID $($frontend.Id)  ->  http://localhost:3000"

Write-Host ""
Success "All services running in $Env mode. Press Ctrl+C to stop."
Write-Host ""

# ── Wait and handle Ctrl+C ────────────────────────────────────────
try {
    while (-not $backend.HasExited -and -not $frontend.HasExited) {
        Start-Sleep -Seconds 1
    }
    # One of the processes crashed
    if ($backend.HasExited)  { Warn "Backend exited unexpectedly (code $($backend.ExitCode))" }
    if ($frontend.HasExited) { Warn "Frontend exited unexpectedly (code $($frontend.ExitCode))" }
} finally {
    Stop-Services
}
