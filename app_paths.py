"""Paths and session storage for source checkouts and packaged desktop apps."""
import os
import sys
from pathlib import Path

APP_NAME = "VRChat Avatar Tagger"
SOURCE_DIR = Path(__file__).resolve().parent

def resource_file(name):
    base = Path(getattr(sys, "_MEIPASS", SOURCE_DIR))
    return str(base / name)

def data_directory():
    if sys.platform == "darwin":
        folder = Path.home() / "Library" / "Application Support" / APP_NAME
    elif getattr(sys, "frozen", False) and sys.platform == "win32":
        folder = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")) / APP_NAME
    elif getattr(sys, "frozen", False):
        folder = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")) / "vrchat-avatar-tagger"
    else:
        folder = SOURCE_DIR
    folder.mkdir(parents=True, exist_ok=True)
    if os.name == "posix" and folder != SOURCE_DIR:
        try:
            folder.chmod(0o700)
        except OSError:
            pass
    return str(folder)

def save_session_securely(cookie_jar, path):
    """Store VRChat cookies and restrict file permissions on macOS/Linux."""
    cookie_jar.save(ignore_discard=True, ignore_expires=True)
    if os.name == "posix":
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
