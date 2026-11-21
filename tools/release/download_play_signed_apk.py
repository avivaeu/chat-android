#!/usr/bin/env python3

# Copyright (c) 2026 Aviva
#
# SPDX-License-Identifier: AGPL-3.0-only
# Please see LICENSE files in the repository root for full details.

"""Fetch and validate Play's generated universal APK for a published AAB."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from android_distribution_common import (
    APPLICATION_ID,
    PLAY_APP_SIGNING_CERT_SHA256,
    DistributionError,
    file_sha256,
    validate_firebase_apk,
)


def adc_token() -> str:
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "application-default", "print-access-token"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise DistributionError("ADC unavailable; authenticate with Android Publisher scope first") from error
    if not token:
        raise DistributionError("gcloud returned an empty ADC token")
    return token


def get_json(url: str, token: str) -> dict:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise DistributionError(f"Android Publisher API returned HTTP {error.code}: {detail[:800]}") from error
    except (urllib.error.URLError, json.JSONDecodeError) as error:
        raise DistributionError(f"Android Publisher API request failed: {error}") from error


def universal_download_id(listing: dict) -> str:
    expected = PLAY_APP_SIGNING_CERT_SHA256.replace(":", "").upper()
    signing_keys = []
    for entry in listing.get("generatedApks", []):
        fingerprint = entry.get("certificateSha256Hash", "").replace(":", "").upper()
        signing_keys.append(fingerprint or "(missing SHA-256)")
        universal = entry.get("generatedUniversalApk", {})
        if fingerprint == expected and universal.get("downloadId"):
            return universal["downloadId"]
    raise DistributionError(
        "Play did not return a universal APK for the expected App Signing certificate "
        f"{PLAY_APP_SIGNING_CERT_SHA256}. Signing groups returned: {', '.join(signing_keys) if signing_keys else 'none'}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version-code", required=True, type=int, help="Version code of the AAB processed by Play")
    parser.add_argument("--output", type=Path, help="Output path; defaults under app/build/outputs/firebase")
    parser.add_argument("--dry-run", action="store_true", help="Check Play metadata but do not download an APK")
    parser.add_argument("--overwrite", action="store_true", help="Replace an existing output file")
    args = parser.parse_args()

    try:
        base = (
            f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
            f"{APPLICATION_ID}/generatedApks/{args.version_code}"
        )
        token = adc_token()
        listing = get_json(base, token)
        download_id = universal_download_id(listing)
        if args.dry_run:
            print(
                f"Play has a universal APK for {APPLICATION_ID} versionCode {args.version_code}, "
                f"signed with {PLAY_APP_SIGNING_CERT_SHA256}. No download performed."
            )
            return 0

        output = args.output or Path("app/build/outputs/firebase") / f"aviva-chat-play-signed-{args.version_code}.apk"
        output = output.resolve()
        if output.exists() and not args.overwrite:
            raise DistributionError(f"Output already exists; pass --overwrite to replace: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)

        download_url = base + f"/downloads/{urllib.parse.quote(download_id, safe='')}:download?alt=media"
        request = urllib.request.Request(download_url, headers={"Authorization": f"Bearer {token}"})
        with tempfile.NamedTemporaryFile(prefix=f".{output.name}.", suffix=".tmp", dir=output.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    shutil.copyfileobj(response, temporary)
                with temporary_path.open("rb") as downloaded:
                    if downloaded.read(4) != b"PK\x03\x04":
                        raise DistributionError("Play generated-APK download did not return an APK/ZIP")
                version_code, version_name = validate_firebase_apk(
                    temporary_path,
                    expected_version_code=args.version_code,
                )
                digest = file_sha256(temporary_path)
                temporary_path.replace(output)
            except Exception:
                temporary_path.unlink(missing_ok=True)
                raise

        print(f"Saved Play-signed APK: {output}")
        print(f"package={APPLICATION_ID}; versionName={version_name}; versionCode={version_code}")
        print(f"certificateSha256={PLAY_APP_SIGNING_CERT_SHA256}; sha256={digest}")
        return 0
    except (DistributionError, OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
