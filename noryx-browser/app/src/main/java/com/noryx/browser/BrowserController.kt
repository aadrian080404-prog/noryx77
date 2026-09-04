package com.noryx.browser

import android.webkit.WebView
import android.webkit.URLUtil
import java.net.URLEncoder

class BrowserController(private val webView: WebView) {
    fun navigate(url: String) { webView.loadUrl(normalize(url)) }
    fun navigateInput(input: String) {
        val value = input.trim()
        if (value.isEmpty()) return
        val target = if (URLUtil.isHttpsUrl(value)) value else if (value.contains(".") && !value.contains(" ")) "https://$value" else "https://www.google.com/search?q=" + URLEncoder.encode(value, "UTF-8")
        webView.loadUrl(target)
    }
    fun goBack() { if (webView.canGoBack()) webView.goBack() }
    fun goForward() { if (webView.canGoForward()) webView.goForward() }
    fun reload() = webView.reload()
    fun loadHome() = webView.loadDataWithBaseURL(null, "<!doctype html><html><body><h1>NORYX Browser</h1><p>Pagina iniziale offline.</p></body></html>", "text/html", "UTF-8", null)
    private fun normalize(url: String) = if (URLUtil.isHttpsUrl(url)) url else "https://$url"
}
