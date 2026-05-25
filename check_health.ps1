#!/usr/bin/env pwsh
# Quick backend health check after startup
param([int]$Port = 8000, [int]$TimeoutSeconds = 30)

Write-Host "Waiting for backend on :$Port..." -ForegroundColor Cyan
$start = Get-Date
$up = $false

while ((Get-Date) - $start -lt [TimeSpan]::FromSeconds($TimeoutSeconds)) {
    try {
        $resp = Invoke-RestMethod "http://localhost:$Port/api/health" -TimeoutSec 2
        Write-Host "✅ Backend is UP!" -ForegroundColor Green
        Write-Host "   Graph nodes:  $($resp.graph.total_nodes)" -ForegroundColor White
        Write-Host "   Graph edges:  $($resp.graph.total_edges)" -ForegroundColor White
        Write-Host "   Documents:    $($resp.graph.document_count)" -ForegroundColor White
        $up = $true
        break
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $up) {
    Write-Error "Backend did not start within $TimeoutSeconds seconds"
    exit 1
}
