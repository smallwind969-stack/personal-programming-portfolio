$ErrorActionPreference = "SilentlyContinue"

foreach ($port in 3000, 8000) {
  $listeners = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
    Where-Object { $_.State -eq "Listen" } |
    Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($processId in $listeners) {
    Stop-Process -Id $processId -Force
  }
}

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$workerPidFile = Join-Path $root "logs\agent-worker.pid"
if (Test-Path -LiteralPath $workerPidFile) {
  $workerId = Get-Content -LiteralPath $workerPidFile | Select-Object -First 1
  if ($workerId -match '^\d+$') { Stop-Process -Id ([int]$workerId) -Force }
  Remove-Item -LiteralPath $workerPidFile -Force
}

Write-Host "JUNZAO QIYUAN local services stopped."
