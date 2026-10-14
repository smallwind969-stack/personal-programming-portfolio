@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0\.."
call build.bat
if errorlevel 1 exit /b 1
(
echo 2
echo 1
echo 8
echo 6
echo 7
echo 0
) | build\smartcampus.exe
