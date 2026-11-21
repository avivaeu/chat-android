/*
 * Copyright (c) 2025 Element Creations Ltd.
 * Copyright 2022-2025 New Vector Ltd.
 *
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Element-Commercial.
 * Please see LICENSE files in the repository root for full details.
 */

import config.BuildTimeConfig
import extension.buildConfigFieldStr
import extension.readLocalProperty
import extension.testCommonDependencies

plugins {
    id("io.element.android-compose-library")
    id("kotlin-parcelize")
}

android {
    namespace = "io.element.android.features.location.api"

    buildFeatures {
        buildConfig = true
    }

    defaultConfig {
        // Direct MapTiler requests require the client key in the application. Keep it out of
        // generated APKs/AABs by default until the user approves client-key packaging. If approved
        // for a local build, set AVIVA_MAPTILER_ALLOW_CLIENT_KEY_IN_ARTIFACT=true; the key itself
        // is read only from protected local inputs and is never logged or written to tracked files.
        val allowMapTilerKeyInArtifact = System.getenv("AVIVA_MAPTILER_ALLOW_CLIENT_KEY_IN_ARTIFACT") == "true"
        val avivaMapTilerApiKey = if (allowMapTilerKeyInArtifact) {
            System.getenv("AVIVA_MAPTILER_API_KEY")?.takeIf { it.isNotBlank() }
                ?: rootProject.file("../.secrets/maptiler.key")
                    .takeIf { it.isFile }
                    ?.readText()
                    ?.trim()
                    ?.takeIf { it.isNotBlank() }
                ?: readLocalProperty("services.maptiler.apikey")?.takeIf { it.isNotBlank() }
        } else {
            null
        }
        buildConfigFieldStr(
            name = "MAPTILER_BASE_URL",
            value = BuildTimeConfig.SERVICES_MAPTILER_BASE_URL,
        )
        buildConfigFieldStr(
            name = "MAPTILER_API_KEY",
            value = if (isEnterpriseBuild) {
                BuildTimeConfig.SERVICES_MAPTILER_APIKEY
            } else {
                avivaMapTilerApiKey
            },
        )
        buildConfigFieldStr(
            name = "MAPTILER_LIGHT_MAP_ID",
            value = if (isEnterpriseBuild) {
                BuildTimeConfig.SERVICES_MAPTILER_LIGHT_MAPID
            } else {
                System.getenv("AVIVA_MAPTILER_LIGHT_MAP_ID")
                    ?: readLocalProperty("services.maptiler.lightMapId")
            },
        )
        buildConfigFieldStr(
            name = "MAPTILER_DARK_MAP_ID",
            value = if (isEnterpriseBuild) {
                BuildTimeConfig.SERVICES_MAPTILER_DARK_MAPID
            } else {
                System.getenv("AVIVA_MAPTILER_DARK_MAP_ID")
                    ?: readLocalProperty("services.maptiler.darkMapId")
            },
        )
    }
}

dependencies {
    implementation(projects.libraries.architecture)
    implementation(projects.libraries.designsystem)
    implementation(projects.libraries.core)
    implementation(projects.libraries.matrix.api)
    implementation(projects.libraries.uiStrings)
    implementation(projects.features.enterprise.api)
    implementation(libs.coil.compose)

    testCommonDependencies(libs)
}
