<!-- Copyright (c) 2026 Aviva. SPDX-License-Identifier: AGPL-3.0-only -->

# Aviva Chat Android build and Google Play deployment

This document describes how to build, sign, validate, and distribute Aviva Chat for Android from the current source repository. The current release is `26.10.1` (`versionCode 202610010`); the `26.10.0` deployment below is historical evidence. It records the Google Play Internal Testing deployment, Firebase project transition, and Internal App Sharing as a separate option.

## Scope and source

- Android source of truth: `/Users/fa2gq58/code/aviva/chat/android`.
- Do not build from or copy from the legacy `/Users/fa2gq58/code/aviva/aviva-chat-android` repository.
- Package ID: `org.avivaeu.chat`. Keep it unchanged to preserve Play app continuity.
- Current Play release: `26.10.1`, `versionCode 202610010`. The initial
  `26.10.0` deployment is retained below as historical evidence.
- Distribution currently used: **Google Play Internal Testing**. Internal App Sharing is described separately below and was not used for this release.
- Do not publish to Production as part of this workflow.

## Prerequisites

- JDK 21 and Android SDK/build tools 37. This workstation's SDK is `/opt/homebrew/share/android-commandlinetools`; `local.properties` supplies the SDK path.
- `bundletool` installed for AAB inspection.
- Play Console access to `org.avivaeu.chat` with permission to manage releases on the Internal Testing track.
- Google Android Publisher API enabled for the Google identity/project being used.
- Aviva upload keystore outside the repository at `~/.keystores/aviva-chat-android/upload-keystore.jks`.
- The keystore password is held locally in `chat/.secrets/android-keypass`. Restrict that file to the owner (`chmod 600`). Do not print its contents or add it to Git.
- The keystore alias and passwords must be supplied to Gradle through the supported `AVIVA_RELEASE_*` environment variables. Never put password values in this document, shell history, command-line arguments, build logs, or tracked properties.

Gradle release signing reads:

| Environment variable | Value |
|---|---|
| `AVIVA_RELEASE_STORE_FILE` | Path to Aviva upload keystore |
| `AVIVA_RELEASE_STORE_PASSWORD` | Local keystore password |
| `AVIVA_RELEASE_KEY_ALIAS` | Alias in the keystore |
| `AVIVA_RELEASE_KEY_PASSWORD` | Local private-key password |

On the currently provisioned machine, the password file supplies the same password for both store and key. Confirm this against the current keystore before reusing the procedure; use a secure local prompt/secret manager if they differ.

## Build the Play AAB

Run from the Android repository root. The release Gradle task fails early if any Aviva signing input is missing.

```sh
cd /Users/fa2gq58/code/aviva/chat/android
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"
./gradlew :app:bundleGplayRelease
```

The artifact is:

```text
app/build/outputs/bundle/gplayRelease/app-gplay-release.aab
```

### Secure signing setup used on this workstation

The successful build read the password locally, resolved the keystore's private-key alias without printing the password, put signing inputs only in the child Gradle process environment, and ran `:app:bundleGplayRelease`. Do not enable shell tracing (`set -x`) during signing.

Equivalent safe local setup (confirm the alias if the keystore changes):

```sh
cd /Users/fa2gq58/code/aviva/chat/android
(
  set +x
  export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
  export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"
  export AVIVA_RELEASE_STORE_FILE="$HOME/.keystores/aviva-chat-android/upload-keystore.jks"
  IFS= read -r AVIVA_RELEASE_STORE_PASSWORD < ../.secrets/android-keypass
  export AVIVA_RELEASE_STORE_PASSWORD
  export AVIVA_RELEASE_KEY_PASSWORD="$AVIVA_RELEASE_STORE_PASSWORD"
  export AVIVA_RELEASE_KEY_ALIAS="<alias-from-local-keystore>"
  ./gradlew :app:bundleGplayRelease
)
```

To inspect the alias locally, use `keytool -list -keystore "$AVIVA_RELEASE_STORE_FILE" -storepass:env AVIVA_RELEASE_STORE_PASSWORD`; do not put a password literal in the command. The successful build in this workspace used JDK `21.0.13.0.2` and Gradle `9.8.1`.

## Validate the AAB before distribution

Run the following from the Android repository root:

```sh
bundletool validate --bundle=app/build/outputs/bundle/gplayRelease/app-gplay-release.aab
bundletool dump manifest --bundle=app/build/outputs/bundle/gplayRelease/app-gplay-release.aab --module=base
jarsigner -verify app/build/outputs/bundle/gplayRelease/app-gplay-release.aab
shasum -a 256 app/build/outputs/bundle/gplayRelease/app-gplay-release.aab
```

Confirm the manifest has `package="org.avivaeu.chat"`, the intended `versionName`/`versionCode`, and target SDK. Confirm `jarsigner` reports `jar verified.` Compare the upload-key certificate fingerprint against the expected Play Console upload certificate before publishing. Record the AAB checksum and source commit with the release evidence.

## Google Play Internal Testing — deployed workflow

### Authenticate with the local OAuth client

The Play upload used Google Application Default Credentials (ADC) authenticated with the user's locally stored OAuth client JSON and these scopes:

- `https://www.googleapis.com/auth/cloud-platform`
- `https://www.googleapis.com/auth/androidpublisher`

The OAuth client JSON and ADC token must remain local and must never be committed or printed. For an authorized operator, the login command is:

```sh
gcloud auth application-default login \
  --client-id-file="<path-to-local-play-oauth-client.json>" \
  --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/androidpublisher"
```

Check that ADC login completed without displaying the token:

```sh
gcloud auth application-default print-access-token >/dev/null && echo "ADC listo"
```

An active `gcloud auth login` session alone may not have the Android Publisher scope. If Android Publisher returns `403 ACCESS_TOKEN_SCOPE_INSUFFICIENT`, complete ADC login with both scopes. If it instead reports an app permission/authorization failure, grant the Google identity access to this app and the Internal Testing release permission in Play Console. No API call should be attempted with credentials printed in logs.

### Release procedure

The Google Android Publisher API exposes a transactional edit. This deployment used an in-memory Python standard-library driver that obtained the ADC token from `gcloud`, streamed the AAB as binary, and did not save or print the token. Its API sequence was:

1. `POST /androidpublisher/v3/applications/org.avivaeu.chat/edits` to create an edit.
2. `GET /androidpublisher/v3/applications/org.avivaeu.chat/edits/{editId}/tracks` to verify track IDs and ensure the AAB `versionCode` is not already used by an equal/newer release.
3. Upload the AAB as media using the **upload** host path:

   ```text
   POST /upload/androidpublisher/v3/applications/org.avivaeu.chat/edits/{editId}/bundles?uploadType=media
   Content-Type: application/octet-stream
   Body: bytes of app-gplay-release.aab
   ```

4. Set the Internal Testing release with `PUT /androidpublisher/v3/applications/org.avivaeu.chat/edits/{editId}/tracks/internal` and a body like this historical `26.10.0` example:

   ```json
   {
     "track": "internal",
     "releases": [
       {
         "name": "Aviva Chat 26.10.0",
         "versionCodes": ["202610000"],
         "status": "completed"
       }
     ]
   }
   ```

5. `POST /androidpublisher/v3/applications/org.avivaeu.chat/edits/{editId}:validate`.
6. Only if validation succeeds, `POST /androidpublisher/v3/applications/org.avivaeu.chat/edits/{editId}:commit`.
7. Read back the `internal` track in a fresh edit and delete that read-only verification edit.

Use the actual track ID returned by Play Console/API; this app returned `internal`. The API success response/status and subsequent readback should confirm the version code and release status. A failed preflight/edit must be deleted; do not commit a partially configured edit.

### Initial Internal Testing deployment record (`26.10.0`)

- Package: `org.avivaeu.chat`
- Track: `internal`
- Release: `Aviva Chat 26.10.0`
- Version code: `202610000`
- Source commit: `c29dae13a4`
- AAB SHA-256: `3b0a2aeb62edba40cb435b68f15627dee9b9e1dae7e7c6ddc207580ee4ece205`
- Result: API edit committed; track readback showed release status `completed`.
- Google Play edit ID: `06480842308013923437`.
- No Production track was modified.

### Current release (`26.10.1`)

- Package: `org.avivaeu.chat`
- Release: `Aviva Chat 26.10.1`
- Version code: `202610010`
- AAB SHA-256: `49fa16ee5eef5bf7597a9a774990d251b89c43a447a66256a1764230460c3c2b`
- This is the AAB submitted for Google Play review. Play does not replace an
  artifact inside an already submitted release; a later Play release requires
  a greater version code. This GitHub release does not publish anything to Play.

## Firebase consolidation and dual-channel release (in progress)

### Project and app registrations

Firebase project IDs cannot be renamed after provisioning. The approved destination is the newly created project `aviva-chat` (display name `Aviva Chat`, project number `60506354350`). The old project `aviva-chat-android` remains active until all Firebase and server dependencies are migrated and verified. Do not delete it as part of the Android release steps.

Registered apps in `aviva-chat`:

| Variant/platform | Package/bundle ID | Firebase App ID |
|---|---|---|
| Android Release | `org.avivaeu.chat` | `1:60506354350:android:ac82f5fdf4785d6f24b33f` |
| Android Debug | `org.avivaeu.chat.debug` | `1:60506354350:android:e9ace14d4c0b162124b33f` |
| Android Nightly | `org.avivaeu.chat.nightly` | `1:60506354350:android:265d5228c78f687b24b33f` |
| iOS | `org.avivaeu.chat` | `1:60506354350:ios:82e4f12a1e08e7ce24b33f` |

The shared Android/iOS bundle/package identifier is valid: Firebase registers them as distinct platform apps with distinct Firebase App IDs. Android `BuildTimeConfig.kt` now points at the new Android App IDs; the Gradle `applicationId` remains `org.avivaeu.chat`. iOS must update its own local Firebase configuration from the new iOS App ID using the iOS owner's normal repository conventions. The Android agent does not modify the iOS repository.

The destination project currently uses Firebase Spark, while `aviva-chat-android` uses Blaze. FCM and App Distribution are the services in this Android plan; inventory any other active Firebase/Google Cloud resources and explicitly approve billing before enabling billable products or attaching a billing account.

### Firebase App Distribution self-enrollment

- Release app: Android App ID `1:60506354350:android:ac82f5fdf4785d6f24b33f`.
- Group alias: `aviva-technical-testers` (`Aviva Technical Testers`).
- A public group invite link has been created in Firebase Console with no domain restriction. It is an enrollment link, not an APK download link; it is intentionally not recorded in this tracked document. Share it only with the intended technical audience. Testers self-register with an email and accept/sign in; the owner need not manually add each address.
- Firebase CLI can list the destination group. The previous error was resolved by completing Firebase App Distribution onboarding in Console.
- The App Distribution contact email change to `webadmin@avivaeu.org` is pending its email confirmation. Confirm it before distributing so testers do not see the personal account that Firebase currently shows.
- Firebase invite links are created in the Console. Distribution itself can use Firebase CLI:

  ```sh
  firebase appdistribution:distribute <play-signed-universal.apk> \
    --app 1:60506354350:android:ac82f5fdf4785d6f24b33f \
    --groups aviva-technical-testers \
    --release-notes-file <release-notes.txt>
  ```

- Upload an APK only to this Firebase destination. Never send the AAB to Firebase. The Firebase group has no testers or releases yet; the invite link is ready but no artifact has been distributed.

### Migration progress and restart checklist

Update these checkboxes as each gate is completed. Do not remove the old Firebase project until the final item is satisfied.

- [x] Create Firebase project ID `aviva-chat` (project number `60506354350`, display name `Aviva Chat`). Project ID changes are not possible after provisioning; this is a separate project.
- [x] Register Android Release/Debug/Nightly and iOS `org.avivaeu.chat` apps in `aviva-chat`; their new App IDs are listed above.
- [x] Update Android `BuildTimeConfig.GOOGLE_APP_ID_RELEASE/DEBUG/NIGHTLY` and Firebase base resources (`project_id`, `gcm_defaultSenderId`, API-key resources, storage bucket) to `aviva-chat` without changing application ID, upload key, or app-signing key.
- [x] Build Gplay Debug and run focused app, Enterprise, Matrix, slash-command, and Push tests with the Android Studio JBR.
- [x] Verify Play's `generatedApks.list`/`generatedApks.download` can retrieve a universal APK signed with the Play App Signing certificate `89:F8:…`; the current Play-generated diagnostic APK has old Firebase resources and is not the migrated release artifact.
- [x] Enable Firebase App Distribution on the destination Release app, create group `aviva-technical-testers`, and create a public group invite link with no domain restriction. The group currently has zero testers and zero releases.
- [ ] Confirm the Firebase contact-email change to `webadmin@avivaeu.org`; until confirmed, Firebase Console still shows the current account contact.
- [x] Server-bot reported the Android Release mapping for Firebase project `aviva-chat` deployed and confirmed an end-to-end FCM smoke notification for `26.10.1` on 2026-11-20. Keep old Sygnal/FCM credentials for old pushers during migration.
- [x] Set Android pusher registration `append=true` so the new pusher does not evict pushers for other devices during the transition.
- [ ] Select and record the next globally increasing versionCode above current Play Internal `202610010` and all Firebase releases. For migration testing, Firebase install version N must be followed by a Play Internal release N+1. Once migrated, the APK retrieved from each Play AAB uses the same version/versionCode as that AAB.
- [ ] Build the next signed Gplay Release AAB with `AVIVA_RELEASE_*`, new Firebase App IDs and the server-confirmed push URL. Keep source `applicationId=org.avivaeu.chat` and existing keys unchanged.
- [ ] Upload the AAB to Play `internal` using the Play publisher tool below; wait for processing, then fetch the universal APK for that exact versionCode from Play App Signing.
- [ ] Validate the fetched APK has package `org.avivaeu.chat`, the new Release Firebase App ID, expected versionCode, and Play certificate SHA-256 `89:F8:…`; then distribute that APK (never the AAB) to Firebase group `aviva-technical-testers`.
- [x] Read-only Play Console verification confirmed the designated test account is in the existing `Aviva Testing` email list; the list was not modified. Android Publisher Testers API does not support email lists.
- [ ] Verify Firebase self-enrollment and an update from Firebase to a higher Play Internal version on a disposable test device.
- [ ] iOS owner updates the iOS repo to Firebase project `aviva-chat` / App ID `1:60506354350:ios:82e4f12a1e08e7ce24b33f` and verifies its own build/distribution.
- [ ] Inventory all Firebase/GCP resources and wait for server-bot to observe zero old-project pushers through the agreed soak period. Only then delete `aviva-chat-android`. Its billing plan is Blaze; `aviva-chat` is Spark. Do not transfer billing/enable paid products without explicit budget approval.

The Android migration changes Release/Debug/Nightly Firebase App IDs in `BuildTimeConfig.kt` and project resources in `libraries/pushproviders/firebase/src/main/res/values/firebase.xml`; pusher registration uses `append=true` with its focused test expectation updated. Three destination tools are under `tools/release/`: Play-generated APK fetch/verification, Firebase APK distribution, and Play Internal AAB publication. Gplay Debug assembly and focused tests passed with the Android Studio JBR. The `26.10.1` Play AAB uses the new Firebase project. No Firebase App Distribution release has been recorded yet; the older Play-generated diagnostic APK embeds the old Firebase App ID and is unsuitable for the destination project.

#### Firebase APK destination command

The fetched APK must pass the preflight and server/contact gates. The script defaults to dry-run:

```sh
python3 tools/release/download_play_signed_apk.py \
  --version-code <processed-play-version-code>

python3 tools/release/distribute_firebase_apk.py \
  --apk app/build/outputs/firebase/aviva-chat-play-signed-<version-code>.apk \
  --groups aviva-technical-testers \
  --release-notes-file <release-notes.txt>
```

Only after contact verification and server FCM validation, use the second command with `--publish --confirm-contact-email --confirm-fcm-ready`. Add `--next-play-version-code <higher-code>` when exercising the migration-update test; the corresponding Play release must be greater than the Firebase-installed APK.

#### Play Internal destination command

The Play script defaults to a dry run and refuses to commit until the new FCM route is confirmed:

```sh
python3 tools/release/publish_play_internal.py \
  --aab app/build/outputs/bundle/gplayRelease/app-gplay-release.aab \
  --release-name "Aviva Chat <version>" \
  --latest-firebase-version-code <highest-firebase-code>
```

After server validation, add `--commit --confirm-fcm-ready` to publish only to Play Internal Testing. Never use Production as a target for this workflow.

### APK signing compatibility and Play-generated APK retrieval

The local Aviva upload-key certificate is SHA-256 `B9:2E:BC:EA:A8:F9:74:04:54:D7:77:9D:97:09:4C:92:47:C8:B5:97:16:A0:4A:C9:90:E8:63:D4:FD:95:4B:7B`; the AAB uploaded to Play was signed with that upload key. The Play App Signing certificate is SHA-256 `89:F8:76:8F:1C:61:BD:11:29:C0:14:6A:B6:D5:52:75:04:8B:26:7E:09:EE:D7:21:76:A0:50:5A:35:A2:18:AC`. These differ, so do **not** distribute a locally generated Release APK signed with the upload key if seamless Play updates are required. The pre-existing local `app-gplay-release.apk` is debug-signed and is also not distributable.

The Android Publisher generated-APK API is the preferred way to retrieve the APK signed with Play's app-signing key. No local copy of Google's private app-signing key is needed:

1. `GET https://androidpublisher.googleapis.com/androidpublisher/v3/applications/org.avivaeu.chat/generatedApks/{versionCode}`.
2. From `generatedApks[]`, select `certificateSha256Hash` matching the Play App Signing fingerprint; take its `generatedUniversalApk.downloadId`.
3. `GET https://androidpublisher.googleapis.com/androidpublisher/v3/applications/org.avivaeu.chat/generatedApks/{versionCode}/downloads/{downloadId}:download?alt=media`.
4. Verify the APK package, Firebase app ID, expected `versionCode`, and `apksigner` SHA-256 before distributing it to Firebase.

Read-only API verification for the existing Play version `202610000` returned the supplied App Signing fingerprint and a universal download ID (plus 151 split APKs). The downloaded diagnostic APK at `app/build/outputs/firebase/aviva-chat-202610000-play-signed.apk` verifies package `org.avivaeu.chat`, version `26.10.0`/code `202610000`, and the Play App Signing certificate. It embeds the old Firebase app ID because it came from the old AAB; it is **not** suitable for distribution to `aviva-chat`. The `download_play_signed_apk.py` tool now automates the API lookup/download and rejects APKs whose compiled Firebase app ID is not the destination Release app ID.

### FCM migration status

Changing Android Firebase App IDs changes the FCM sender/project for newly updated clients. Server-bot reported the Android Release mapping for Firebase project `aviva-chat` deployed and confirmed a successful end-to-end FCM smoke notification for `26.10.1` on 2026-11-20. The app's gateway remains `https://push.chat.avivaeu.org/_matrix/push/v1/notify`; the proposed `push-v2` URL is not the endpoint used by this release.

Sygnal v0.17.0 supports one Firebase project per app mapping/instance. Preserve the old Firebase project, old Sygnal endpoint, and old credentials while old clients/pushers remain. Do not delete `aviva-chat-android` until server-bot confirms old-project pushers are at zero through an agreed soak period and all project resources/dependencies have been inventoried.

### Version alignment and migration test

- Current Play Internal release: `versionCode 202610010`.
- Allocate future version codes monotonically across both destinations. The Play Internal AAB must have a higher code than the most recent Firebase APK for an in-place Firebase-to-Play update. Verify Play's existing track codes and the Firebase release history before reserving a code.
- For the first migration test, distribute a Play-signed APK to Firebase, opt a disposable device into Internal Testing, then publish a later Internal AAB with a higher code and verify Play updates the installed app without uninstalling or losing app data. Use the designated test account and confirm it belongs to Play's `Aviva Testing` email list in Play Console first.
- In steady state, the Firebase APK should be generated by Play from the same AAB release, so both destinations have the same package, version name, version code, and app-signing certificate. The artifact-fetch/Firebase-upload action and the Play track publishing action remain separately invoked and gated. Firebase APK generation depends on Play having processed that AAB because Google holds the app-signing private key.
- Play Internal Testing is capped at 100 testers per app. The current `Aviva Testing` email list is administered in Play Console; Android Publisher `edits.testers.get/patch/update` only supports `googleGroups` and explicitly does not support email lists. Do not claim the tester list was verified or changed by API. Firebase's self-enrollment group is separate from the Play tester allow-list.

### Firebase project migration progress

Progress markers are maintained here so a resumed session can continue from this file:

- [x] Create Firebase/GCP destination project `aviva-chat` (project number `60506354350`, display name `Aviva Chat`). Firebase project IDs are immutable; this is a new project, not a rename.
- [x] Register Android Release/Debug/Nightly and iOS `org.avivaeu.chat` apps in the destination; use the App IDs listed above.
- [x] Update Android `BuildTimeConfig.GOOGLE_APP_ID_RELEASE/DEBUG/NIGHTLY` to the destination App IDs; Gplay Debug build and focused app/Enterprise/Matrix/slash-command tests passed with Android Studio JBR.
- [x] Complete Firebase App Distribution onboarding for Android Release; set the requested contact `webadmin@avivaeu.org` (email verification is pending).
- [x] Create Firebase group `aviva-technical-testers` and a public self-enrollment invite link with no domain restriction. Group has zero testers/releases at last CLI readback; invite link is in Firebase Console and intentionally not stored here.
- [x] Verify Play-generated universal APK download metadata for version `202610000` and certificate `89:F8:…`; the APK downloaded locally is diagnostic only because its embedded Firebase app ID is still from `aviva-chat-android`.
- [ ] Confirm the `webadmin@avivaeu.org` contact-email verification before distributing.
- [x] Server-side FCM/Sygnal Release mapping for `aviva-chat`; server-bot reported a successful end-to-end FCM smoke notification for `26.10.1` on 2026-11-20. The Android gateway is `https://push.chat.avivaeu.org/_matrix/push/v1/notify`. Keep the old route and credential for existing pushers through the migration soak. Android pusher registration uses `append=true` so a new pusher does not evict another device's pusher.
- [ ] Keep the old FCM service-account credential and Sygnal route available for existing pushers during the migration. Configure the new project's credential through the server owner's secure Secret workflow; do not put credentials in this repository or logs.
- [ ] Confirm the designated test account is in the Play Console `Aviva Testing` email list (API cannot read or modify email lists); use it for the migration smoke test.
- [ ] Bump the next release `versionCode` above Play's current `202610010` and above any Firebase release. Build a signed AAB with the Aviva Firebase configuration and confirmed push URL; publish only to Internal Testing after the server gate.
- [ ] Fetch the Play-signed universal APK for that AAB via `download_play_signed_apk.py`, validate new app ID/certificate/version, then distribute the APK (not AAB) to `aviva-technical-testers` with `distribute_firebase_apk.py`.
- [ ] Verify on a disposable device: self-join the Firebase invite, install the Firebase APK, opt into Play Internal Testing with the designated test account, then install a strictly higher Play versionCode without uninstalling; verify data, session and new-project push delivery.
- [ ] Notify/coordinate iOS owner to update its app config to iOS App ID `1:60506354350:ios:82e4f12a1e08e7ce24b33f`; old project stays intact while iOS and server migrations are in progress.
- [ ] Inventory old-project Firebase/GCP resources and dependencies; delete `aviva-chat-android` only after server-bot confirms zero old-project pushers through the soak period and Android/iOS/other resources no longer depend on it. The old project is Blaze; the new project is Spark. Do not attach billing without approval.

## Internal App Sharing — separate, not used for this release

Internal App Sharing (IAS) is a separate Play feature for uploading an APK/AAB and receiving an install/download link. It does **not** create or update a release on the Internal Testing track, does not replace its tester list, and was not used for the release recorded above.

The official AAB upload method is `internalappsharingartifacts.uploadbundle`:

```text
POST https://androidpublisher.googleapis.com/upload/androidpublisher/v3/applications/internalappsharing/org.avivaeu.chat/artifacts/bundle?uploadType=media
Authorization: Bearer <short-lived ADC access token>
Content-Type: application/octet-stream
Body: bytes of app-gplay-release.aab
```

It requires the `androidpublisher` OAuth scope. The response includes `downloadUrl`, `certificateFingerprint`, and `sha256`. Protect the access token; share the returned URL only with intended testers. IAS uses its own Play authorization/install behavior and should be treated as a separate distribution decision.

## References

- [Google Play Developer API setup](https://developers.google.com/android-publisher/getting_started)
- [Google Play bundle upload](https://developers.google.com/android-publisher/api-ref/rest/v3/edits.bundles/upload)
- [Google Play track update](https://developers.google.com/android-publisher/api-ref/rest/v3/edits.tracks/update)
- [Google Play edit validation](https://developers.google.com/android-publisher/api-ref/rest/v3/edits/validate)
- [Google Play edit commit](https://developers.google.com/android-publisher/api-ref/rest/v3/edits/commit)
- [Internal App Sharing bundle upload](https://developers.google.com/android-publisher/api-ref/rest/v3/internalappsharingartifacts/uploadbundle)
- [Internal App Sharing artifact response](https://developers.google.com/android-publisher/api-ref/rest/v3/internalappsharingartifacts)
