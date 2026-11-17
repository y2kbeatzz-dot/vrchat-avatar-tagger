# VRChat Avatar Tagger v1.5.5 — Fix macOS crash and slow avatar loading

## Crash fix
- Prevent macOS Qt from aborting while an active avatar-fetching QThread is destroyed.
- Closing the app now requests cooperative cancellation and finishes the current API call before the window exits.
- Background requests use a bounded timeout, so cancellation doesn't wait on a hung request indefinitely.
- Unexpected Qt callback errors are written to the local app log rather than terminating Python with a live background worker.

## Faster avatar library
- **Fixed a 60-second delay after each page of 100 avatars.** Read-only avatar listing now uses a short 1-second pause between pages, separate from the intentionally cautious bulk-write delay.
- First 100 avatars appear as soon as they're fetched. More avatars stream into the library, with live counts.
- Fewer full-table redraws reduce jank when large collections are loaded.
- A refresh cannot launch overlapping avatar fetch requests.

## Testing
- Added regression tests for pagination speed, incremental batches, cancellation, and closing the app while a worker is active.
- Existing certificate validation and confirmed Apply/Preview functionality remain unchanged.
- Automated tests do not log into or modify a real VRChat account.

**Install:** Quit the old app, download the new DMG, drag the application into Applications and choose Replace.

Mac Apple Silicon, Mac Intel and Windows downloads: https://github.com/y2kbeatzz-dot/vrchat-avatar-tagger/releases/latest

Created by **Ksyusha (Ксюша)** · https://guns.lol/life999

Unofficial community project not affiliated with VRChat.
