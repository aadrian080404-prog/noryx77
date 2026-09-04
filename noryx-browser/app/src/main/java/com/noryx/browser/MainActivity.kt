package com.noryx.browser

import android.os.Bundle
import android.view.View
import androidx.appcompat.app.AppCompatActivity
import com.noryx.browser.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var controller: BrowserController
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        configureWebView()
        controller = BrowserController(binding.webView)
        binding.back.setOnClickListener { controller.goBack() }
        binding.forward.setOnClickListener { controller.goForward() }
        binding.reload.setOnClickListener { controller.reload() }
        binding.home.setOnClickListener { controller.loadHome() }
        binding.address.setOnEditorActionListener { _, _, _ -> controller.navigateInput(binding.address.text.toString()); true }
        if (savedInstanceState == null) controller.loadHome()
    }
    private fun configureWebView() {
        binding.webView.settings.javaScriptEnabled = true
        binding.webView.settings.domStorageEnabled = true
        binding.webView.settings.allowFileAccess = false
        binding.webView.settings.allowContentAccess = false
        binding.webView.settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
        binding.webView.webViewClient = NoryxWebViewClient { binding.address.error = "Impossibile caricare la pagina." }
        binding.webView.webChromeClient = NoryxWebChromeClient { p -> binding.progress.progress = p; binding.progress.visibility = if (p < 100) View.VISIBLE else View.GONE }
    }
    override fun onSaveInstanceState(outState: Bundle) { binding.webView.saveState(outState); super.onSaveInstanceState(outState) }
    override fun onRestoreInstanceState(savedInstanceState: Bundle) { super.onRestoreInstanceState(savedInstanceState); binding.webView.restoreState(savedInstanceState) }
    override fun onDestroy() { binding.webView.stopLoading(); binding.webView.destroy(); super.onDestroy() }
}
