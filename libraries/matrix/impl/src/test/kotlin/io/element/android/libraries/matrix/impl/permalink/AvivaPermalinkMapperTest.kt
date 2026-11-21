/*
 * Copyright (c) 2025 Element Creations Ltd.
 * Copyright 2023-2025 New Vector Ltd.
 *
 * SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-Element-Commercial.
 * Please see LICENSE files in the repository root for full details.
 */

package io.element.android.libraries.matrix.impl.permalink

import com.google.common.truth.Truth.assertThat
import org.junit.Test

class AvivaPermalinkMapperTest {
    @Test
    fun `maps Matrix-to permalinks to Aviva Web`() {
        assertThat(mapToAvivaPermalink("https://matrix.to/#/@alice:chat.avivaeu.org"))
            .isEqualTo("https://web.chat.avivaeu.org/#/@alice:chat.avivaeu.org")
        assertThat(mapToAvivaPermalink("https://matrix.to/#/#announcements:chat.avivaeu.org"))
            .isEqualTo("https://web.chat.avivaeu.org/#/#announcements:chat.avivaeu.org")
    }

    @Test
    fun `leaves non-Matrix permalink unchanged`() {
        assertThat(mapToAvivaPermalink("https://web.chat.avivaeu.org/#/@alice:chat.avivaeu.org"))
            .isEqualTo("https://web.chat.avivaeu.org/#/@alice:chat.avivaeu.org")
    }
}
