package com.noryx.browser

data class NavigationState(val url: String = "", val loading: Boolean = false, val canGoBack: Boolean = false, val canGoForward: Boolean = false)
