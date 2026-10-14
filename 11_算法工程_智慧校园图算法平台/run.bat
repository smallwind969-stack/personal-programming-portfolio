@echo off
setlocal
chcp 65001 >nul
call build.bat
if errorlevel 1 exit /b 1
build\smartcampus.exe
