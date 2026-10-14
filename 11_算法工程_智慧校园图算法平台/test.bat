@echo off
setlocal
chcp 65001 >nul
if not exist build mkdir build
g++ -std=c++17 -Wall -Wextra -Iinclude tests\graph_algorithms_test.cpp src\Graph.cpp src\GraphAlgorithms.cpp -o build\graph_algorithms_test.exe
if errorlevel 1 exit /b 1
build\graph_algorithms_test.exe
