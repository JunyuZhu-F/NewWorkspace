@echo off
setlocal
call "D:\Microsoft Visual Studio\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
set "CMAKE=D:\Microsoft Visual Studio\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
set "CONFIG=Release"
set "ASAN=OFF"
set "TAG=Release-WikiExperiment"
if "%~1"=="asan" set "CONFIG=RelWithDebInfo"
if "%~1"=="asan" set "ASAN=ON"
if "%~1"=="asan" set "TAG=RelWithDebInfo-ASan-WikiExperiment"
set "OUT=%~dp0..\build-%TAG%"
"%CMAKE%" -S "%~dp0..\wiki_experiment" -B "%OUT%" -G Ninja -DCMAKE_MAKE_PROGRAM=D:/anaconda3/Scripts/ninja.exe -DCMAKE_BUILD_TYPE=%CONFIG% -DDIRECTORY_ENABLE_ASAN=%ASAN% -DDIRECTORY_BUILD_COST_DIAGNOSTICS=OFF
if errorlevel 1 exit /b 2
"%CMAKE%" --build "%OUT%" --target wiki_directory wiki_directory_phase wiki_search --parallel 2
if errorlevel 1 exit /b 3
