/*
 * Copyright (c) 2025 Element Creations Ltd.
 * Copyright 2023-2025 New Vector Ltd.
 *
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Element-Commercial.
 * Please see LICENSE files in the repository root for full details.
 */

package io.element.android.libraries.matrix.impl.permalink

import dev.zacsweers.metro.AppScope
import dev.zacsweers.metro.ContributesBinding
import io.element.android.libraries.core.extensions.runCatchingExceptions
import io.element.android.libraries.matrix.api.core.MatrixPatterns
import io.element.android.libraries.matrix.api.core.RoomAlias
import io.element.android.libraries.matrix.api.core.UserId
import io.element.android.libraries.matrix.api.permalink.PermalinkBuilder
import io.element.android.libraries.matrix.api.permalink.PermalinkBuilderError
import org.matrix.rustcomponents.sdk.matrixToRoomAliasPermalink
import org.matrix.rustcomponents.sdk.matrixToUserPermalink

@ContributesBinding(AppScope::class)
class DefaultPermalinkBuilder : PermalinkBuilder {
    override fun permalinkForUser(userId: UserId): Result<String> {
        if (!MatrixPatterns.isUserId(userId.value)) {
            return Result.failure(PermalinkBuilderError.InvalidData)
        }
        return runCatchingExceptions {
            mapToAvivaPermalink(matrixToUserPermalink(userId.value))
        }
    }

    override fun permalinkForRoomAlias(roomAlias: RoomAlias): Result<String> {
        if (!MatrixPatterns.isRoomAlias(roomAlias.value)) {
            return Result.failure(PermalinkBuilderError.InvalidData)
        }
        return runCatchingExceptions {
            mapToAvivaPermalink(matrixToRoomAliasPermalink(roomAlias.value))
        }
    }
}

internal fun mapToAvivaPermalink(permalink: String): String {
    return if (permalink.startsWith(MATRIX_TO_PERMALINK_PREFIX)) {
        AVIVA_PERMALINK_PREFIX + permalink.removePrefix(MATRIX_TO_PERMALINK_PREFIX)
    } else {
        permalink
    }
}

private const val MATRIX_TO_PERMALINK_PREFIX = "https://matrix.to/#/"
private const val AVIVA_PERMALINK_PREFIX = "https://web.chat.avivaeu.org/#/"
