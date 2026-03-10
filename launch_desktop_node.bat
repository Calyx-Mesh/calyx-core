@echo off
title INGRVM_DESKTOP_NODE (1080 Ti)
echo 🌿 Starting INGRVM Desktop Node...

:: Set the base directory to the location of this script
set BASE_DIR=%~dp0
cd /d %BASE_DIR%

:: Use the stable Python 3.12 environment with CUDA
set PY_EXE=C:\Python312\python.exe

:: 1. Verify CUDA
%PY_EXE% -c "import torch; print('CUDA Detection:', torch.cuda.is_available()); print('Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NOT FOUND')"

:: 2. Get IP Address
echo.
echo 📡 Local IP Address:
ipconfig | findstr /i "IPv4"
echo.

:: 3. Kill existing Hub (if any) to prevent port 8000 conflict
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do taskkill /F /PID %%a 2>nul

:: 4. Start Hardware Pusher (Background)
start /b %PY_EXE% tools\hardware_pusher.py

:: 5. Start Hub Server
echo 🚀 Launching Hub Server on Port 8000...
%PY_EXE% hub_server.py

pause

