@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  set "PYTHON=py"
) else (
  set "PYTHON=python"
)

%PYTHON% -c "import tkinter" >nul 2>nul
if errorlevel 1 (
  echo Tkinter/Tcl-Tk support is missing from this Python installation.
  echo Reinstall Python from python.org and make sure Tcl/Tk is included.
  exit /b 1
)

if not exist .venv (
  %PYTHON% -m venv .venv
  if errorlevel 1 exit /b 1
)

call .venv\Scripts\activate.bat
python -c "import tkinter" >nul 2>nul
if errorlevel 1 (
  echo Tkinter is not available inside this venv. Recreate the venv.
  exit /b 1
)

echo.
echo Setup complete. No pip UI packages were installed.
echo Run:
echo   .venv\Scripts\activate
echo   python run_manager.py
