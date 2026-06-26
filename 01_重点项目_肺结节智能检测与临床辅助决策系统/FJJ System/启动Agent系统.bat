@echo off
setlocal

set "ROOT=%~dp0"
set "OLLAMA_EXE=%ROOT%..\Ollama\ollama.exe"
set "OLLAMA_MODEL=qwen3:8b"
set "PYTHONPATH=%ROOT%vendor;%PYTHONPATH%"

if not exist "%OLLAMA_EXE%" (
  echo Ollama not found:
  echo %OLLAMA_EXE%
  pause
  exit /b 1
)

echo Starting Ollama service...
start "Ollama" /min "%OLLAMA_EXE%" serve

echo Starting FJJ System on http://127.0.0.1:5001 ...
cd /d "%ROOT%"
py app2.py

endlocal
