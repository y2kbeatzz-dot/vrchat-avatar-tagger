#!/bin/bash
# Double-click launcher for running from a downloaded source checkout.
set -e
cd "$(dirname "$0")"
echo "VRChat Avatar Tagger — macOS launcher"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is missing. Install it from https://www.python.org/downloads/macos/"
  read -r -p "Press Enter to close..."
  exit 1
fi
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
  echo "This Python installation does not include tkinter. Install Python from python.org."
  read -r -p "Press Enter to close..."
  exit 1
fi
if [ ! -f .venv/bin/python3 ]; then
  python3 -m venv .venv
fi
.venv/bin/python3 -m pip install -r requirements.txt
.venv/bin/python3 tag_avatars_gui.py
