@echo off
setlocal
call "D:\Microsoft Visual Studio\VC\Auxiliary\Build\vcvars64.bat"
if errorlevel 1 exit /b 1
set "CMAKE=D:\Microsoft Visual Studio\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
set "CTEST=D:\Microsoft Visual Studio\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\ctest.exe"
set "CONFIG=%~1"
if "%CONFIG%"=="" set "CONFIG=Release"
set "TAG=%CONFIG%"
set "ASAN=OFF"
if "%~2"=="asan" set "TAG=%CONFIG%-ASan"
if "%~2"=="asan" set "ASAN=ON"
set "OUT=%~dp0..\build-%TAG%"
python "%~dp0prepare-time-fixture.py" --project "%~dp0..\.." --output "%OUT%\time-pilot.tsv"
if errorlevel 1 exit /b 2
python "%~dp0prepare-benchmark-fixtures.py" --project "%~dp0..\.." --output "%~dp0..\..\notes\benchmark-fixtures-20261026-01"
if errorlevel 1 exit /b 2
"%CMAKE%" -S "%~dp0.." -B "%OUT%" -G Ninja -DCMAKE_MAKE_PROGRAM=D:/anaconda3/Scripts/ninja.exe -DCMAKE_BUILD_TYPE=%CONFIG% -DDIRECTORY_ENABLE_ASAN=%ASAN% "-DDIRECTORY_PILOT_TSV=%OUT%\time-pilot.tsv"
if errorlevel 1 exit /b 3
"%CMAKE%" --build "%OUT%" --parallel 2
if errorlevel 1 exit /b 4
"%CTEST%" --test-dir "%OUT%" --output-on-failure
if errorlevel 1 exit /b 5
"%OUT%\directory_benchmark.exe" self-test "%~dp0..\..\notes\benchmark-fixtures-20261026-01"
if errorlevel 1 exit /b 6
"%OUT%\directory_benchmark_instrumented.exe" self-test "%~dp0..\..\notes\benchmark-fixtures-20261026-01"
if errorlevel 1 exit /b 7
exit /b 0
