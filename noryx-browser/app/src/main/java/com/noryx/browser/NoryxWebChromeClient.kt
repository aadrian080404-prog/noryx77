package com.noryx.browser

import android.webkit.WebChromeClient
import android.webkit.WebView

class NoryxWebChromeClient(private val progress: (Int) -> Unit) : WebChromeClient() {
    override fun onProgressChanged(view: WebView, newProgress: Int) { progress(newProgress) }
}
