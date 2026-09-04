package com.noryx.browser

import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient

class NoryxWebViewClient(
    private val onNavigationChanged: (NavigationState) -> Unit,
    private val onError: () -> Unit,
) : WebViewClient() {
    override fun onPageStarted(view: WebView, url: String?, favicon: android.graphics.Bitmap?) {
        super.onPageStarted(view, url, favicon)
        onNavigationChanged(state(view, url, loading = true))
    }

    override fun onPageFinished(view: WebView, url: String?) {
        super.onPageFinished(view, url)
        onNavigationChanged(state(view, url, loading = false))
    }

    override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean = false

    override fun onReceivedError(view: WebView, request: WebResourceRequest, error: WebResourceError) {
        if (request.isForMainFrame) onError()
    }

    private fun state(view: WebView, url: String?, loading: Boolean): NavigationState =
        NavigationState(
            url = url.orEmpty(),
            loading = loading,
            canGoBack = view.canGoBack(),
            canGoForward = view.canGoForward(),
        )
}
