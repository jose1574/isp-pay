@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
set "LOG_DIR=%~dp0logs"
set "LOG_FILE=%LOG_DIR%\overdue_subscriptions.log"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

if not exist "%PYTHON_EXE%" (
	echo No se encontro el interprete de Python en: %PYTHON_EXE%
	echo Verifica que el entorno virtual .venv exista en la raiz del proyecto.
	pause
	exit /b 1
)

echo ==============================================
echo Ejecutando revision de suscripciones vencidas
echo Log: %LOG_FILE%
echo ==============================================

call "%PYTHON_EXE%" -m flask --app flaskr check-overdue-subscriptions >> "%LOG_FILE%" 2>&1
set "EXIT_CODE=%ERRORLEVEL%"

echo.
echo ==============================================
echo Resultado de ejecucion
echo Codigo de salida: %EXIT_CODE%
echo ==============================================
echo.

type "%LOG_FILE%"
echo.
pause

exit /b %EXIT_CODE%
