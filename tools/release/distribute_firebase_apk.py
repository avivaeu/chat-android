#!/usr/bin/env python3

# Copyright (c) 2026 Aviva
#
# SPDX-License-Identifier: AGPL-3.0-only
# Please see LICENSE files in the repository root for full details.

"""Preflight or publish a Play-signed Release APK through Firebase App Distribution."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from android_distribution_common import (
    FIREBASE_PROJECT_ID,
    FIREBASE_RELEASE_APP_ID,
    LEGACY_FIREBASE_PUSH_URL,
    DistributionError,
    current_firebase_push_url,
    file_sha256,
    validate_firebase_apk,
)


def firebase_groups() -> list[dict]:
    result = subprocess.run(
        ["firebase", "--json", "appdistribution:groups:list", "--project", FIREBASE_PROJECT_ID],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise DistributionError("Firebase CLI could not list App Distribution groups; check onboarding and IAM.")
    json_start = result.stdout.find("{")
    if json_start < 0:
        raise DistributionError("Firebase CLI returned no JSON while listing App Distribution groups.")
    try:
        return json.loads(result.stdout[json_start:]).get("result", {}).get("groups", [])
    except json.JSONDecodeError as error:
        raise DistributionError(f"Firebase CLI returned malformed group JSON: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", required=True, type=Path, help="Play-generated universal APK for the Release app")
    parser.add_argument("--groups", required=True, help="Firebase tester group alias")
    parser.add_argument("--release-notes-file", required=True, type=Path)
    parser.add_argument("--next-play-version-code", type=int, help="Optional planned higher Play code for a migration update test")
    parser.add_argument("--publish", action="store_true", help="Upload to Firebase; omission is a dry run")
    parser.add_argument("--confirm-fcm-ready", action="store_true", help="Confirm server FCM for aviva-chat is deployed and tested")
    parser.add_argument("--confirm-contact-email", action="store_true", help="Confirm Firebase contact email verification is complete")
    args = parser.parse_args()

    try:
        version_code, version_name = validate_firebase_apk(args.apk)
        if not args.release_notes_file.is_file():
            raise DistributionError(f"Release notes file not found: {args.release_notes_file}")
        if args.next_play_version_code is not None and args.next_play_version_code <= version_code:
            raise DistributionError("For a migration update, the next Play versionCode must exceed this APK's code.")

        groups = firebase_groups()
        group = next((item for item in groups if item.get("name", "").endswith(f"/groups/{args.groups}")), None)
        if group is None:
            aliases = ", ".join(item.get("name", "").rsplit("/", 1)[-1] for item in groups)
            raise DistributionError(f"Group {args.groups!r} is not in {FIREBASE_PROJECT_ID}; available: {aliases or 'none'}")
        if int(group.get("inviteLinkCount", 0)) < 1:
            raise DistributionError(f"Group {args.groups!r} has no self-enrollment invite link.")

        push_url = current_firebase_push_url()
        if push_url == LEGACY_FIREBASE_PUSH_URL:
            raise DistributionError(
                "The app still targets the legacy Sygnal route. Wait for the new aviva-chat FCM route, valid TLS, "
                "and server-side dual-project migration before distributing."
            )
        print(f"Preflight OK: package=org.avivaeu.chat versionName={version_name} versionCode={version_code}")
        print(f"Firebase project={FIREBASE_PROJECT_ID}; appId={FIREBASE_RELEASE_APP_ID}; group={args.groups}")
        print(f"Play signer verified; APK SHA-256={file_sha256(args.apk)}")
        if not args.publish:
            print("Dry run only; no Firebase release was uploaded.")
            return 0
        if not args.confirm_fcm_ready:
            raise DistributionError("Refusing upload without --confirm-fcm-ready after server FCM validation.")
        if not args.confirm_contact_email:
            raise DistributionError("Refusing upload without --confirm-contact-email after contact email verification.")
        command = [
            "firebase",
            "appdistribution:distribute",
            str(args.apk),
            "--project",
            FIREBASE_PROJECT_ID,
            "--app",
            FIREBASE_RELEASE_APP_ID,
            "--groups",
            args.groups,
            "--release-notes-file",
            str(args.release_notes_file),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            # CLI output can contain a short-lived signed download URL; don't echo it.
            raise DistributionError(f"Firebase CLI distribution failed (exit {result.returncode}); inspect its local output securely.")
        print("Firebase App Distribution release uploaded successfully to the selected group.")
        return 0
    except (DistributionError, OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
