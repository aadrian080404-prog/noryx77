package com.noryx.browser

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class NavigationPolicyTest {
    @Test fun httpsIsAllowed() {
        assertTrue(NavigationPolicy.allowsMainFrame("https://example.com"))
    }

    @Test fun httpIsRejected() {
        assertFalse(NavigationPolicy.allowsMainFrame("http://example.com"))
    }

    @Test fun customSchemesAreRejected() {
        assertFalse(NavigationPolicy.allowsMainFrame("intent://example.com"))
        assertFalse(NavigationPolicy.allowsMainFrame("javascript:alert(1)"))
        assertFalse(NavigationPolicy.allowsMainFrame("file:///sdcard/test.html"))
    }

    @Test fun dataUrlsAreAlwaysRejected() {
        assertFalse(NavigationPolicy.allowsMainFrame("data:text/html,home"))
        assertFalse(NavigationPolicy.allowsMainFrame("data:text/html,<script>alert(1)</script>"))
    }

    @Test fun malformedHttpsUrlsAreRejected() {
        assertFalse(NavigationPolicy.allowsMainFrame("https://"))
        assertFalse(NavigationPolicy.allowsMainFrame("https:///path"))
        assertFalse(NavigationPolicy.allowsMainFrame("https://user:password@example.com"))
    }

    @Test fun syntheticOfflineHomeOriginIsAllowedAsHttps() {
        assertTrue(NavigationPolicy.allowsMainFrame("https://home.noryx.local/"))
    }

    @Test fun missingUrlIsRejected() {
        assertFalse(NavigationPolicy.allowsMainFrame(null))
        assertFalse(NavigationPolicy.allowsMainFrame(""))
    }
}
