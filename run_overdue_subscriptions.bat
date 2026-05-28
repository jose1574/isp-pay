@echo off
setlocal
cd /d "%~dp0"
call ".\venv\Scripts\python.exe" -m flask --app flaskr check-overdue-subscriptions
