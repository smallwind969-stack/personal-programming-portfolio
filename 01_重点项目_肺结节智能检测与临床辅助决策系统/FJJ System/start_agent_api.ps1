$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONPATH = (Join-Path $root "vendor") + ";" + $env:PYTHONPATH

if ([string]::IsNullOrWhiteSpace($env:LLM_API_BASE)) {
    $env:LLM_API_BASE = "https://ai.rjyunk.com/v1"
}
if ([string]::IsNullOrWhiteSpace($env:LLM_MODEL)) {
    $env:LLM_MODEL = "gpt-5.3-codex-spark"
}

Write-Host "正在启动肺结节智能辅助诊断工作台..." -ForegroundColor Cyan
Write-Host "大模型接口：$env:LLM_API_BASE"
Write-Host "大模型名称：$env:LLM_MODEL"
Write-Host "API Key 来源：优先读取环境变量，其次读取 llm_api_config.py"
Write-Host "访问地址：http://127.0.0.1:5001"
Write-Host ""

Set-Location $root
$bundledPython = Join-Path $root "runtime\python\python.exe"
if (Test-Path $bundledPython) {
    & $bundledPython app2.py
} else {
    py app2.py
}

