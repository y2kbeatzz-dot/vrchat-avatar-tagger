@echo off
setlocal
cd /d "%~dp0"
title VRChat Avatar Tagger Launcher

echo Starting VRChat Avatar Tagger...
echo.

where py >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python was not found.
  echo Install Python 3 from https://www.python.org/downloads/windows/
  echo During setup, check "Add python.exe to PATH", then run this file again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo First-time setup: creating the private Python environment...
  py -3 -m venv .venv
  if errorlevel 1 goto :failed
)

echo Checking required package...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :failed

echo Opening the app...
".venv\Scripts\python.exe" tag_avatars_gui.py
if errorlevel 1 goto :failed
exit /b 0

:failed
echo.
echo ERROR: The app could not start. The useful error is shown above.
echo Take a screenshot of this window if you need more help.
pause
exit /b 1
