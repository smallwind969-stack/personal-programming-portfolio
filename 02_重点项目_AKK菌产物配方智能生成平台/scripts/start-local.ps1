param(
  [switch]$SkipWebBuild
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$webDir = Join-Path $root "apps\web"
$apiDir = Join-Path $root "apps\api"
$logsDir = Join-Path $root "logs"
$runtimeDir = Join-Path $apiDir "data\runtime"
$experimentRuntimeDir = Join-Path $root "data\runtime"
New-Item -ItemType Directory -Force -Path $logsDir, $runtimeDir | Out-Null
$env:AGENT_COMMAND_QUEUE_PATH = if ($env:AGENT_COMMAND_QUEUE_PATH) { $env:AGENT_COMMAND_QUEUE_PATH } else { Join-Path $runtimeDir "agent-commands.db" }
$env:DOMAIN_RUN_STORE_PATH = if ($env:DOMAIN_RUN_STORE_PATH) { $env:DOMAIN_RUN_STORE_PATH } else { Join-Path $runtimeDir "domain-runs.db" }
$env:PRODUCT_INNOVATION_STORE_PATH = if ($env:PRODUCT_INNOVATION_STORE_PATH) { $env:PRODUCT_INNOVATION_STORE_PATH } else { Join-Path $runtimeDir "product-innovation.db" }
$env:RESEARCH_CAMPAIGN_STORE_PATH = if ($env:RESEARCH_CAMPAIGN_STORE_PATH) { $env:RESEARCH_CAMPAIGN_STORE_PATH } else { Join-Path $runtimeDir "research-campaigns.db" }
$env:MODEL_REGISTRY_PATH = if ($env:MODEL_REGISTRY_PATH) { $env:MODEL_REGISTRY_PATH } else { Join-Path $apiDir "data\runtime\promoted-models.db" }
$env:RESEARCH_ARTIFACT_PATH = if ($env:RESEARCH_ARTIFACT_PATH) { $env:RESEARCH_ARTIFACT_PATH } else { Join-Path $apiDir "data\runtime\model-artifacts" }
$env:RESEARCH_RUNNER = if ($env:RESEARCH_RUNNER) { $env:RESEARCH_RUNNER } else { "sklearn" }
$env:EXPERIMENT_DATA_STORE_PATH = if ($env:EXPERIMENT_DATA_STORE_PATH) { $env:EXPERIMENT_DATA_STORE_PATH } else { Join-Path $experimentRuntimeDir "experiment-data.db" }
$env:EXPERIMENT_OBJECT_STORE_PATH = if ($env:EXPERIMENT_OBJECT_STORE_PATH) { $env:EXPERIMENT_OBJECT_STORE_PATH } else { Join-Path $experimentRuntimeDir "experiment-objects" }
$env:CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
$env:CORS_ORIGIN_REGEX = "^http://(localhost|127\.0\.0\.1):3000$"

if (-not $SkipWebBuild) {
  Write-Host "Building web workspace..."
  Push-Location $webDir
  try {
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "Web build failed with exit code $LASTEXITCODE" }
  } finally {
    Pop-Location
  }
}

foreach ($port in 3000, 8000) {
  $ids = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($id in $ids) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
}
# Prevent stale workers with old environment paths from claiming new tasks.
Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match "-m\s+app\.worker" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
@("SERVER_API_BASE_URL=http://127.0.0.1:8000", "NEXT_PUBLIC_API_BASE_URL=/api", "NEXT_TELEMETRY_DISABLED=1") | Set-Content -Encoding UTF8 -Path (Join-Path $webDir ".env.local")
cmd /c start "AKK API" /min "$root\scripts\run-api.cmd"
$worker = Start-Process -FilePath "py.exe" -ArgumentList "-m", "app.worker", "--poll-seconds", "0.5" -WorkingDirectory $apiDir -WindowStyle Hidden -PassThru
$worker.Id | Set-Content -Encoding ASCII -Path (Join-Path $logsDir "agent-worker.pid")
cmd /c start "AKK Web" /min "$root\scripts\run-web.cmd"
Write-Host "Platform is starting."
if ($SkipWebBuild) { Write-Host "Web build was skipped by request." }
Write-Host "Open: http://127.0.0.1:3000/"
Write-Host "Health: http://127.0.0.1:8000/health"
Write-Host "Check: powershell -ExecutionPolicy Bypass -File .\scripts\check-local.ps1"
Write-Host "Stop: .\scripts\stop-local.ps1"
