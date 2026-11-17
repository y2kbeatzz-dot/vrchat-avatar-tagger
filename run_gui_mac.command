#!/bin/bash
# Source-code launcher; binary DMG releases don't require Python.
set -e
cd "$(dirname "$0")"
echo "VRChat Avatar Tagger — modern Qt edition"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is missing. Install Python from python.org."
  read -r -p "Press Enter to close..."
  exit 1
fi
if [ ! -x .venv/bin/python3 ]; then
  python3 -m venv .venv
fi
.venv/bin/python3 -m pip install -r requirements.txt
.venv/bin/python3 tag_avatars_qt.py
