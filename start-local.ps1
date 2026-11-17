param()

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend\ragezine-portal"
$venv = Join-Path $backend ".venv"
$python = Join-Path $venv "Scripts\python.exe"
$requirements = Join-Path $backend "requirements.txt"
$requirementsStamp = Join-Path $venv ".requirements.sha256"
$lockFile = Join-Path $frontend "package-lock.json"
$modules = Join-Path $frontend "node_modules"
$lockStamp = Join-Path $modules ".local-lock-sha256"
$backendProcess = $null

foreach ($port in @(8000, 5173)) {
    if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) {
        throw "Port $port is already in use. Stop the other local server, then run this script again."
    }
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python 3.12 is required. Install it, then run this script again."
}
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "Node.js and npm are required. Install them, then run this script again."
}

if (-not (Test-Path $python)) {
    & py -3.12 -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "Could not create the Python environment." }
}
$requirementsHash = (Get-FileHash $requirements -Algorithm SHA256).Hash
if (-not (Test-Path $requirementsStamp) -or (Get-Content $requirementsStamp -Raw).Trim() -ne $requirementsHash) {
    & $python -m pip install -r $requirements
    if ($LASTEXITCODE -ne 0) { throw "Could not install Python packages." }
    Set-Content -Path $requirementsStamp -Value $requirementsHash
}

$lockHash = (Get-FileHash $lockFile -Algorithm SHA256).Hash
if (-not (Test-Path $lockStamp) -or (Get-Content $lockStamp -Raw).Trim() -ne $lockHash) {
    Push-Location $frontend
    try {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw "Could not install frontend packages." }
    } finally {
        Pop-Location
    }
    Set-Content -Path $lockStamp -Value $lockHash
}

# These values override any production settings in local .env files.
$env:DJANGO_DB_ENGINE = "sqlite"
$env:DJANGO_DEBUG = "1"
$env:DJANGO_SECRET_KEY = "local-preview-only"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
$env:RAGEZINE_STORAGE_BACKEND = "local"
$env:RAGEZINE_REDIS_URL = ""
$env:DJANGO_EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
$env:VITE_API_URL = "/api/"
$env:VITE_PUBLIC_SITE_URL = "/"

Push-Location $backend
try {
    & $python manage.py migrate --noinput
    if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }
} finally {
    Pop-Location
}

try {
    $backendProcess = Start-Process -FilePath $python `
        -ArgumentList @("manage.py", "runserver", "127.0.0.1:8000", "--noreload") `
        -WorkingDirectory $backend -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $venv "server.out.log") `
        -RedirectStandardError (Join-Path $venv "server.err.log")

    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if ($backendProcess.HasExited) { break }
        try {
            Invoke-WebRequest "http://127.0.0.1:8000/api/auth/csrf/" -UseBasicParsing -TimeoutSec 1 | Out-Null
            $ready = $true
            break
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $ready) {
        Get-Content (Join-Path $venv "server.err.log") -ErrorAction SilentlyContinue
        throw "The Django server did not start."
    }

    Write-Host "Local site: http://127.0.0.1:5173/"
    Write-Host "Django API: http://127.0.0.1:8000/api/"
    Write-Host "Frontend edits appear at once. Restart this script after backend edits."
    Write-Host "Press Ctrl+C to stop."
    Push-Location $frontend
    try {
        & npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
    } finally {
        Pop-Location
    }
} finally {
    if ($backendProcess -and -not $backendProcess.HasExited) {
        Stop-Process -Id $backendProcess.Id
    }
}
