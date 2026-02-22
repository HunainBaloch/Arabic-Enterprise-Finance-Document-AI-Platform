# start.ps1
# Run: powershell -ExecutionPolicy Bypass -File .\start.ps1
param()

$ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT

Write-Host "=== Arabic Enterprise Finance Document AI Platform ===" -ForegroundColor Magenta

# 1. Docker
Write-Host "`n>>> Checking Docker" -ForegroundColor Cyan
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[FAIL] Docker not installed" -ForegroundColor Red; exit 1
}
Write-Host "  OK Docker" -ForegroundColor Green
try { docker info *>$null } catch {
    Write-Host "[FAIL] Docker daemon not running. Start Docker Desktop." -ForegroundColor Red; exit 1
}
Write-Host "  OK Docker daemon running" -ForegroundColor Green

# 2. Env file
Write-Host "`n>>> Environment file" -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "  !! .env created from .env.example" -ForegroundColor Yellow
    } else {
        Write-Host "[FAIL] .env missing" -ForegroundColor Red; exit 1
    }
} else {
    Write-Host "  OK .env exists" -ForegroundColor Green
}

# 3. Model check
Write-Host "`n>>> AraBERT fine-tuned model" -ForegroundColor Cyan
$modelPath = "backend\training\models\arabert_ner_uae\model.safetensors"
if (Test-Path $modelPath) {
    Write-Host "  OK Fine-tuned model found" -ForegroundColor Green
} else {
    Write-Host "  !! Model not found - will use base AraBERT" -ForegroundColor Yellow
}

# 4. Pull images
Write-Host "`n>>> Pulling base images" -ForegroundColor Cyan
docker compose pull db redis prometheus grafana

# 5. Start infra
Write-Host "`n>>> Starting db + redis" -ForegroundColor Cyan
docker compose up -d db redis

# 6. Wait for DB health
Write-Host "`n>>> Waiting for PostgreSQL to be healthy (max 60s)" -ForegroundColor Cyan
$waited = 0
$dbReady = $false
while ($waited -lt 60) {
    Start-Sleep -Seconds 3
    $waited = $waited + 3
    $health = docker inspect --format="{{.State.Health.Status}}" idp_db 2>$null
    Write-Host "  [${waited}s] db: $health"
    if ($health -eq "healthy") {
        $dbReady = $true
        break
    }
}
if (-not $dbReady) {
    Write-Host "[FAIL] DB not healthy. Run: docker logs idp_db" -ForegroundColor Red; exit 1
}
Write-Host "  OK PostgreSQL healthy" -ForegroundColor Green

# 7. Alembic migrations
Write-Host "`n>>> Database migrations" -ForegroundColor Cyan
if (Test-Path "backend\alembic") {
    docker compose run --rm --no-deps backend alembic upgrade head
    Write-Host "  OK Migrations applied" -ForegroundColor Green
} else {
    Write-Host "  !! No alembic dir - skipping migrations" -ForegroundColor Yellow
}

# 8. Build + start all
Write-Host "`n>>> Building and starting all services (this may take several minutes on first run)" -ForegroundColor Cyan
docker compose up --build -d
Write-Host "  OK All containers launched" -ForegroundColor Green

# 9. Wait for backend
Write-Host "`n>>> Waiting for backend API (max 120s)" -ForegroundColor Cyan
$waited = 0
$apiReady = $false
while ($waited -lt 120) {
    Start-Sleep -Seconds 5
    $waited = $waited + 5
    try {
        $resp = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 3 -ErrorAction Stop
        if ($resp.StatusCode -eq 200) {
            $apiReady = $true
            break
        }
    } catch {
        # still starting
    }
    Write-Host "  [${waited}s] backend: $(if($apiReady){'UP'}else{'starting...'})"
}
if (-not $apiReady) {
    Write-Host "  !! Backend not responding yet. Check: docker logs idp_backend -f" -ForegroundColor Yellow
} else {
    Write-Host "  OK Backend API live" -ForegroundColor Green
}

# 10. Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host " Platform is Running" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host " API Docs    http://localhost:8000/api/v1/docs"
Write-Host " Health      http://localhost:8000/health"
Write-Host " Metrics     http://localhost:8000/metrics"
Write-Host " Frontend    http://localhost:3000"
Write-Host " Prometheus  http://localhost:9090"
Write-Host " Grafana     http://localhost:3001  (admin / Grafana_IDP_2026)"
Write-Host " PostgreSQL  localhost:5434"
Write-Host " Redis       localhost:6379"
Write-Host ""
Write-Host " To stop everything : docker compose down"
Write-Host " Backend logs       : docker logs idp_backend -f"
Write-Host " Worker logs        : docker logs idp_worker  -f"
Write-Host "==========================================" -ForegroundColor Green
