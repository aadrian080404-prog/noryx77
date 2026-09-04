package com.noryx.browser

import android.webkit.WebView

class BrowserController(private val webView: WebView) {
    fun navigate(url: String) { webView.loadUrl(NavigationInput.normalize(url)) }
    fun navigateInput(input: String) { webView.loadUrl(NavigationInput.normalize(input)) }
    fun goBack() { if (webView.canGoBack()) webView.goBack() }
    fun goForward() { if (webView.canGoForward()) webView.goForward() }
    fun reload() = webView.reload()
    fun loadHome() = webView.loadDataWithBaseURL(null, HomePage.HTML, "text/html", "UTF-8", null)
}
