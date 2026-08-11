<img width="300" height="60" alt="gemini-svg" src="https://github.com/user-attachments/assets/10aade69-151e-44f1-b141-9b0d2f7a0c25" />![Uploading <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1500 300" width="100%" height="100%">
  <defs>
    <!-- Background Gradient -->
    <radialGradient id="bgGrad" cx="50%" cy="50%" r="75%">
      <stop offset="0%" stop-color="#1e1e24" />
      <stop offset="100%" stop-color="#0a0a0c" />
    </radialGradient>

    <!-- Main Title Gradient -->
    <linearGradient id="titleGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#FFDD00" />
      <stop offset="100%" stop-color="#FF5500" />
    </linearGradient>

    <!-- Badge/Icon Gradient -->
    <linearGradient id="tagGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FF5500" />
      <stop offset="100%" stop-color="#C41230" />
    </linearGradient>

    <!-- Glow Effect -->
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="6" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>

    <!-- Shadow Effect -->
    <filter id="dropShadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.6" />
    </filter>
  </defs>

  <!-- Dark Background Canvas -->
  <rect width="1500" height="300" fill="url(#bgGrad)" />

  <!-- Abstract Background Elements (Simulating VRChat World Vibe) -->
  <circle cx="150" cy="150" r="180" fill="#FF5500" opacity="0.05" filter="url(#glow)" />
  <circle cx="1350" cy="100" r="220" fill="#FFDD00" opacity="0.03" filter="url(#glow)" />

  <!-- Left Icon / Tag Symbol -->
  <g transform="translate(90, 85)" filter="url(#dropShadow)">
    <circle cx="65" cy="65" r="55" fill="none" stroke="url(#tagGrad)" stroke-width="12" />
    <path d="M 45 45 L 75 45 L 85 55 L 85 85 L 55 85 Z" fill="none" stroke="#FFDD00" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="58" cy="58" r="4" fill="#FFDD00" />
  </g>

  <!-- "Tagging Tool / Utility" Eyebrow Text -->
  <text x="260" y="105" 
        fill="#FF8800" 
        font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" 
        font-size="28" 
        font-weight="800" 
        letter-spacing="1">
    VRChat Avatar Tooling
  </text>

  <!-- Main Title: VRChat Avatar Tagger -->
  <text x="255" y="195" 
        fill="url(#titleGrad)" 
        font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" 
        font-size="88" 
        font-weight="900" 
        letter-spacing="-1"
        filter="url(#dropShadow)">
    VRChat Avatar Tagger
  </text>

  <!-- Subtitle Text -->
  <text x="750" y="255" 
        text-anchor="middle"
        fill="#FFFFFF" 
        font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif" 
        font-size="30" 
        font-weight="600" 
        opacity="0.9"
        letter-spacing="0.5">
    Automated Tagging &amp; Categorization Manager for VRChat Avatars
  </text>
</svg>
gemini-svg.svg…]()


# vrchat-avatar-tagger
Bulk-apply VRChat Content Warning tags to all your avatars at once from the command line.
[README.md](https://github.com/user-attachments/files/30912286/README.md)
# vrchat-avatar-tagger

A small command-line tool to bulk-apply [VRChat Content Warning tags](https://hello.vrchat.com/creator-guidelines) (Sexually Suggestive, Adult Language and Themes, Graphic Violence, Excessive Gore, Extreme Horror) to **all of your own avatars** at once, instead of clicking through each one individually on the VRChat website.

Useful if you have a large number of avatars and need to get them properly labeled to comply with VRChat's Creator Guidelines and upcoming Content Gating / Age Verification enforcement.

## What it does

- Logs into your VRChat account (supports email and authenticator 2FA)
- Fetches every avatar you own
- Adds the content warning tag(s) you choose to each avatar that doesn't already have them
- **Never removes** any existing tags, content-warning or otherwise

## Install

```bash
pip install vrchatapi --break-system-packages
```

(or `pip install -r requirements.txt`)

## Usage

Always preview first with `--dry-run` — it prints exactly what would change without touching your account:

```bash
python3 tag_avatars.py --tags sex --dry-run
```

If that looks right, run it for real:

```bash
python3 tag_avatars.py --tags sex
```

Apply multiple tags at once:

```bash
python3 tag_avatars.py --tags sex,violence,gore
```

See all valid tag names:

```bash
python3 tag_avatars.py --list-tags
```

| Name       | VRChat label                  |
|------------|--------------------------------|
| `sex`      | Sexually Suggestive             |
| `adult`    | Adult Language and Themes       |
| `violence` | Graphic Violence                |
| `gore`     | Excessive Gore                  |
| `horror`   | Extreme Horror                  |

## Notes

- Your username/password are only used locally to log into VRChat's own servers, exactly like the website login. They're entered at runtime (never hardcoded) and nothing is sent anywhere besides VRChat's API.
- After a successful login, the tool saves a session file (`vrchat_session.cookies`) next to the script so re-running it doesn't need a fresh login every time. **Don't share or commit this file** — it's as sensitive as being logged in. It's already excluded via `.gitignore`.
- VRChat limits how many login sessions and requests you can make in a short window. The script pauses briefly between requests; don't remove that.
- This uses [`vrchatapi`](https://github.com/vrchatapi/vrchatapi-python), an unofficial but actively maintained community wrapper around VRChat's API. It isn't officially supported by VRChat.

## License

MIT — see [LICENSE](LICENSE).
