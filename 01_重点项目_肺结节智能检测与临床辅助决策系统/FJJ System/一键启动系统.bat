@echo off
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

if exist "%ROOT%runtime\python\python.exe" (
  echo Using bundled offline Python runtime.
) else (
  echo Checking local Python runtime...
  py -c "import flask, flask_cors, torch, numpy, SimpleITK, PIL, scipy, skimage" >nul 2>nul
  if errorlevel 1 (
    echo.
    echo No bundled runtime found, and local Python dependencies are incomplete.
    echo Please use the full offline package that includes runtime\python.
    pause
    exit /b 1
  )
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%start_agent_api.ps1"

endlocal
