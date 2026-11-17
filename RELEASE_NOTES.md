# VRChat Avatar Tagger v1.5.4 — Reliable Apply + UI Fixes

## Tag updates that actually save
- Separate **Preview changes (no upload)** and **Apply tags to VRChat** buttons. Applying requires confirmation.
- Bulk and individual tag edits use VRChat's update-avatar endpoint.
- A save is counted as successful only when the API's returned Avatar confirms the requested tags; mismatched, missing, or rejected responses are reported as failures rather than successes.
- Resume history cannot silently skip an avatar if its tags currently differ.
- Custom tags are normalized to the `author_tag_` namespace. Warning tags use their own checkboxes.
- Completion dialogs distinguish preview-only plans from confirmed VRChat updates.
- Bulk writes are deliberately paced to follow the unofficial API rate guidance.

## Improved desktop layout
- Drag-to-resize Avatar Library and Tag Studio panels.
- More compact, laptop-friendly margins, stat cards and sidebar.
- No content warning selected by default: choose the labels appropriate to your avatars.
- Custom Mac drag-to-Applications DMGs and Windows setup wizard remain available.

## Testing
Mocked offline tests cover actual writes, preview-only behavior, API tag mismatch, interrupted resumes, custom tags, and single-avatar edits. No live VRChat account was accessed during automated tests.

Download: https://github.com/y2kbeatzz-dot/vrchat-avatar-tagger/releases/latest

Created by **Ksyusha (Ксюша)** · https://guns.lol/life999

VRChat Avatar Tagger is an unofficial community project; VRChat's API can change without notice.
