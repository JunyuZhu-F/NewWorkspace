@echo off
setlocal
call "D:\Microsoft Visual Studio\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
set "CMAKE=D:\Microsoft Visual Studio\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
set "CONFIG=Release"
set "ASAN=OFF"
set "TAG=Release-ScaleFormal"
if "%~1"=="asan" set "CONFIG=RelWithDebInfo"
if "%~1"=="asan" set "ASAN=ON"
if "%~1"=="asan" set "TAG=RelWithDebInfo-ASan-ScaleFormal"
set "OUT=%~dp0..\build-%TAG%"
"%CMAKE%" -S "%~dp0..\scale_formal" -B "%OUT%" -G Ninja -DCMAKE_MAKE_PROGRAM=D:/anaconda3/Scripts/ninja.exe -DCMAKE_BUILD_TYPE=%CONFIG% -DDIRECTORY_ENABLE_ASAN=%ASAN% -DDIRECTORY_BUILD_COST_DIAGNOSTICS=OFF
if errorlevel 1 exit /b 2
"%CMAKE%" --build "%OUT%" --target scale_formal --parallel 2
if errorlevel 1 exit /b 3
