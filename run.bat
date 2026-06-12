@echo off
cd /d "%~dp0"
set FLASK_APP=flaskr
if not exist "logs" mkdir "logs"
set LOG_FILE=logs\run.log
set "PYTHON_CMD=python"

if exist ".venv\Scripts\pythonw.exe" set "PYTHON_CMD=.venv\Scripts\pythonw.exe"
if "%PYTHON_CMD%"=="python" if exist "venv\Scripts\pythonw.exe" set "PYTHON_CMD=venv\Scripts\pythonw.exe"
if "%PYTHON_CMD%"=="python" if exist ".venv\Scripts\python.exe" set "PYTHON_CMD=.venv\Scripts\python.exe"
if "%PYTHON_CMD%"=="python" if exist "venv\Scripts\python.exe" set "PYTHON_CMD=venv\Scripts\python.exe"

echo ==================================================>> "%LOG_FILE%"
echo Inicio de ejecucion: %date% %time%>> "%LOG_FILE%"
start "" /B "%PYTHON_CMD%" -m flask run --host=0.0.0.0 --port=5000 >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% neq 0 echo ERROR: no se pudo iniciar Flask >> "%LOG_FILE%"
echo Proceso Flask lanzado en segundo plano: %date% %time%>> "%LOG_FILE%"
exit /b 0