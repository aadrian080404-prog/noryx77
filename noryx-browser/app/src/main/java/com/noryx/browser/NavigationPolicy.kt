package com.noryx.browser

import java.net.URI

/** Main-frame navigation policy: only well-formed HTTPS URLs are navigable. */
object NavigationPolicy {

    fun allowsMainFrame(url: String?): Boolean {
        if (url.isNullOrBlank()) return false

        val parsed = runCatching { URI(url) }.getOrNull()
            ?: return false

        if (!parsed.scheme.equals("https", ignoreCase = true)) {
            return false
        }

        if (parsed.host.isNullOrBlank()) {
            return false
        }

        if (parsed.userInfo != null) {
            return false
        }

        return true
    }
}
