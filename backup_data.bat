@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "backups" mkdir "backups"
for /f "tokens=1-4 delims=/-. " %%a in ("%date%") do set TODAY=%%d-%%b-%%c
for /f "tokens=1-2 delims=:" %%a in ("%time%") do set NOW=%%a-%%b
set NOW=%NOW: =0%
copy "data\mxs.db" "backups\mxs_backup_%TODAY%_%NOW%.db"
echo Backup created in backups folder.
pause
