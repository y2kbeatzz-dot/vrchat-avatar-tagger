# VRChat Avatar Tagger v1.5.3 — Secure macOS connection fix

## Fixed
- **macOS VRChat sign-in SSL certificate errors:** the desktop app now verifies the API's HTTPS certificates against the trusted certificates in your Mac's system Keychain via `truststore`, rather than relying solely on packaged Python/OpenSSL CA roots.
- Windows also uses the native trusted certificate store, while Linux continues with its existing trusted OpenSSL system roots.
- Certificate verification **remains enabled** with full hostname checks; no `verify=False`, no ignored SSL warnings, and no automatic installation of trust roots.
- Clear, friendly guidance when a VPN, HTTPS-filtering proxy, school/work network, or untrusted root certificate blocks the secure connection.
- Builds bundle the native TLS trust library in both Mac DMG packages and Windows installer/ZIP.

## Install
- On **Mac Apple Silicon or Intel**, download the matching DMG, drag the app to Applications, and reopen the new copy (quit the previous app first).
- On **Windows**, use the branded Setup EXE or portable ZIP.
- Downloads: https://github.com/y2kbeatzz-dot/vrchat-avatar-tagger/releases/latest

## If certificate verification still fails
The server's presented certificate chain may be untrusted *by macOS itself* (e.g., HTTPS interception). Test on a trusted network, check the system date/time, inspect security/VPN software, and ask the administrator of a managed network for help. **Do not bypass certificate verification or install unknown certificates.**

Created by **Ksyusha (Ксюша)** · https://guns.lol/life999

*Unofficial community project, not affiliated with VRChat.*
