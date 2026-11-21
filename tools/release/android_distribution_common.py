#!/usr/bin/env python3

# Copyright (c) 2026 Aviva
#
# SPDX-License-Identifier: AGPL-3.0-only
# Please see LICENSE files in the repository root for full details.

"""Shared metadata and signing checks for the Aviva Android distribution scripts."""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
APPLICATION_ID = "org.avivaeu.chat"
FIREBASE_PROJECT_ID = "aviva-chat"
FIREBASE_RELEASE_APP_ID = "1:60506354350:android:ac82f5fdf4785d6f24b33f"
FIREBASE_RELEASE_GOOGLE_APP_ID = FIREBASE_RELEASE_APP_ID
PLAY_APP_SIGNING_CERT_SHA256 = "89F8768F1C61BD1129C0146AB6D55275048B267E09EED72176A0505A35A218AC"
AVIVA_UPLOAD_CERT_SHA256 = "B92EBCEAA8F9740454D7779D97094C9247C8B59716A04AC990E863D4FD954B7B"
LEGACY_FIREBASE_PUSH_URL = "https://push.chat.avivaeu.org/_matrix/push/v1/notify"
ANDROID_NAMESPACE = "{http://schemas.android.com/apk/res/android}"


class DistributionError(RuntimeError):
    """Raised when a distribution artifact or destination fails preflight."""


def android_environment() -> dict[str, str]:
    env = os.environ.copy()
    java_home = env.get("JAVA_HOME") or "/Applications/Android Studio.app/Contents/jbr/Contents/Home"
    env["JAVA_HOME"] = java_home
    env["PATH"] = f"{java_home}/bin:{env.get('PATH', '')}"
    return env


def android_sdk_root() -> Path:
    for variable in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
        value = os.environ.get(variable)
        if value:
            return Path(value).expanduser()

    local_properties = REPOSITORY_ROOT / "local.properties"
    if local_properties.is_file():
        for line in local_properties.read_text().splitlines():
            if line.startswith("sdk.dir="):
                return Path(line.partition("=")[2].replace("\\:", ":")).expanduser()
    raise DistributionError("Android SDK path was not found in environment or local.properties")


def android_build_tools() -> Path:
    root = android_sdk_root() / "build-tools"
    if not root.is_dir():
        raise DistributionError(f"Android build-tools directory not found: {root}")

    def version_key(path: Path) -> tuple[int, ...]:
        return tuple(int(part) if part.isdigit() else 0 for part in path.name.split("."))

    versions = sorted((path for path in root.iterdir() if path.is_dir()), key=version_key)
    if not versions:
        raise DistributionError(f"No Android build-tools versions found under {root}")
    return versions[-1]


def tool_path(name: str) -> str:
    configured = os.environ.get(name.upper().replace("-", "_"))
    if configured:
        return configured
    candidate = android_build_tools() / name
    if candidate.is_file():
        return str(candidate)
    raise DistributionError(f"Android tool not found: {candidate}")


def run_tool(arguments: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        arguments,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=android_environment(),
    )
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise DistributionError(f"Command failed ({result.returncode}): {arguments[0]}: {detail[-1200:]}")
    return result


def normalize_fingerprint(value: str) -> str:
    return "".join(character for character in value.upper() if character in "0123456789ABCDEF")


def apk_manifest(apk: Path) -> tuple[str, int, str]:
    result = run_tool([tool_path("aapt"), "dump", "badging", str(apk)])
    match = re.search(
        r"(?m)^package: name='([^']+)' versionCode='([0-9]+)' versionName='([^']*)'",
        result.stdout,
    )
    if not match:
        raise DistributionError(f"Could not read APK package/version metadata: {apk}")
    return match.group(1), int(match.group(2)), match.group(3)


def apk_firebase_app_id(apk: Path) -> str:
    result = run_tool([tool_path("aapt"), "dump", "--values", "resources", str(apk)])
    lines = result.stdout.splitlines()
    for index, line in enumerate(lines):
        if "resource " not in line or "spec resource" in line or ":string/google_app_id:" not in line:
            continue
        for value_line in lines[index + 1 : index + 4]:
            match = re.search(r'\(string8\)\s+"([^"]+)"', value_line)
            if match:
                return match.group(1)
    raise DistributionError("APK has no compiled google_app_id string resource")


def apk_signer_fingerprints(apk: Path) -> set[str]:
    result = run_tool([tool_path("apksigner"), "verify", "--print-certs", str(apk)])
    fingerprints = set(
        normalize_fingerprint(value)
        for value in re.findall(r"certificate SHA-256 digest:\s*([0-9A-Fa-f:]+)", result.stdout)
    )
    if not fingerprints:
        raise DistributionError(f"No APK signer SHA-256 fingerprint was reported: {apk}")
    return fingerprints


def validate_firebase_apk(
    apk: Path,
    *,
    expected_version_code: int | None = None,
    expected_google_app_id: str = FIREBASE_RELEASE_GOOGLE_APP_ID,
) -> tuple[int, str]:
    if not apk.is_file():
        raise DistributionError(f"APK not found: {apk}")
    package, version_code, version_name = apk_manifest(apk)
    if package != APPLICATION_ID:
        raise DistributionError(f"APK applicationId is {package}, expected {APPLICATION_ID}")
    if expected_version_code is not None and version_code != expected_version_code:
        raise DistributionError(f"APK versionCode {version_code} does not match expected {expected_version_code}")
    google_app_id = apk_firebase_app_id(apk)
    if google_app_id != expected_google_app_id:
        raise DistributionError(
            f"APK Firebase app ID {google_app_id} is not the destination Release app ID {expected_google_app_id}"
        )
    signers = apk_signer_fingerprints(apk)
    expected_signer = normalize_fingerprint(PLAY_APP_SIGNING_CERT_SHA256)
    if expected_signer not in signers:
        raise DistributionError(
            "APK is not signed with the current Play App Signing certificate "
            f"({PLAY_APP_SIGNING_CERT_SHA256}); observed: {', '.join(sorted(signers))}"
        )
    return version_code, version_name


def aab_manifest(bundle: Path) -> tuple[str, int, str]:
    if not bundle.is_file():
        raise DistributionError(f"AAB not found: {bundle}")
    run_tool(["bundletool", "validate", f"--bundle={bundle}"])
    dumped = run_tool(["bundletool", "dump", "manifest", f"--bundle={bundle}", "--module=base"])
    try:
        manifest = ET.fromstring(dumped.stdout)
    except ET.ParseError as error:
        raise DistributionError(f"Could not parse AAB base manifest: {error}") from error
    package = manifest.attrib.get("package", "")
    version_code = manifest.attrib.get(ANDROID_NAMESPACE + "versionCode")
    version_name = manifest.attrib.get(ANDROID_NAMESPACE + "versionName", "")
    if not package or not version_code:
        raise DistributionError("AAB base manifest is missing package or versionCode")
    return package, int(version_code), version_name


def aab_signer_fingerprints(bundle: Path) -> set[str]:
    result = run_tool(["keytool", "-printcert", "-jarfile", str(bundle)])
    fingerprints = set(
        normalize_fingerprint(value)
        for value in re.findall(r"(?m)^\s*SHA256:\s*([0-9A-Fa-f:]+)\s*$", result.stdout)
    )
    if not fingerprints:
        raise DistributionError(f"No AAB signer SHA-256 fingerprint was reported: {bundle}")
    return fingerprints


def validate_play_aab(bundle: Path) -> tuple[int, str]:
    package, version_code, version_name = aab_manifest(bundle)
    if package != APPLICATION_ID:
        raise DistributionError(f"AAB applicationId is {package}, expected {APPLICATION_ID}")
    signers = aab_signer_fingerprints(bundle)
    if normalize_fingerprint(AVIVA_UPLOAD_CERT_SHA256) not in signers:
        raise DistributionError(
            "AAB is not signed with the configured Aviva upload certificate "
            f"({AVIVA_UPLOAD_CERT_SHA256}); observed: {', '.join(sorted(signers))}"
        )
    config = (REPOSITORY_ROOT / "plugins/src/main/kotlin/config/BuildTimeConfig.kt").read_text()
    if FIREBASE_RELEASE_APP_ID not in config:
        raise DistributionError("Android source Firebase Release App ID is not the aviva-chat project registration")
    firebase_resources = (
        REPOSITORY_ROOT / "libraries/pushproviders/firebase/src/main/res/values/firebase.xml"
    ).read_text()
    required_firebase_values = (
        '<string name="gcm_defaultSenderId" translatable="false">60506354350</string>',
        '<string name="google_storage_bucket" translatable="false">aviva-chat.firebasestorage.app</string>',
        '<string name="project_id" translatable="false" tools:ignore="UnusedResources">aviva-chat</string>',
    )
    missing_values = [value.split('name="', 1)[1].split('"', 1)[0] for value in required_firebase_values if value not in firebase_resources]
    if missing_values:
        raise DistributionError(f"Android Firebase resource config is not migrated to aviva-chat: {', '.join(missing_values)}")
    return version_code, version_name


def current_firebase_push_url() -> str:
    source = (REPOSITORY_ROOT / "features/enterprise/impl-foss/src/main/kotlin/io/element/android/features/enterprise/impl/DefaultEnterpriseService.kt").read_text()
    match = re.search(r'FIREBASE_PUSH_GATEWAY\s*=\s*"([^"]+)"', source)
    if not match:
        raise DistributionError("Could not read the Android Firebase push gateway from DefaultEnterpriseService.kt")
    return match.group(1)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
