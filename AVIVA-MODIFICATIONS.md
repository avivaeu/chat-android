# Aviva Android fork modifications

Copyright (c) 2026 Aviva. This file and Aviva-authored additions are licensed
under `AGPL-3.0-only`; see [`LICENSE`](LICENSE).

This repository is based on the Element X Android `v26.10.0` source baseline
(`21a94116766f429b45cec24dd0b17c1300e49dd1`), with Aviva changes through
revision `c29dae13a48b3277066f61ee3244ee8515bfb50b`. The upstream copyrights
and license notices remain in the files where they originated. The upstream Element
Commercial License is a separate written agreement offered by Element and does
not grant commercial rights to Aviva-authored code or modifications.

Aviva changes represented in the `26.10.1` source tree include:

- Aviva product identity, Matrix/SSO destinations, metadata host, and login
  behavior.
- Aviva Firebase project configuration and Android pusher app IDs, including
  append-only pusher registration behavior.
- Aviva's replacement of the legacy-call string in the 33 locale files under
  `features/messages/impl/src/main/res/values-*/translations.xml`.
- Aviva build configuration and release version metadata in `plugins/`.
- Aviva release automation in `tools/release/`, the branding string override,
  and Android build/distribution documentation.

The FOSS Play build does not include the optional Element Enterprise
submodule. This Aviva source snapshot also omits upstream GitHub Actions
workflows: release and Enterprise automation relies on Element-owned secrets,
private services, or permissions. CI can be added separately using Aviva-owned
infrastructure; no Element credentials or automation are part of this release.

## Play 26.10.1 source and artifact

- Package: `org.avivaeu.chat`
- Version: `26.10.1`, `versionCode 202610010`
- AAB SHA-256: `49fa16ee5eef5bf7597a9a774990d251b89c43a447a66256a1764230460c3c2b`
- The AAB's embedded `version-control-info.textproto` names Aviva revision
  `c29dae13a48b3277066f61ee3244ee8515bfb50b`. At build time, the application
  source changes from that working tree had not yet been committed; this release
  tag records those changes together with attribution/documentation hardening.
- The release tag is the source snapshot corresponding to the AAB's application
  code. A rebuild from the tag may not be byte-identical because Gradle embeds
  the new Git revision metadata.
- The AAB was submitted to Google Play for review. The GitHub release only
  redistributes that exact AAB; it does not replace or resubmit the Play build.
