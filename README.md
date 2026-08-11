<img width="300" height="60" alt="gemini-svg" src="https://github.com/user-attachments/assets/10aade69-151e-44f1-b141-9b0d2f7a0c25" />


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
