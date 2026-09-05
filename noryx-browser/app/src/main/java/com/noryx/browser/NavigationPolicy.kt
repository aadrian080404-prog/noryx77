package com.noryx.browser

import android.net.Uri

/** Main-frame navigation policy: HTTPS only, with an explicit local-home exception. */
object NavigationPolicy {
    fun allowsMainFrame(url: String?, allowLocalHome: Boolean = false): Boolean {
        if (url.isNullOrBlank()) return false
        val scheme = Uri.parse(url).scheme?.lowercase() ?: return false
        if (scheme == "https") return true
        return allowLocalHome && scheme == "data"
    }
}
