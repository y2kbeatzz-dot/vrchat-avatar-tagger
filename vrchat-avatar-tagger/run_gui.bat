@echo off
echo Starting VRChat Avatar Tagger...
echo (If this is your first time, it may take a moment to install requirements.)
python -m pip install --quiet vrchatapi --break-system-packages >nul 2>&1
python tag_avatars_gui.py
if errorlevel 1 (
  echo.
  echo Something went wrong -- see the error above.
  pause
)
