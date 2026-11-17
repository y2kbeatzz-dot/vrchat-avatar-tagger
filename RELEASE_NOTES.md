# VRChat Avatar Tagger v1.5.0 — New UI + Custom Installers

## Creator & project story
- New About the Creator screen, introducing **Ksyusha (Ксюша)** and the project's purpose, tools, and development approach.
- The README and website now include an About section and a direct link to the creator's [profiles](https://guns.lol/life999).
- The Windows installer identifies Ksyusha as the app publisher.

## Redesigned desktop app
- Rebuilt the desktop interface with **Qt/PySide6** for a modern macOS and Windows experience.
- Sidebar navigation for Avatars, Activity, and About.
- Dark/light themes, dashboard statistics, search/filter by avatar name or tags.
- Tag Studio with warning tags, custom tags, add/remove, previews, optional resume and update limit.
- Multi-avatar selection, per-avatar tag editor, running progress, cancellation and activity log.
- VRChat sign-in and email/authenticator 2FA retained; all network work occurs off the UI thread.

## Custom installer experience
- **Mac Apple Silicon**: branded drag-to-Applications DMG with a custom background and icon.
- **Mac Intel**: the same custom DMG experience.
- **Windows**: custom branded Setup EXE with installer graphics, install location, Start Menu shortcut, optional desktop shortcut, launch after install and uninstall.
- **Windows portable**: ZIP remains available for users who do not want to install.

## Download
Official website: https://y2kbeatzz-dot.github.io/vrchat-avatar-tagger/
GitHub Releases: https://github.com/y2kbeatzz-dot/vrchat-avatar-tagger/releases/latest

**Privacy:** local cookies and operation records remain on your computer. This is an unofficial community project not affiliated with VRChat.

**macOS note:** the community DMGs are not Apple-signed or notarized and may be blocked by Gatekeeper. Use System Settings → Privacy & Security → Open Anyway only after verifying you trust the build.
