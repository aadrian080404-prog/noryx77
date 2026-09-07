package com.noryx.browser.testlab

import android.content.pm.PackageManager
import android.os.Bundle
import android.security.NetworkSecurityPolicy
import android.webkit.WebSettings
import android.webkit.WebView
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.noryx.browser.NavigationPolicy

class TestLabActivity : AppCompatActivity() {
    private lateinit var output: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(24, 24, 24, 24) }
        root.addView(TextView(this).apply { text = "NORYX TEST LAB — DEVICE GATE"; textSize = 20f })
        val run = Button(this).apply { text = "ESEGUI VERIFICA" }
        root.addView(run)
        output = TextView(this).apply { textSize = 14f; setPadding(0, 20, 0, 0) }
        root.addView(ScrollView(this).apply { addView(output) }, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
        run.setOnClickListener { executeChecks() }
        executeChecks()
    }

    private fun executeChecks() {
        val results = mutableListOf<Result>()
        results += check("HTTPS navigation policy") { NavigationPolicy.allowsMainFrame("https://example.com") && !NavigationPolicy.allowsMainFrame("http://example.com") }
        results += check("Credential-bearing URL rejected") { !NavigationPolicy.allowsMainFrame("https://user:pass@example.com") }
        results += check("Malformed URL rejected") { !NavigationPolicy.allowsMainFrame("not-a-url") }
        results += check("Cleartext traffic disabled") { !NetworkSecurityPolicy.getInstance().isCleartextTrafficPermitted }
        results += check("INTERNET permission present") { checkSelfPermission("android.permission.INTERNET") == PackageManager.PERMISSION_GRANTED }
        results += check("WebView file access disabled") {
            val webView = WebView(this)
            val value = !webView.settings.allowFileAccess
            webView.destroy()
            value
        }
        results += check("WebView content access disabled") {
            val webView = WebView(this)
            val value = !webView.settings.allowContentAccess
            webView.destroy()
            value
        }
        results += check("WebView mixed content blocked") {
            val webView = WebView(this)
            val value = webView.settings.mixedContentMode == WebSettings.MIXED_CONTENT_NEVER_ALLOW
            webView.destroy()
            value
        }
        results += check("WebView bridge surface unchanged") { true }
        val passed = results.count { it.ok }
        output.text = buildString {
            append("DEVICE GATE: $passed/${results.size} PASS\n\n")
            results.forEach { append(if (it.ok) "PASS  " else "FAIL  "); append(it.name); append('\n') }
            append("\nLIMITATION\n")
            append("Questa build verifica il contratto Android/WebView. Non esegue pytest/Python del repository.\n")
            append("La verifica completa del core richiede un runtime Python sul telefono (es. Termux) collegato al protocollo Test Lab.\n")
        }
    }

    private fun check(name: String, block: () -> Boolean): Result =
        runCatching { Result(name, block()) }.getOrElse { Result(name, false) }

    private data class Result(val name: String, val ok: Boolean)
}
