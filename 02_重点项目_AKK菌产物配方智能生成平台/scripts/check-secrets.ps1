param([string]$Root = (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)))

$ErrorActionPreference = "Stop"
$targets = @("apps", "scripts", "deploy", "docs", ".env.example", ".env.production.example", ".env.server.example", "docker-compose.yml")
$existing = $targets | ForEach-Object { Join-Path $Root $_ } | Where-Object { Test-Path $_ }
$matches = & rg -n --no-heading --glob "!node_modules/**" --glob "!.next/**" --glob "!*.tsbuildinfo" --glob "!data/runtime/**" --glob "!apps/api/data/runtime/**" "sk-[A-Za-z0-9_-]{20,}" @existing 2>$null

if ($LASTEXITCODE -eq 0 -and $matches) {
  Write-Error "Potential API secret found in source files:`n$($matches -join [Environment]::NewLine)"
}
if ($LASTEXITCODE -notin 0, 1) { throw "Secret scan failed with exit code $LASTEXITCODE" }

Write-Host "Secret scan passed: no API key pattern found in source or deployment files."

