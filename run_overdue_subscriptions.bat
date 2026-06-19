@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "PYTHON_EXE="
set "LOG_DIR=%~dp0logs"
set "LOG_FILE=%LOG_DIR%\overdue_subscriptions.log"
set "LAST_RUN_LOG=%LOG_DIR%\overdue_subscriptions_last.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

call :try_python "%~dp0.venv\Scripts\python.exe"
if not defined PYTHON_EXE call :try_python "%~dp0venv\Scripts\python.exe"
if not defined PYTHON_EXE call :try_python "python"

if not defined PYTHON_EXE (
	echo No se encontro un interprete de Python con las dependencias instaladas.
	echo Instala dependencias con: python -m pip install -r requirements.txt
	pause
	exit /b 1
)

echo ==============================================
echo Ejecutando revision de suscripciones vencidas
echo Log: %LOG_FILE%
echo ==============================================

echo ==============================================>> "%LOG_FILE%"
echo Inicio de ejecucion: %date% %time%>> "%LOG_FILE%"
echo Python seleccionado: %PYTHON_EXE%>> "%LOG_FILE%"

call "%PYTHON_EXE%" -m flask --app flaskr check-overdue-subscriptions > "%LAST_RUN_LOG%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"
type "%LAST_RUN_LOG%" >> "%LOG_FILE%"
>> "%LOG_FILE%" echo Codigo de salida: %EXIT_CODE%

echo.
echo ==============================================
echo Resultado de ejecucion
echo Codigo de salida: %EXIT_CODE%
echo ==============================================
echo.

type "%LAST_RUN_LOG%"
echo.
pause

exit /b %EXIT_CODE%

:try_python
set "CANDIDATE=%~1"
if defined PYTHON_EXE exit /b 0

if /I "%CANDIDATE%"=="python" (
	python -c "import flask, flask_sqlalchemy, sqlalchemy, psycopg2, librouteros" >nul 2>&1
	if not errorlevel 1 set "PYTHON_EXE=python"
	exit /b 0
)

if exist "%CANDIDATE%" (
	"%CANDIDATE%" -c "import flask, flask_sqlalchemy, sqlalchemy, psycopg2, librouteros" >nul 2>&1
	if not errorlevel 1 set "PYTHON_EXE=%CANDIDATE%"
)
exit /b 0
