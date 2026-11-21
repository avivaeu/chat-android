/*
 * Copyright (c) 2025 Element Creations Ltd.
 * Copyright 2025 New Vector Ltd.
 * Copyright (c) 2026 Aviva.
 *
 * SPDX-License-Identifier: AGPL-3.0-only
 * Please see LICENSE files in the repository root for full details.
 */

package config

object BuildTimeConfig {
    const val APPLICATION_ID = "org.avivaeu.chat"
    const val APPLICATION_NAME = "Aviva Chat"
    // Reverse-DNS scheme must correspond to the OAuth client_uri host so the MAS
    // native-client DCR policy accepts the redirect. Keep APPLICATION_ID unchanged.
    val METADATA_HOST_REVERSED: String? = "org.avivaeu.chat.info"
    val OAUTH_CLIENT_URL_PATH: String? = null
    val URL_WEBSITE: String? = "https://info.chat.avivaeu.org/"
    val URL_LOGO: String? = "https://info.chat.avivaeu.org/assets/aviva-logo-light.webp"
    val URL_COPYRIGHT: String? = "https://info.chat.avivaeu.org/"
    val URL_TERMS: String? = "https://info.chat.avivaeu.org/nutzungsbedingungen.html"
    val URL_ACCEPTABLE_USE: String? = "https://info.chat.avivaeu.org/nutzungsregeln.html"
    val URL_PRIVACY: String? = "https://info.chat.avivaeu.org/datenschutz.html"
    val URL_POLICY: String? = "https://info.chat.avivaeu.org/datenschutz.html"
    val SERVICES_MAPTILER_BASE_URL: String? = null
    val SERVICES_MAPTILER_APIKEY: String? = null
    val SERVICES_MAPTILER_LIGHT_MAPID: String? = null
    val SERVICES_MAPTILER_DARK_MAPID: String? = null
    val SERVICES_POSTHOG_HOST: String? = null
    val SERVICES_POSTHOG_APIKEY: String? = null
    val SERVICES_SENTRY_DSN: String? = null
    val SERVICES_SENTRY_DSN_RUST: String? = null
    val BUG_REPORT_URL: String? = ""
    val BUG_REPORT_APP_NAME: String? = ""
    const val PUSH_CONFIG_INCLUDE_FIREBASE: Boolean = true
    const val PUSH_CONFIG_INCLUDE_UNIFIED_PUSH: Boolean = false
    const val PUSHER_APP_ID_RELEASE = "org.avivaeu.chat.android.v2"
    const val PUSHER_APP_ID_DEBUG = "org.avivaeu.chat.android"
    const val PUSHER_APP_ID_NIGHTLY = "org.avivaeu.chat.android"
    const val GOOGLE_APP_ID_RELEASE = "1:60506354350:android:ac82f5fdf4785d6f24b33f"
    const val GOOGLE_APP_ID_DEBUG = "1:60506354350:android:e9ace14d4c0b162124b33f"
    const val GOOGLE_APP_ID_NIGHTLY = "1:60506354350:android:265d5228c78f687b24b33f"
}
