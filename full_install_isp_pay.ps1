Param(
    [string]$SecretKey = $(if ($env:SECRET_KEY) { $env:SECRET_KEY } else { 'dev' }),
    [string]$DbHost = $(if ($env:DB_HOST) { $env:DB_HOST } else { 'localhost' }),
    [string]$DbPort = $(if ($env:DB_PORT) { $env:DB_PORT } else { '5432' }),
    [string]$DbName = $(if ($env:DB_NAME) { $env:DB_NAME } else { 'cadm_geniusnet' }),
    [string]$DbUser = $(if ($env:DB_USER) { $env:DB_USER } else { 'postgres' }),
    [string]$DbPassword = $(if ($env:DB_PASSWORD) { $env:DB_PASSWORD } else { 'root' }),
    [string]$AutoInitDb = $(if ($env:AUTO_INIT_DB) { $env:AUTO_INIT_DB } else { 'true' })
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$instanceDir = Join-Path $PSScriptRoot 'instance'
$configFile = Join-Path $instanceDir 'config.py'
$pythonExe = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$autoInitDbPython = if ($AutoInitDb -match '^(?i:true|1|yes)$') { 'True' } else { 'False' }

if (-not (Test-Path $instanceDir)) {
    New-Item -ItemType Directory -Path $instanceDir | Out-Null
}

if (-not (Test-Path (Join-Path $PSScriptRoot 'logs'))) {
    New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot 'logs') | Out-Null
}

if (-not (Test-Path $pythonExe)) {
    $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        Write-Host 'Creando entorno virtual con py -3...'
        & py -3 -m venv .venv
    } else {
        $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
        if ($pythonCmd) {
            Write-Host 'Creando entorno virtual con python...'
            & python -m venv .venv
        } else {
            throw 'No se encontro Python en el sistema.'
        }
    }
}

if (-not (Test-Path $pythonExe)) {
    throw 'No se pudo crear o localizar el entorno virtual.'
}

Write-Host '=============================================='
Write-Host 'Instalando dependencias'
Write-Host '=============================================='
& $pythonExe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'Fallo la actualizacion de pip.' }
& $pythonExe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Fallo la instalacion de dependencias.' }

Write-Host '=============================================='
Write-Host 'Generando instance/config.py'
Write-Host '=============================================='
$configContent = @"
SECRET_KEY = '$SecretKey'
SQLALCHEMY_DATABASE_URI = 'postgresql://$DbUser`:$DbPassword@$DbHost`:$DbPort/$DbName'
AUTO_INIT_DB = $autoInitDbPython
"@
Set-Content -Path $configFile -Value $configContent -Encoding UTF8
Write-Host "Archivo generado en: $configFile"

Write-Host '=============================================='
Write-Host 'Aplicando migraciones y creando tablas en genius'
Write-Host '=============================================='
& $pythonExe -m flask --app flaskr migrate-db
if ($LASTEXITCODE -ne 0) { throw 'Fallo la aplicacion de migraciones.' }

Write-Host '=============================================='
Write-Host 'Validando automatizaciones'
Write-Host '=============================================='
& $pythonExe -m flask --app flaskr check-overdue-subscriptions
if ($LASTEXITCODE -ne 0) { throw 'Fallo la revision de vencidos.' }
& $pythonExe -m flask --app flaskr check-paid-subscriptions
if ($LASTEXITCODE -ne 0) { throw 'Fallo la reactivacion por pagos.' }

Write-Host '=============================================='
Write-Host 'Instalacion completada correctamente'
Write-Host '=============================================='
