$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false) } catch {}
$apiBase = if ($env:API_BASE_URL) { $env:API_BASE_URL } else { "http://127.0.0.1:8000" }
$webBase = if ($env:WEB_BASE_URL) { $env:WEB_BASE_URL } else { "http://127.0.0.1:3000" }
try {
  $health = Invoke-RestMethod -Uri "$apiBase/health" -Method Get -TimeoutSec 8
  $assets = Invoke-RestMethod -Uri "$apiBase/simulation/model-assets" -Method Get -TimeoutSec 8
  $webCode = (& curl.exe -s -o NUL -w "%{http_code}" "$webBase/model-assets").Trim()
  if ($webCode -ne "200") { throw "工作台返回 HTTP $webCode" }
  $assetItems = if ($assets.items) { @($assets.items) } elseif ($assets.value) { @($assets.value) } else { @() }
  Write-Host "JUNZAO QIYUAN startup check passed."
  Write-Host "API health: $apiBase/health [$($health.status)]"
  Write-Host "Model assets: $($assetItems.Count)"
  Write-Host "Workbench: $webBase/model-assets [$webCode]"
  exit 0
} catch {
  Write-Error "Startup check failed: $($_.Exception.Message)"
  exit 1
}
