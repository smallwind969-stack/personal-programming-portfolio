$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$webDir = Join-Path $root "apps\web"
$apiDir = Join-Path $root "apps\api"
$runtimeDir = Join-Path $apiDir "data\runtime"
$experimentRuntimeDir = Join-Path $root "data\runtime"
$logsDir = Join-Path $root "logs"
New-Item -ItemType Directory -Force -Path $logsDir, $runtimeDir, $experimentRuntimeDir | Out-Null

$ip = Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object {
    $_.IPAddress -notlike "169.254*" -and
    $_.IPAddress -ne "127.0.0.1" -and
    $_.InterfaceAlias -notmatch "wintun|loopback|docker|vEthernet"
  } |
  Sort-Object InterfaceAlias |
  Select-Object -First 1 -ExpandProperty IPAddress

if (-not $ip) {
  throw "No LAN IPv4 address found. Connect to Wi-Fi or Ethernet first."
}

$envFile = Join-Path $webDir ".env.local"
@"
SERVER_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_API_BASE_URL=http://${ip}:8000
NEXT_TELEMETRY_DISABLED=1
"@ | Set-Content -Encoding UTF8 -Path $envFile

foreach ($port in 3000, 8000) {
  $listeners = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" } |
    Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($processId in $listeners) {
    Stop-Process -Id $processId -Force
  }
}

$env:CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000,http://${ip}:3000"
$env:CORS_ORIGIN_REGEX = "^http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+):3000$"
$env:AGENT_COMMAND_QUEUE_PATH = if ($env:AGENT_COMMAND_QUEUE_PATH) { $env:AGENT_COMMAND_QUEUE_PATH } else { Join-Path $runtimeDir "agent-commands.db" }
$env:DOMAIN_RUN_STORE_PATH = if ($env:DOMAIN_RUN_STORE_PATH) { $env:DOMAIN_RUN_STORE_PATH } else { Join-Path $runtimeDir "domain-runs.db" }
$env:PRODUCT_INNOVATION_STORE_PATH = if ($env:PRODUCT_INNOVATION_STORE_PATH) { $env:PRODUCT_INNOVATION_STORE_PATH } else { Join-Path $runtimeDir "product-innovation.db" }
$env:RESEARCH_CAMPAIGN_STORE_PATH = if ($env:RESEARCH_CAMPAIGN_STORE_PATH) { $env:RESEARCH_CAMPAIGN_STORE_PATH } else { Join-Path $runtimeDir "research-campaigns.db" }
$env:MODEL_REGISTRY_PATH = if ($env:MODEL_REGISTRY_PATH) { $env:MODEL_REGISTRY_PATH } else { Join-Path $runtimeDir "promoted-models.db" }
$env:RESEARCH_ARTIFACT_PATH = if ($env:RESEARCH_ARTIFACT_PATH) { $env:RESEARCH_ARTIFACT_PATH } else { Join-Path $runtimeDir "model-artifacts" }
$env:RESEARCH_RUNNER = if ($env:RESEARCH_RUNNER) { $env:RESEARCH_RUNNER } else { "sklearn" }
$env:EXPERIMENT_DATA_STORE_PATH = if ($env:EXPERIMENT_DATA_STORE_PATH) { $env:EXPERIMENT_DATA_STORE_PATH } else { Join-Path $experimentRuntimeDir "experiment-data.db" }
$env:EXPERIMENT_OBJECT_STORE_PATH = if ($env:EXPERIMENT_OBJECT_STORE_PATH) { $env:EXPERIMENT_OBJECT_STORE_PATH } else { Join-Path $experimentRuntimeDir "experiment-objects" }

Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
  Where-Object { $_.CommandLine -match "-m\s+app\.worker" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Start-Process -FilePath "py" `
  -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000" `
  -WorkingDirectory $apiDir `
  -RedirectStandardOutput (Join-Path $logsDir "api.out.log") `
  -RedirectStandardError (Join-Path $logsDir "api.err.log") `
  -WindowStyle Hidden

$worker = Start-Process -FilePath "py" `
  -ArgumentList "-m","app.worker","--poll-seconds","0.5" `
  -WorkingDirectory $apiDir `
  -RedirectStandardOutput (Join-Path $logsDir "worker.out.log") `
  -RedirectStandardError (Join-Path $logsDir "worker.err.log") `
  -WindowStyle Hidden `
  -PassThru
$worker.Id | Set-Content -Encoding ASCII -Path (Join-Path $logsDir "agent-worker.pid")

$npm = "npm"
$customNpm = "D:\Program Files (x86)\want\npm.cmd"
if (Test-Path $customNpm) {
  $npm = $customNpm
}

Start-Process -FilePath "cmd.exe" `
  -ArgumentList "/c", "`"$npm`" run dev -- -H 0.0.0.0 -p 3000" `
  -WorkingDirectory $webDir `
  -RedirectStandardOutput (Join-Path $logsDir "web.out.log") `
  -RedirectStandardError (Join-Path $logsDir "web.err.log") `
  -WindowStyle Hidden

Start-Sleep -Seconds 6

Write-Host ""
Write-Host "JUNZAO QIYUAN LAN platform is starting."
Write-Host "Open on this computer: http://localhost:3000"
Write-Host "Share with teammates on the same Wi-Fi: http://${ip}:3000"
Write-Host "API health check: http://${ip}:8000/health"
Write-Host ""
Write-Host "If teammates cannot open it, allow ports 3000 and 8000 in Windows Firewall."
