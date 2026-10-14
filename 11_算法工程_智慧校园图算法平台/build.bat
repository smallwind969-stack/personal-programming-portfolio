@echo off
setlocal
chcp 65001 >nul
if not exist build mkdir build
g++ -std=c++17 -Wall -Wextra -Iinclude src\*.cpp -o build\smartcampus.exe
if errorlevel 1 exit /b 1
