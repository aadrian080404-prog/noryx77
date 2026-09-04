package com.noryx.browser

import java.net.URLEncoder

object NavigationInput {
    private const val SEARCH = "https://www.google.com/search?q="

    fun normalize(input: String): String {
        val value = input.trim()
        require(value.isNotEmpty()) { "empty navigation input" }
        require(!value.startsWith("http://", ignoreCase = true)) { "cleartext_http_disabled" }
        if (value.startsWith("https://", ignoreCase = true)) return value
        return if (value.contains(".") && !value.contains(" ")) "https://$value" else SEARCH + URLEncoder.encode(value, "UTF-8")
    }
}
