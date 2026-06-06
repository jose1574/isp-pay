@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

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
echo Aplicando migraciones y creando tablas en genius
echo ==============================================
"%PYTHON_EXE%" -m flask --app flaskr migrate-db
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
