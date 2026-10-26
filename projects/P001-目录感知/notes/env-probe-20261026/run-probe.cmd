@echo off
call "D:\Microsoft Visual Studio\VC\Auxiliary\Build\vcvars64.bat" > "%~dp0vcvars.log" 2>&1
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /Zc:__cplusplus /EHsc /O2 "%~dp0probe.cpp" /Fe:"%~dp0probe.exe" /Fo:"%~dp0probe.obj" > "%~dp0build.log" 2>&1
if errorlevel 1 exit /b 2
"%~dp0probe.exe" > "%~dp0probe-output.json"
if errorlevel 1 exit /b 3
exit /b 0
