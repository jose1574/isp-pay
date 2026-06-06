@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

rem ------------------------------------------------------------
rem Configuracion por variables de entorno o valores por defecto
rem ------------------------------------------------------------
if not defined SECRET_KEY set "SECRET_KEY=dev"
if not defined DB_HOST set "DB_HOST=localhost"
if not defined DB_PORT set "DB_PORT=5432"
if not defined DB_NAME set "DB_NAME=cadm_geniusnet"
if not defined DB_USER set "DB_USER=postgres"
if not defined DB_PASSWORD set "DB_PASSWORD=root"
if not defined AUTO_INIT_DB set "AUTO_INIT_DB=true"

set "AUTO_INIT_DB_PY=False"
if /I "%AUTO_INIT_DB%"=="true" set "AUTO_INIT_DB_PY=True"
if /I "%AUTO_INIT_DB%"=="1" set "AUTO_INIT_DB_PY=True"
if /I "%AUTO_INIT_DB%"=="yes" set "AUTO_INIT_DB_PY=True"

set "INSTANCE_DIR=%~dp0instance"
set "CONFIG_FILE=%INSTANCE_DIR%\config.py"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%INSTANCE_DIR%" mkdir "%INSTANCE_DIR%"
if not exist "%~dp0logs" mkdir "%~dp0logs"

if not exist "%PYTHON_EXE%" (
	where py >nul 2>nul
	if %ERRORLEVEL% EQU 0 (
		echo Creando entorno virtual con py -3...
		py -3 -m venv .venv
	) else (
		where python >nul 2>nul
		if %ERRORLEVEL% EQU 0 (
			echo Creando entorno virtual con python...
			python -m venv .venv
		) else (
			echo No se encontro Python en el sistema.
			pause
			exit /b 1
		)
	)
)

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
	echo No se pudo crear o localizar el entorno virtual.
	pause
	exit /b 1
)

echo ==============================================
echo Instalando dependencias
echo ==============================================
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 goto :error
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo ==============================================
echo Generando instance\config.py
echo ==============================================
(
	echo SECRET_KEY = '%SECRET_KEY%'
	echo SQLALCHEMY_DATABASE_URI = 'postgresql://%DB_USER%:%DB_PASSWORD%@%DB_HOST%:%DB_PORT%/%DB_NAME%'
	echo AUTO_INIT_DB = %AUTO_INIT_DB_PY%
) > "%CONFIG_FILE%"

echo Archivo generado en: %CONFIG_FILE%

echo ==============================================
echo Aplicando migraciones y creando tablas en genius
echo ==============================================
"%PYTHON_EXE%" -m flask --app flaskr migrate-db
if errorlevel 1 goto :error

echo ==============================================
echo Validando automatizaciones
echo ==============================================
"%PYTHON_EXE%" -m flask --app flaskr check-overdue-subscriptions
if errorlevel 1 goto :error
"%PYTHON_EXE%" -m flask --app flaskr check-paid-subscriptions
if errorlevel 1 goto :error

echo ==============================================
echo Instalacion completada correctamente
echo ==============================================
pause
exit /b 0

:error
echo.
echo Se produjo un error durante la instalacion.
pause
exit /b 1
