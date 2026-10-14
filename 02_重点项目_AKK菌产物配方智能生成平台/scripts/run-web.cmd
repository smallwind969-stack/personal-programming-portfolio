@echo off
set ROOT=%~dp0..
cd /d "%ROOT%\apps\web"
set NEXT_TELEMETRY_DISABLED=1
npm.cmd run start -- -H 0.0.0.0 -p 3000
