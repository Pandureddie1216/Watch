@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo Pandu AI Trading Agent - LAN HOST
echo ============================================

where py >nul 2>&1
if errorlevel 1 goto NO_PY

if not exist ".venv\Scripts\python.exe" goto CREATE_ENV
goto ENV_READY

:CREATE_ENV
echo Creating Python virtual environment...
py -3.12 -m venv .venv >nul 2>&1
if not errorlevel 1 goto ENV_READY
py -3.11 -m venv .venv
if errorlevel 1 goto ENV_FAIL

:ENV_READY
echo Installing/checking required packages...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto PIP_FAIL
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto PIP_FAIL

echo.
echo Starting Pandu AI on all network interfaces...
echo On this PC: http://127.0.0.1:8502
echo On other PCs: http://YOUR-HOST-PC-IP:8502
echo Keep this window open while others are using the app.
echo.
start "" "http://127.0.0.1:8502"
".venv\Scripts\python.exe" -m streamlit run app.py --server.address 0.0.0.0 --server.port 8502 --server.headless true
goto END

:NO_PY
echo Python Launcher was not found.
echo Install Python 3.11 or 3.12 (64-bit), then run this file again.
goto END

:ENV_FAIL
echo Could not create the virtual environment.
echo Install Python 3.11 or 3.12 (64-bit), then try again.
goto END

:PIP_FAIL
echo Package installation failed. Check your internet connection.
goto END

:END
echo.
pause
endlocal
