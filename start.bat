@echo off
chcp 65001 >nul 2>&1
title MyTV - Start
set "SCRIPT_DIR=%~dp0"
set "HTML_FILE=%SCRIPT_DIR%tv-player.html"
set "PROXY_SCRIPT=%SCRIPT_DIR%proxy-server.py"
set "PORT_FILE=%SCRIPT_DIR%.proxy_port"

echo.
echo ============================================
echo   MyTV Portable TV Player - Starting...
echo ============================================
echo.

set "PYTHON_EXE="
if exist "C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe" (
    set "PYTHON_EXE=C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe"
    echo [OK] Found managed Python
    goto :found_python
)
if exist "C:\Python313\python.exe" (
    set "PYTHON_EXE=C:\Python313\python.exe"
    echo [OK] Found system Python
    goto :found_python
)
if exist "C:\Python312\python.exe" (
    set "PYTHON_EXE=C:\Python312\python.exe"
    echo [OK] Found system Python
    goto :found_python
)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    echo [OK] Found user Python
    goto :found_python
)
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    echo [OK] Found Python in PATH
    goto :found_python
)

echo [ERROR] Python 3 not found!
echo Please install Python 3: https://www.python.org/downloads/
echo.
pause
exit /b 1

:found_python
echo [CHECK] %PYTHON_EXE% --version
"%PYTHON_EXE%" --version 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python cannot execute!
    pause
    exit /b 1
)

if exist "%PORT_FILE%" del "%PORT_FILE%" 2>nul

echo [START] Starting local CORS proxy...
start "MyTV-Proxy" /min cmd /c ""%PYTHON_EXE%" "%PROXY_SCRIPT%" > "%SCRIPT_DIR%proxy.log" 2>&1"

echo [WAIT] Waiting for proxy to be ready...
set /a RETRY=0
:wait_loop
ping 127.0.0.1 -n 2 >nul
set /a RETRY+=1

if exist "%PORT_FILE%" (
    set /p PROXY_PORT=<"%PORT_FILE%"
    call echo [READY] Proxy started: http://127.0.0.1:%%PROXY_PORT%%
    goto :open_browser
)

if %RETRY% lss 15 goto :wait_loop

echo [WARN] Proxy startup timeout (%RETRY%s)
if exist "%SCRIPT_DIR%proxy.log" type "%SCRIPT_DIR%proxy.log" 2>nul
echo Will open player anyway (remote sources may fail)
goto :open_browser

:open_browser
echo [OPEN] Opening player...
start "" "%HTML_FILE%"

echo.
echo ============================================
echo   MyTV Started!
echo   Tips: Enter M3U URL -> Load, or Local File
echo   Keyboard: Arrows=ch/group, 0-9=select, F=fav
echo ============================================
echo.

