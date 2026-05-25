#!/usr/bin/env pwsh
# ─────────────────────────────────────────────────────────────────
# KnowledgeOS — Start Script
# Launches backend (FastAPI) and frontend (Vite) in separate windows
# NOTE: Requires Python 3.12 venv (Python 3.14 is NOT supported by
#       chromadb/pydantic-core Rust extensions yet)
# ─────────────────────────────────────────────────────────────────


param(
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$Root = $PSScriptRoot
$Backend = Join-Path $Root "apps\backend"
$Frontend = Join-Path $Root "apps\frontend"

function Check-EnvFile {
    $envFile = Join-Path $Backend ".env"
    if (!(Test-Path $envFile)) {
        Write-Warning ".env not found. Copying from .env.example..."
        Copy-Item (Join-Path $Backend ".env.example") $envFile
    }
    $content = Get-Content $envFile -Raw
    if ($content -match "GEMINI_API_KEY=your_gemini_api_key_here") {
        Write-Error "⚠  Please set your GEMINI_API_KEY in apps\backend\.env before starting!"
        exit 1
    }
}

Check-EnvFile

if (!$FrontendOnly) {
    Write-Host "🚀 Starting backend on http://localhost:8000 ..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$Backend'; .\\venv\\Scripts\\Activate.ps1; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    ) -WindowStyle Normal
    Start-Sleep -Seconds 3
}

if (!$BackendOnly) {
    Write-Host "🎨 Starting frontend on http://localhost:5173 ..." -ForegroundColor Magenta
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "cd '$Frontend'; npm run dev"
    ) -WindowStyle Normal
}

Write-Host ""
Write-Host "✅ KnowledgeOS is starting up!" -ForegroundColor Green
Write-Host "   Backend API:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "   Frontend App: http://localhost:5173" -ForegroundColor White
Write-Host ""
