package com.noryx.browser

import android.net.Uri

/** Main-frame navigation policy: HTTPS only. */
object NavigationPolicy {
    fun allowsMainFrame(url: String?): Boolean {
        if (url.isNullOrBlank()) return false
        val parsed = Uri.parse(url)
        return parsed.scheme?.equals("https", ignoreCase = true) == true
    }
}
