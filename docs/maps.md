# Use of maps

<!--- TOC -->

* [Overview](#overview)
* [Local development with MapTiler](#local-development-with-maptiler)
* [Making releasable builds with MapTiler](#making-releasable-builds-with-maptiler)
* [Using other map sources or MapTiler styles](#using-other-map-sources-or-maptiler-styles)

<!--- END -->

## Overview

Aviva Chat uses the upstream MapLibre/MapTiler integration to provide map imagery. Direct MapTiler requests require the Aviva account's public client key in the application. The user approved enabling the native integration; no proxy is used.

## Local development with MapTiler

Place the raw approved key in `chat/.secrets/maptiler.key` or set `services.maptiler.apikey` in ignored `local.properties` / `AVIVA_MAPTILER_API_KEY` in the environment. Set `AVIVA_MAPTILER_ALLOW_CLIENT_KEY_IN_ARTIFACT=true` when building to inject the client key into generated BuildConfig. The key is never printed or written to tracked source.

Aviva currently uses MapTiler's built-in `basic-v2` light and `basic-v2-dark` dark styles. Optional overrides are `services.maptiler.lightMapId` / `services.maptiler.darkMapId` in ignored `local.properties`, or `AVIVA_MAPTILER_LIGHT_MAP_ID` / `AVIVA_MAPTILER_DARK_MAP_ID` environment variables. With no overrides, the upstream defaults remain in effect.

## Making releasable builds with MapTiler

For Aviva release builds, enable `AVIVA_MAPTILER_ALLOW_CLIENT_KEY_IN_ARTIFACT=true` and read the key from the ignored local file or a protected CI secret. Restrict/quota the public client key at MapTiler where supported. Do not use Element-owned credentials or print Gradle configuration values.

## Using other map sources or MapTiler styles

If you wish to use an alternative map provider, you can provide your own implementations of
`TileServerStyleUriBuilder` and `StaticMapUrlBuilder` in
`features/location/api/src/main/kotlin/io/element/android/features/location/api/internal/`.
