@echo off
REM Graph-Based Network Anomaly Detection — developer tasks (Windows)
REM Mirrors the Makefile targets: make.bat <target>

setlocal
set VENV=.venv
set PY=%VENV%\Scripts\python.exe
set PIP=%VENV%\Scripts\pip.exe

if "%~1"=="" goto help
if /I "%~1"=="help" goto help
if /I "%~1"=="venv" goto venv
if /I "%~1"=="install" goto install
if /I "%~1"=="run" goto run
if /I "%~1"=="test" goto test
if /I "%~1"=="test-verbose" goto test_verbose
if /I "%~1"=="convert-ctu13" goto convert_ctu13
if /I "%~1"=="convert-iot23" goto convert_iot23
if /I "%~1"=="docker" goto docker
if /I "%~1"=="docker-down" goto docker_down
if /I "%~1"=="clean" goto clean
echo Unknown target: %~1
goto help

:help
echo Available targets:
echo   venv            Create the virtual environment
echo   install         Create the venv and install dependencies
echo   run             Start the dashboard at http://127.0.0.1:8050
echo   test            Run the test suite
echo   test-verbose    Run the test suite with full output
echo   convert-ctu13   Convert a CTU-13 capture: make.bat convert-ctu13 path\to\file.binetflow [out.csv] ["Name"]
echo   convert-iot23   Convert an IoT-23 conn.log.labeled: make.bat convert-iot23 path\to\conn.log.labeled [out.csv] ["Name"]
echo   docker          Build and run with Docker Compose
echo   docker-down     Stop the Docker Compose stack
echo   clean           Remove the venv and caches
goto :eof

:venv
python -m venv %VENV%
goto :eof

:install
if not exist %PY% python -m venv %VENV%
%PIP% install --upgrade pip
%PIP% install -r requirements.txt
goto :eof

:run
%PY% app.py
goto :eof

:test
%PY% -m pytest tests/ -q
goto :eof

:test_verbose
%PY% -m pytest tests/ -v
goto :eof

:convert_ctu13
if "%~2"=="" (
    echo Usage: make.bat convert-ctu13 path\to\capture.binetflow [output.csv] ["Scenario name"]
    goto :eof
)
set OUT=%~3
if "%OUT%"=="" set OUT=data\ctu13_scenario9.csv
set NAME=%~4
if "%NAME%"=="" set NAME=CTU-13 Real Botnet (Neris)
%PY% scripts\convert_ctu13.py "%~2" "%OUT%" "%NAME%"
goto :eof

:convert_iot23
if "%~2"=="" (
    echo Usage: make.bat convert-iot23 path\to\conn.log.labeled [output.csv] ["Scenario name"]
    goto :eof
)
set OUT=%~3
if "%OUT%"=="" set OUT=data\iot23_scenario3.csv
set NAME=%~4
if "%NAME%"=="" set NAME=IoT-23 Real Botnet (Port Scan)
%PY% scripts\convert_iot23.py "%~2" "%OUT%" "%NAME%"
goto :eof

:docker
docker compose up --build
goto :eof

:docker_down
docker compose down
goto :eof

:clean
if exist %VENV% rmdir /S /Q %VENV%
if exist .pytest_cache rmdir /S /Q .pytest_cache
for /D /R %%d in (__pycache__) do @if exist "%%d" rmdir /S /Q "%%d"
goto :eof
