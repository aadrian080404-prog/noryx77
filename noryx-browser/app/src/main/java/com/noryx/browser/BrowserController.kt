package com.noryx.browser

import android.webkit.WebView

class BrowserController(private val webView: WebView) {
    fun navigate(url: String) { webView.loadUrl(NavigationInput.normalize(url)) }
    fun navigateInput(input: String) { webView.loadUrl(NavigationInput.normalize(input)) }
    fun goBack() { if (webView.canGoBack()) webView.goBack() }
    fun goForward() { if (webView.canGoForward()) webView.goForward() }
    fun reload() = webView.reload()

    /**
     * Loads the offline home under a synthetic HTTPS origin so the navigation
     * policy never needs a broad `data:` exception for local content.
     */
    fun loadHome() = webView.loadDataWithBaseURL(
        HOME_ORIGIN,
        HomePage.HTML,
        "text/html",
        "UTF-8",
        null,
    )

    private companion object {
        const val HOME_ORIGIN = "https://home.noryx.local/"
    }
}
