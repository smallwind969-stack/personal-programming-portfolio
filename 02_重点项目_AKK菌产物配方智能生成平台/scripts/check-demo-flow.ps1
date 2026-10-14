param(
  [string]$ApiBaseUrl = "http://127.0.0.1:8000",
  [string]$WebBaseUrl = "http://127.0.0.1:3000",
  [string]$ExperimentId = "exp-eebc4a9daa21"
)

$ErrorActionPreference = "Stop"

function Get-Json([string]$Path) {
  $response = Invoke-WebRequest -Uri "$ApiBaseUrl$Path" -UseBasicParsing
  if ($response.StatusCode -ne 200) { throw "GET $Path returned $($response.StatusCode)" }
  $content = if ($null -ne $response.RawContentStream) {
    [System.Text.Encoding]::UTF8.GetString($response.RawContentStream.ToArray())
  } else {
    $response.Content
  }
  return ($content | ConvertFrom-Json)
}

function Assert-Equal([string]$Name, $Actual, $Expected) {
  if ($Actual -ne $Expected) { throw "$Name expected '$Expected' but got '$Actual'" }
  Write-Host "${Name}: $Actual [ok]"
}

$health = Get-Json "/health"
Assert-Equal "API health" $health.status "ok"

$archive = Get-Json "/experiments/archive"
if ($archive.totalCount -lt 1) { throw "Experiment archive is empty" }
Write-Host "Archive experiments: $($archive.totalCount) [ok]"

$overview = Get-Json "/experiments/$ExperimentId/overview"
Assert-Equal "Experiment id" $overview.experimentId $ExperimentId
if ([string]::IsNullOrWhiteSpace([string]$overview.productionContext.industry)) { throw "Production context industry is missing" }
if ([string]::IsNullOrWhiteSpace([string]$overview.productionContext.processType)) { throw "Production context process type is missing" }
Write-Host "Production context: $($overview.productionContext.industry) / $($overview.productionContext.processType) [ok]"
Write-Host "Experiment status: $($overview.status) / stage: $($overview.currentStage) [ok]"

$progress = Get-Json "/experiments/$ExperimentId/analysis-progress"
if ($progress.steps.Count -lt 3) { throw "Analysis progress has fewer than three steps" }
Write-Host "Analysis progress: $($progress.progressPercent)% / steps: $($progress.steps.Count) [ok]"

$simulation = Get-Json "/experiments/$ExperimentId/simulation-runs/latest"
Assert-Equal "Simulation run status" $simulation.status "completed"
if ($null -eq $simulation.officialResult) { throw "Simulation official result is missing" }
Write-Host "Simulation result: $($simulation.officialResult.snapshotId) [ok]"

$optimization = Get-Json "/experiments/$ExperimentId/optimization-runs/latest"
Assert-Equal "Optimization run status" $optimization.status "completed"
if ($null -eq $optimization.resultSummary) { throw "Optimization result summary is missing" }
if ([string]::IsNullOrWhiteSpace([string]$optimization.officialParameterVersion)) { throw "Optimization parameter version is missing" }
if ([string]::IsNullOrWhiteSpace([string]$optimization.newResultVersion)) { throw "Optimization result version is missing" }
Assert-Equal "Optimization source simulation" $optimization.baseSimulationRunId $simulation.runId
Write-Host "Optimization parameter version: $($optimization.officialParameterVersion) [ok]"
Write-Host "Optimization result version: $($optimization.newResultVersion) [ok]"

$webResponse = Invoke-WebRequest -Uri "$WebBaseUrl/experiments/$ExperimentId" -UseBasicParsing
Assert-Equal "Experiment workspace" $webResponse.StatusCode 200

foreach ($route in "agents", "innovation", "analysis", "simulation", "optimization", "reports") {
  $routeResponse = Invoke-WebRequest -Uri "$WebBaseUrl/experiments/$ExperimentId/$route" -UseBasicParsing
  Assert-Equal "Workspace route /$route" $routeResponse.StatusCode 200
}

$reports = @(Get-Json "/experiments/$ExperimentId/research-reports")
Write-Host "Research reports: $($reports.Count) [ok]"
if ($reports.Count -gt 0) {
  $latestReport = $reports[0]
  if ([string]::IsNullOrWhiteSpace([string]$latestReport.inputFingerprint)) { throw "Latest research report input fingerprint is missing" }
  if ($latestReport.sections.Count -lt 1) { throw "Latest research report has no sections" }
  Write-Host "Latest report version: $($latestReport.reportVersion) / sections: $($latestReport.sections.Count) [ok]"
  $reportPackage = Get-Json "/experiments/$ExperimentId/research-reports/$($latestReport.reportId)/json"
  Assert-Equal "Report package id" $reportPackage.reportId $latestReport.reportId
  Assert-Equal "Report package fingerprint" $reportPackage.inputFingerprint $latestReport.inputFingerprint
}

Write-Host "JUNZAO QIYUAN demo flow check passed."
