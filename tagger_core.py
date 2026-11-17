"""Network and persistence helpers shared by the modern Qt desktop UI.

This module does not create widgets or run network calls at import time.
"""
import atexit
import http.cookiejar
import json
import os
import ssl
import sys
import time
from pathlib import Path
from threading import RLock

import vrchatapi
from vrchatapi.api import authentication_api, avatars_api
from vrchatapi.exceptions import UnauthorizedException
from vrchatapi.models.two_factor_auth_code import TwoFactorAuthCode
from vrchatapi.models.two_factor_email_code import TwoFactorEmailCode
from vrchatapi.models.update_avatar_request import UpdateAvatarRequest

from app_paths import data_directory, save_session_securely

def _configure_native_tls(client):
    """Use OS-trusted certificates for this VRChat HTTP client only.

    urllib3's packaged OpenSSL roots can disagree with the macOS Keychain or
    Windows trust store. Truststore validates the chain against native
    certificate authorities without disabling verification or hostname checks.
    """
    if sys.platform not in ("darwin", "win32"):
        return
    import truststore
    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    # The VRChat SDK builds urllib3's PoolManager during ApiClient init.
    # Configure its existing manager *before* any network request starts.
    client.rest_client.pool_manager.connection_pool_kw["ssl_context"] = context


def friendly_login_error(exc):
    """Explain TLS errors without exposing lengthy urllib3 traceback text."""
    message = str(exc)
    lowered = message.lower()
    if (
        "certificate_verify_failed" in lowered
        or "certificate verify failed" in lowered
        or "self-signed certificate" in lowered
        or "self signed certificate" in lowered
    ):
        return (
            "Secure connection to VRChat could not be verified.\n\n"
            "The app checks certificates trusted by your operating system. "
            "If you still see this message, your VPN, security software, "
            "school/work network, or proxy may be presenting a certificate "
            "your computer does not trust.\n\n"
            "Try a different trusted network, check your Mac's date and time, "
            "and temporarily disconnect a VPN or HTTPS-filtering tool if "
            "you control it. If this is a managed network, ask its administrator "
            "to verify the certificate.\n\n"
            "For your account's safety, SSL verification remains enabled. "
            "Do not install an unknown root certificate or disable verification."
        )
    return f"{type(exc).__name__}: {message}"


DATA_DIR = Path(data_directory())
COOKIE_FILE = DATA_DIR / "vrchat_session.cookies"
PROGRESS_FILE = DATA_DIR / "tagger_progress.json"
REQUEST_DELAY = 1.2

CONTENT_TAGS = [
    ("Sexually Suggestive", "content_sex"),
    ("Adult Language and Themes", "content_adult"),
    ("Graphic Violence", "content_violence"),
    ("Excessive Gore", "content_gore"),
    ("Extreme Horror", "content_horror"),
]


def normalize_tag(value):
    return value.strip().lower().replace(" ", "_")


def operation_key(tags, remove):
    return ("remove" if remove else "add") + ":" + ",".join(sorted(tags))


class ProgressStore:
    """Atomic, local-only resume records for completed avatar operations."""

    def __init__(self, path=PROGRESS_FILE):
        self.path = Path(path)
        self.lock = RLock()
        self.data = {}
        try:
            if self.path.exists():
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    self.data = loaded
        except (OSError, ValueError, TypeError):
            self.data = {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(self.path.name + ".tmp")
        with temp.open("w", encoding="utf-8") as stream:
            json.dump(self.data, stream, indent=2)
        if os.name == "posix":
            os.chmod(temp, 0o600)
        temp.replace(self.path)

    def done(self, key, avatar_id):
        with self.lock:
            return avatar_id in self.data.get(key, [])

    def mark(self, key, avatar_id):
        with self.lock:
            ids = self.data.setdefault(key, [])
            if avatar_id not in ids:
                ids.append(avatar_id)
                self._save()

    def count(self, key):
        with self.lock:
            return len(self.data.get(key, []))

    def clear(self):
        with self.lock:
            self.data = {}
            self._save()


def create_session(username, password):
    config = vrchatapi.Configuration(username=username, password=password)
    # Never bypass TLS validation, especially for account credentials.
    config.verify_ssl = True
    # VRChat occasionally omits optional fields that the SDK validates strictly.
    config.client_side_validation = False
    vrchatapi.Configuration.set_default(config)
    client = vrchatapi.ApiClient(config)
    _configure_native_tls(client)
    client.user_agent = (
        "vrchat-avatar-tagger/2.0 "
        "(github.com/y2kbeatzz-dot/vrchat-avatar-tagger)"
    )
    jar = http.cookiejar.MozillaCookieJar(str(COOKIE_FILE))
    if COOKIE_FILE.exists():
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except (OSError, http.cookiejar.LoadError):
            pass
    client.rest_client.cookie_jar = jar

    def save():
        try:
            save_session_securely(jar, str(COOKIE_FILE))
        except OSError:
            pass

    atexit.register(save)
    return client, save


def authenticate(client, ask_for_code):
    """Authenticate, requesting a 2FA code through a GUI-safe callback."""
    auth = authentication_api.AuthenticationApi(client)
    try:
        user = auth.get_current_user()
    except UnauthorizedException as exc:
        if exc.status != 200:
            raise
        message = str(exc.reason).lower()
        mode = "email" if "email" in message else "totp"
        code = ask_for_code(mode)
        if not code:
            raise RuntimeError("Two-factor verification cancelled.")
        if mode == "email":
            auth.verify2_fa_email_code(TwoFactorEmailCode(code=code.strip()))
        else:
            auth.verify2_fa(TwoFactorAuthCode(code=code.strip()))
        user = auth.get_current_user()
    return user


def fetch_owned_avatars(api, stopped=lambda: False):
    avatars = []
    offset = 0
    page_size = 100
    while not stopped():
        page = api.search_avatars(user="me", n=page_size, offset=offset, release_status="all")
        if not page:
            break
        avatars.extend(page)
        if len(page) < page_size:
            break
        offset += len(page)
        time.sleep(REQUEST_DELAY)
    return avatars


def update_avatar_tags(api, avatar_id, tags):
    # Passing explicit None avoids the SDK mistakenly injecting asset versions.
    api.update_avatar(
        avatar_id,
        update_avatar_request=UpdateAvatarRequest(
            tags=sorted(tags), unity_version=None, version=None
        ),
    )
