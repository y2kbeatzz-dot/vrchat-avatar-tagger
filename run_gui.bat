@echo off
setlocal
cd /d "%~dp0"
title VRChat Avatar Tagger

where py >nul 2>&1
if errorlevel 1 (
  echo Python is missing. Install Python 3 from https://python.org/downloads/windows/
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto :failed
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :failed
".venv\Scripts\python.exe" tag_avatars_qt.py
if errorlevel 1 goto :failed
exit /b 0
:failed
echo.
echo App could not start. See the error above.
pause
exit /b 1
