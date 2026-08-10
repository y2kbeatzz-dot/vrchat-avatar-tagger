#!/usr/bin/env python3
"""
Bulk-apply VRChat Content Warning tags to all of your own avatars.

Requires: pip install vrchatapi --break-system-packages

This uses VRChat's unofficial-but-community-documented API (vrchatapi).
It logs in as you, fetches every avatar you own, and adds the selected
Content Warning tag(s) to each one -- without touching any other tags
(like your custom search tags) that are already on the avatar.

USAGE:
  python3 tag_avatars.py --tags sex                        # preview nothing changed yet? no, this applies for real
  python3 tag_avatars.py --tags sex --dry-run               # preview only, changes nothing
  python3 tag_avatars.py --tags sex,violence,gore            # multiple tags at once
  python3 tag_avatars.py --list-tags                         # show valid tag names and exit

VALID TAG NAMES (see --list-tags): sex, adult, violence, gore, horror

IMPORTANT NOTES BEFORE YOU RUN THIS:
  - Your login/password are only used locally to authenticate with VRChat's
    servers, exactly like the website login does. Nothing is sent anywhere
    else. Credentials are entered at runtime via getpass, never hardcoded.
  - VRChat rate-limits and can flag accounts for unusually fast automated
    activity. This script sleeps briefly between requests -- don't lower
    REQUEST_DELAY below ~1 second.
  - Always run with --dry-run first to see exactly what would change
    before it changes anything for real.
  - This script only ADDS the tags you specify; it never removes existing
    tags (content warning or otherwise) from an avatar.
"""

import argparse
import atexit
import getpass
import http.cookiejar
import os
import sys
import time

import vrchatapi
from vrchatapi.api import authentication_api, avatars_api
from vrchatapi.exceptions import UnauthorizedException
from vrchatapi.models.two_factor_auth_code import TwoFactorAuthCode
from vrchatapi.models.two_factor_email_code import TwoFactorEmailCode
from vrchatapi.models.update_avatar_request import UpdateAvatarRequest

COOKIE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vrchat_session.cookies")

# Friendly name -> official VRChat content tag string (VRChat's Content
# Warning system, see https://hello.vrchat.com/creator-guidelines)
CONTENT_TAGS = {
    "sex": "content_sex",           # Sexually Suggestive
    "adult": "content_adult",       # Adult Language and Themes
    "violence": "content_violence", # Graphic Violence
    "gore": "content_gore",         # Excessive Gore
    "horror": "content_horror",     # Extreme Horror
}

REQUEST_DELAY = 1.2  # seconds between API calls, be polite to VRChat's API


def parse_args():
    parser = argparse.ArgumentParser(
        description="Bulk-apply VRChat Content Warning tags to all of your own avatars."
    )
    parser.add_argument(
        "--tags",
        help=f"Comma-separated list of tags to apply. Valid names: {', '.join(CONTENT_TAGS)}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would change without actually updating anything.",
    )
    parser.add_argument(
        "--list-tags",
        action="store_true",
        help="Print the valid tag names and exit.",
    )
    args = parser.parse_args()

    if args.list_tags:
        for name, api_value in CONTENT_TAGS.items():
            print(f"  {name:10s} -> {api_value}")
        sys.exit(0)

    if not args.tags:
        parser.error("--tags is required (or use --list-tags to see options)")

    names = [t.strip() for t in args.tags.split(",") if t.strip()]
    unknown = [n for n in names if n not in CONTENT_TAGS]
    if unknown:
        parser.error(
            f"Unknown tag name(s): {', '.join(unknown)}. "
            f"Valid names: {', '.join(CONTENT_TAGS)}"
        )

    return [CONTENT_TAGS[n] for n in names], args.dry_run


def login():
    configuration = vrchatapi.Configuration(
        username=input("VRChat username: ").strip(),
        password=getpass.getpass("VRChat password: "),
    )

    # The vrchatapi library aggressively validates that fields aren't None,
    # but VRChat's real API frequently omits fields (e.g. an avatar with no
    # image) which otherwise crashes the library entirely. This must be set
    # as the *global default* config, since deserialized models pull from
    # there rather than the instance we pass to ApiClient.
    configuration.client_side_validation = False
    vrchatapi.Configuration.set_default(configuration)

    api_client = vrchatapi.ApiClient(configuration)
    api_client.user_agent = "vrchat-avatar-tagger/1.0 (github.com/USERNAME/vrchat-avatar-tagger)"

    # Persist the login session (auth + 2FA cookies) to disk. VRChat only
    # allows a limited number of simultaneous username/password logins
    # ("sessions") -- reusing a saved session on re-runs avoids burning
    # through that limit and getting temporarily rate-limited.
    cookie_jar = http.cookiejar.MozillaCookieJar(COOKIE_FILE)
    if os.path.exists(COOKIE_FILE):
        try:
            cookie_jar.load(ignore_discard=True, ignore_expires=True)
            print("Reusing saved VRChat session.")
        except Exception:
            pass
    api_client.rest_client.cookie_jar = cookie_jar

    def save_session():
        try:
            cookie_jar.save(ignore_discard=True, ignore_expires=True)
        except Exception:
            pass

    atexit.register(save_session)

    auth_api = authentication_api.AuthenticationApi(api_client)

    try:
        # NOTE: when 2FA is required, VRChat's server sends back HTTP 200
        # with a body like {"requiresTwoFactorAuth": ["emailOtp"]}. The
        # vrchatapi library detects this and raises UnauthorizedException
        # with status=200 and a reason describing which 2FA type is needed
        # -- that's a normal step, not a real login failure. Only a
        # non-200 status here means the login itself actually failed.
        current_user = auth_api.get_current_user()
    except UnauthorizedException as e:
        if e.status == 200:
            if "Email" in str(e.reason):
                code = input("Email 2FA code (check your inbox): ").strip()
                auth_api.verify2_fa_email_code(TwoFactorEmailCode(code=code))
            else:
                code = input("Authenticator (TOTP) 2FA code: ").strip()
                auth_api.verify2_fa(TwoFactorAuthCode(code=code))
            current_user = auth_api.get_current_user()
        else:
            print("Login failed. VRChat's server said:")
            print(f"  status: {e.status}")
            print(f"  reason: {e.reason}")
            print(f"  body:   {e.body}")
            print()
            print("If the body mentions 'ratelimit' or similar, VRChat has")
            print("temporarily blocked new logins -- wait a while and retry.")
            print("If it mentions invalid credentials, double check them.")
            sys.exit(1)

    save_session()
    print(f"Logged in as {current_user.display_name}\n")
    return api_client


def fetch_all_own_avatars(avatar_api):
    all_avatars = []
    offset = 0
    page_size = 100
    while True:
        page = avatar_api.search_avatars(
            user="me",
            n=page_size,
            offset=offset,
            release_status="all",
        )
        if not page:
            break
        all_avatars.extend(page)
        offset += page_size
        time.sleep(REQUEST_DELAY)
    return all_avatars


def main():
    tags_to_apply, dry_run = parse_args()

    api_client = login()
    avatar_api = avatars_api.AvatarsApi(api_client)

    all_avatars = fetch_all_own_avatars(avatar_api)
    print(f"Found {len(all_avatars)} avatars.\n")

    updated, skipped, failed = 0, 0, 0

    for i, avatar in enumerate(all_avatars, 1):
        existing_tags = set(avatar.tags or [])
        new_tags = existing_tags | set(tags_to_apply)

        if new_tags == existing_tags:
            print(f"[{i}/{len(all_avatars)}] {avatar.name} -- already tagged, skipping")
            skipped += 1
            continue

        print(f"[{i}/{len(all_avatars)}] {avatar.name} -- adding {tags_to_apply}")

        if dry_run:
            updated += 1
            continue

        try:
            avatar_api.update_avatar(
                avatar.id,
                update_avatar_request=UpdateAvatarRequest(
                    tags=list(new_tags),
                    unity_version=None,  # library defaults this to '5.3.4p1' unless
                    version=None,        # overridden, which makes VRChat's API think
                                          # we're trying to update the avatar's asset
                                          # files and reject the request.
                ),
            )
            updated += 1
        except Exception as e:
            print(f"    FAILED: {e}")
            failed += 1

        time.sleep(REQUEST_DELAY)

    print(f"\nDone. Updated: {updated}, already tagged: {skipped}, failed: {failed}")
    if dry_run:
        print("(This was a --dry-run, nothing was actually changed.)")


if __name__ == "__main__":
    main()
