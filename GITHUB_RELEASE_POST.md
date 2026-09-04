# VRChat Avatar Tagger v1.2

VRChat Avatar Tagger is a small desktop tool that lets avatar creators add or remove content-warning tags across their own avatars without editing every avatar individually on the VRChat website.

## Features

- Add or remove VRChat content-warning tags
- Select all avatars or only specific ones
- Search your avatar list
- Preview changes with Dry Run before applying them
- Edit one avatar directly by double-clicking it
- Resume an interrupted bulk update
- Supports email and authenticator 2FA
- Light and dark modes

## Fixes in v1.2

- Fixed silent failures while loading avatars
- Added a visible error message and `tagger_error.log`
- Improved the Windows launcher so setup errors stay visible
- Added a private Python environment to prevent package conflicts
- Pinned the tested `vrchatapi` version
- Added the missing `.gitignore` for session and progress files
- Updated the API User-Agent project address
- Prevented oversized or incorrect banner images from covering the login form

## Windows setup

1. Download and extract the ZIP.
2. Install Python 3 from python.org and enable **Add python.exe to PATH**.
3. Double-click `run_gui.bat`.
4. Log in, choose avatars and tags, and use **Dry Run** first.

This project uses the unofficial community `vrchatapi` package and is not affiliated with or endorsed by VRChat Inc. Your login is sent only to VRChat for authentication. Never upload or share `vrchat_session.cookies`.
