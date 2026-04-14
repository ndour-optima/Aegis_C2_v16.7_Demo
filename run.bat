@echo off
setlocal ENABLEDELAYEDEXPANSION
cd /d %~dp0

echo ============================================
echo   AEGIS C2 QUANTUM DUAL USE — v16.7 FMV Demo Hardening
echo ============================================

call C:\z_data\VENV\Aegis_Venv\Scripts\activate.bat

for %%P in (8502 8503 8504 8505) do (
  for /f "tokens=5" %%a in ('netstat -aon ^| findstr :%%P') do taskkill /F /PID %%a >nul 2>&1
)

set PORT=8502
:check_port
netstat -aon | findstr :%PORT% >nul
if %ERRORLEVEL%==0 (
  set /a PORT+=1
  goto check_port
)

echo Using port %PORT%
start "" http://localhost:%PORT%
streamlit run app.py --server.port %PORT% --server.headless true
pause
