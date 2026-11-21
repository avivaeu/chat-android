#!/usr/bin/env python3

# Copyright (c) 2026 Aviva
#
# SPDX-License-Identifier: AGPL-3.0-only
# Please see LICENSE files in the repository root for full details.

"""Preflight or publish a signed Aviva AAB to the Play Internal Testing track."""

from __future__ import annotations

import argparse
import http.client
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from android_distribution_common import (
    APPLICATION_ID,
    DistributionError,
    LEGACY_FIREBASE_PUSH_URL,
    current_firebase_push_url,
    validate_play_aab,
)


TRACK = "internal"


def adc_token() -> str:
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "application-default", "print-access-token"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise DistributionError("ADC unavailable; authenticate with the Android Publisher scope first") from error
    if not token:
        raise DistributionError("gcloud returned an empty ADC token")
    return token


def api_json(token: str, method: str, url: str, payload: dict | None = None) -> tuple[int, dict | str]:
    body = None if payload is None else json.dumps(payload).encode()
    headers = {"Authorization": f"Bearer {token}"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        body_text = error.read().decode("utf-8", "replace")
        try:
            return error.code, json.dumps(json.loads(body_text))
        except json.JSONDecodeError:
            return error.code, body_text
    except urllib.error.URLError as error:
        return 0, str(error)


def all_play_version_codes(tracks: dict) -> list[int]:
    result: list[int] = []
    for track in tracks.get("tracks", []):
        for release in track.get("releases", []):
            for raw_code in release.get("versionCodes", []):
                try:
                    result.append(int(raw_code))
                except (TypeError, ValueError):
                    continue
    return result


def upload_bundle(package: str, edit_id: str, bundle: Path, token: str) -> tuple[int, dict | str]:
    connection = http.client.HTTPSConnection("androidpublisher.googleapis.com", timeout=900)
    path = f"/upload/androidpublisher/v3/applications/{package}/edits/{edit_id}/bundles?uploadType=media"
    connection.putrequest("POST", path)
    connection.putheader("Authorization", f"Bearer {token}")
    connection.putheader("Content-Type", "application/octet-stream")
    connection.putheader("Content-Length", str(bundle.stat().st_size))
    connection.endheaders()
    try:
        with bundle.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                connection.send(chunk)
        response = connection.getresponse()
        raw = response.read()
        status = response.status
    except OSError as error:
        return 0, str(error)
    finally:
        connection.close()
    try:
        return status, json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return status, raw.decode("utf-8", "replace")


def delete_edit(base: str, edit_id: str, token: str) -> None:
    api_json(token, "DELETE", f"{base}/edits/{edit_id}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aab", required=True, type=Path, help="Aviva-upload-key-signed Gplay Release AAB")
    parser.add_argument("--release-name", required=True)
    parser.add_argument("--release-notes", help="Optional English release notes")
    parser.add_argument("--latest-firebase-version-code", type=int, help="Highest code already distributed through Firebase")
    parser.add_argument("--commit", action="store_true", help="Upload, validate, and commit to Internal Testing")
    parser.add_argument("--confirm-fcm-ready", action="store_true", help="Attest the new aviva-chat FCM route is live and tested")
    args = parser.parse_args()

    try:
        version_code, version_name = validate_play_aab(args.aab)
        gateway = current_firebase_push_url()
        if gateway == LEGACY_FIREBASE_PUSH_URL:
            raise DistributionError(
                "Android source still targets the legacy FCM/Sygnal route. Wait until server-bot confirms the "
                "new aviva-chat route, valid TLS, and dual-project rollout before publishing this migration build."
            )
        if args.latest_firebase_version_code is not None and version_code <= args.latest_firebase_version_code:
            raise DistributionError(
                f"AAB versionCode {version_code} must exceed the latest Firebase APK code "
                f"{args.latest_firebase_version_code} for an in-place Firebase-to-Play update."
            )
        if args.commit and not args.confirm_fcm_ready:
            raise DistributionError("Refusing to commit a Play release without --confirm-fcm-ready.")

        token = adc_token()
        base = f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{APPLICATION_ID}"
        status, edit = api_json(token, "POST", f"{base}/edits", {})
        if status != 200 or not isinstance(edit, dict) or not edit.get("id"):
            raise DistributionError(f"Play edit creation failed (HTTP {status}): {str(edit)[:1000]}")
        edit_id = edit["id"]
        edit_url = f"{base}/edits/{edit_id}"
        status, tracks = api_json(token, "GET", f"{edit_url}/tracks")
        if status != 200 or not isinstance(tracks, dict):
            delete_edit(base, edit_id, token)
            raise DistributionError(f"Play track query failed (HTTP {status}); temporary edit deleted: {str(tracks)[:1000]}")
        if not any(item.get("track") == TRACK for item in tracks.get("tracks", [])):
            available = ", ".join(sorted(item.get("track", "") for item in tracks.get("tracks", [])))
            delete_edit(base, edit_id, token)
            raise DistributionError(f"Track {TRACK!r} is unavailable; Play returned: {available}")
        highest = max(all_play_version_codes(tracks), default=0)
        if version_code <= highest:
            delete_edit(base, edit_id, token)
            raise DistributionError(
                f"AAB versionCode {version_code} must exceed the highest Play release code {highest}; "
                "temporary edit deleted."
            )

        print(f"Preflight OK: package={APPLICATION_ID}; versionName={version_name}; versionCode={version_code}; track={TRACK}")
        print(f"Highest current Play versionCode={highest}; AAB={args.aab.stat().st_size} bytes.")
        if not args.commit:
            delete_edit(base, edit_id, token)
            print("Dry run complete; temporary edit deleted and no Play bundle/track was changed.")
            return 0

        status, uploaded = upload_bundle(APPLICATION_ID, edit_id, args.aab, token)
        if status not in (200, 201) or not isinstance(uploaded, dict):
            delete_edit(base, edit_id, token)
            raise DistributionError(f"AAB upload failed (HTTP {status}); edit deleted: {str(uploaded)[:1000]}")
        if int(uploaded.get("versionCode", -1)) != version_code:
            delete_edit(base, edit_id, token)
            raise DistributionError("Play returned a different versionCode than the AAB; edit deleted.")

        release = {"name": args.release_name, "versionCodes": [str(version_code)], "status": "completed"}
        if args.release_notes:
            release["releaseNotes"] = [{"language": "en-US", "text": args.release_notes}]
        status, result = api_json(token, "PUT", f"{edit_url}/tracks/{TRACK}", {"track": TRACK, "releases": [release]})
        if status != 200:
            delete_edit(base, edit_id, token)
            raise DistributionError(f"Track update failed (HTTP {status}); edit deleted: {str(result)[:1000]}")
        status, result = api_json(token, "POST", f"{edit_url}:validate")
        if status != 200:
            delete_edit(base, edit_id, token)
            raise DistributionError(f"Play validation failed (HTTP {status}); edit deleted: {str(result)[:1000]}")
        status, result = api_json(token, "POST", f"{edit_url}:commit")
        if status != 200:
            raise DistributionError(f"Play commit failed (HTTP {status}); edit {edit_id} may remain uncommitted: {str(result)[:1000]}")
        print(f"Committed Play Internal release {args.release_name}; versionCode={version_code}; edit={edit_id}.")
        return 0
    except (DistributionError, OSError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
