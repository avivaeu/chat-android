import config.BuildTimeConfig
import extension.buildConfigFieldStr
import extension.readLocalProperty
import extension.setupDependencyInjection
import extension.testCommonDependencies

/*
 * Copyright (c) 2025 Element Creations Ltd.
 * Copyright 2023, 2024 New Vector Ltd.
 *
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Element-Commercial.
 * Please see LICENSE files in the repository root for full details.
 */
plugins {
    id("io.element.android-library")
}

android {
    namespace = "io.element.android.services.analyticsproviders.sentry"

    buildFeatures {
        buildConfig = true
    }

    defaultConfig {
        // Aviva FOSS/GPlay builds read approved Sentry configuration only from local properties
        // or explicitly named AVIVA_* environment variables. Never consume Element CI secrets.
        val avivaSentryDsn = System.getenv("AVIVA_SENTRY_DSN")?.takeIf { it.isNotBlank() }
            ?: readLocalProperty("services.sentry.dsn")?.takeIf { it.isNotBlank() }
            ?: BuildTimeConfig.SERVICES_SENTRY_DSN.takeIf { isEnterpriseBuild }
        val avivaSentryRustDsn = System.getenv("AVIVA_SENTRY_RUST_DSN")?.takeIf { it.isNotBlank() }
            ?: readLocalProperty("services.sentry.rustDsn")?.takeIf { it.isNotBlank() }
            ?: BuildTimeConfig.SERVICES_SENTRY_DSN_RUST.takeIf { isEnterpriseBuild }
            ?: avivaSentryDsn
        buildConfigFieldStr(
            name = "SENTRY_DSN",
            value = avivaSentryDsn ?: "",
        )
        buildConfigFieldStr(
            name = "SDK_SENTRY_DSN",
            value = avivaSentryRustDsn ?: "",
        )
    }
}

setupDependencyInjection()

dependencies {
    implementation(libs.sentry)
    implementation(libs.coroutines.core)
    implementation(libs.androidx.annotationjvm)
    implementation(projects.libraries.core)
    implementation(projects.libraries.di)
    implementation(projects.libraries.matrix.api)
    implementation(projects.services.analyticsproviders.api)
    implementation(projects.services.appnavstate.api)

    testCommonDependencies(libs, false)
    testImplementation(projects.libraries.matrix.test)
    testImplementation(projects.services.appnavstate.test)
}
