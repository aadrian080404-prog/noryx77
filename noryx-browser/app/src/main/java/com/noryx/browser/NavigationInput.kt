package com.noryx.browser

import java.net.URLEncoder

object NavigationInput {
    private const val SEARCH = "https://www.google.com/search?q="
    private val SCHEME_PATTERN = Regex("^[A-Za-z][A-Za-z0-9+.-]*:")

    fun normalize(input: String): String {
        val value = input.trim()
        require(value.isNotEmpty()) { "empty navigation input" }
        require(value.none { it.code < 0x20 || it.code == 0x7F }) { "invalid_navigation_input" }

        if (SCHEME_PATTERN.containsMatchIn(value)) {
            require(value.startsWith("https://", ignoreCase = true)) { "https_only" }
            return value
        }

        return if (value.contains(".") && !value.contains(" ")) {
            "https://$value"
        } else {
            SEARCH + URLEncoder.encode(value, "UTF-8")
        }
    }
}
