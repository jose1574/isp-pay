@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "FLASK_APP=flaskr"
set "FLASK_ENV=production"
set "FLASK_DEBUG=0"
if not exist "logs" mkdir "logs"
set "LOG_FILE=logs\run.log"
set "PYTHON_CMD="

call :try_python ".venv\Scripts\python.exe"
if not defined PYTHON_CMD call :try_python "venv\Scripts\python.exe"
if not defined PYTHON_CMD call :try_python "python"

echo ==================================================>> "%LOG_FILE%"
echo Inicio de ejecucion: %date% %time%>> "%LOG_FILE%"

if not defined PYTHON_CMD (
	echo ERROR: no se encontro un interprete de Python con Flask instalado.>> "%LOG_FILE%"
	echo Instala dependencias con: python -m pip install -r requirements.txt>> "%LOG_FILE%"
	exit /b 1
)

echo Python seleccionado: %PYTHON_CMD%>> "%LOG_FILE%"
start "" /B "%PYTHON_CMD%" -c "import logging; logging.getLogger('werkzeug').setLevel(logging.ERROR); from flaskr import app; app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)" >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% neq 0 echo ERROR: no se pudo iniciar Flask >> "%LOG_FILE%"
echo Proceso Flask lanzado en segundo plano: %date% %time%>> "%LOG_FILE%"
exit /b 0

:try_python
set "CANDIDATE=%~1"
if defined PYTHON_CMD exit /b 0

if /I "%CANDIDATE%"=="python" (
	python -c "import flask, flask_sqlalchemy, sqlalchemy, psycopg2, librouteros" >nul 2>&1
	if not errorlevel 1 set "PYTHON_CMD=python"
	exit /b 0
)

if exist "%CANDIDATE%" (
	"%CANDIDATE%" -c "import flask, flask_sqlalchemy, sqlalchemy, psycopg2, librouteros" >nul 2>&1
	if not errorlevel 1 set "PYTHON_CMD=%CANDIDATE%"
)
exit /b 0