@echo off
title CELESTIA BOT Launcher
echo ==================================================
echo   CELESTIA BOT - LAUNCHER
echo ==================================================
echo.
echo [1/2] Checking and installing Python dependencies...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Failed to install dependencies. Make sure Python is installed and added to PATH.
    pause
    exit /b
)
echo.
echo [2/2] Launching the Discord Tournament Bot...
echo.
python main.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Bot stopped with an error. 
    echo Please make sure you have put your real Discord token in the .env file.
)
echo.
pause
