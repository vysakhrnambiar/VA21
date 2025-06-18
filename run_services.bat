@echo off
echo Starting Home Assistant Live service manager...
echo This script ensures services run in the proper virtual environment

REM Activate the virtual environment
call Scripts\activate.bat 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Virtual environment not found in current directory.
    echo Please run this script from the project root where the virtual environment is located
    echo or manually activate your virtual environment before running the process_manager.py script.
    exit /b 1
)

REM Run the process manager
python process_manager.py

REM If process manager exits, deactivate the virtual environment
call deactivate