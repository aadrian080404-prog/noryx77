package com.noryx.browser

import org.junit.Assert.assertEquals
import org.junit.Test

class NavigationInputTest {
    @Test fun domainGetsHttps() {
        assertEquals("https://example.com", NavigationInput.normalize("example.com"))
    }

    @Test fun httpsIsPreserved() {
        assertEquals("https://example.com/path", NavigationInput.normalize("https://example.com/path"))
    }

    @Test(expected = IllegalArgumentException::class)
    fun cleartextHttpIsRejected() {
        NavigationInput.normalize("http://example.com")
    }

    @Test fun phraseBecomesHttpsSearch() {
        assertEquals("https://www.google.com/search?q=hello+world", NavigationInput.normalize("hello world"))
    }
}
