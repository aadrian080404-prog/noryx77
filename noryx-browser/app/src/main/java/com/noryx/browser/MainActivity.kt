package com.noryx.browser

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.EditText
import android.widget.LinearLayout
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.noryx.browser.databinding.ActivityMainBinding
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class MainActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMainBinding
    private lateinit var controller: BrowserController
    private lateinit var gatewayExecutor: ExecutorService
    private var gatewayClient: NoryxGatewayClient? = null
    private var browserPairingCode: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        gatewayExecutor = Executors.newSingleThreadExecutor()

        configureWebView()
        controller = BrowserController(binding.webView)

        binding.back.setOnClickListener { controller.goBack() }
        binding.forward.setOnClickListener { controller.goForward() }
        binding.reload.setOnClickListener {
            clearError()
            controller.reload()
        }
        binding.home.setOnClickListener {
            clearError()
            controller.loadHome()
        }
        binding.retry.setOnClickListener {
            clearError()
            controller.reload()
        }
        binding.tabs.setOnClickListener { showGatewayDialog() }
        binding.tabs.contentDescription = "NORYX7 Gateway"
        configureDebugTestLab()

        binding.address.setOnEditorActionListener { _, _, _ ->
            clearError()
            try {
                controller.navigateInput(binding.address.text.toString())
            } catch (_: IllegalArgumentException) {
                showError()
            }
            true
        }

        if (savedInstanceState == null) controller.loadHome()
        updateNavigationState()
    }

    private fun configureDebugTestLab() {
        if (!BuildConfig.DEBUG) return
        val id = resources.getIdentifier("debugTestLab", "id", packageName)
        if (id == 0) return
        findViewById<View>(id)?.setOnClickListener {
            startActivity(Intent(this, Class.forName("com.noryx.browser.testlab.TestLabActivity")))
        }
    }

    private fun showGatewayDialog() {
        val input = EditText(this).apply {
            hint = "Scrivi una richiesta per NORYX7"
            minLines = 3
            maxLines = 6
            setPadding(32, 24, 32, 24)
        }
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(24, 0, 24, 0)
            addView(input)
        }
        val dialog = AlertDialog.Builder(this)
            .setTitle("NORYX7 Gateway")
            .setMessage("Richiesta → Gateway → Runtime → risposta verificata")
            .setView(container)
            .setNegativeButton("Annulla", null)
            .setPositiveButton("Invia", null)
            .create()

        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val text = input.text.toString().trim()
                if (text.isEmpty()) {
                    input.error = "Inserisci una richiesta"
                    return@setOnClickListener
                }
                dialog.getButton(AlertDialog.BUTTON_POSITIVE).isEnabled = false
                input.isEnabled = false
                ensureGatewaySession(text, dialog)
            }
        }
        dialog.show()
    }

    private fun ensureGatewaySession(text: String, requestDialog: AlertDialog) {
        if (gatewayClient != null) {
            executeGatewayRequest(text, requestDialog)
            return
        }

        val pairingInput = EditText(this).apply {
            hint = "Codice di pairing"
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_PASSWORD
            setPadding(32, 24, 32, 24)
        }
        val pairingDialog = AlertDialog.Builder(this)
            .setTitle("Collega NORYX7 Browser")
            .setMessage("Inserisci il codice di pairing fornito dall'amministratore NORYX7. Il codice non viene salvato nell'app.")
            .setView(pairingInput)
            .setNegativeButton("Annulla") { _, _ ->
                requestDialog.dismiss()
            }
            .setPositiveButton("Collega", null)
            .create()

        pairingDialog.setOnShowListener {
            pairingDialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val code = pairingInput.text.toString().trim()
                if (code.isEmpty()) {
                    pairingInput.error = "Codice richiesto"
                    return@setOnClickListener
                }
                browserPairingCode = code
                pairingInput.isEnabled = false
                pairingDialog.getButton(AlertDialog.BUTTON_POSITIVE).isEnabled = false
                gatewayClient = NoryxGatewayClient(
                    baseUrl = getString(R.string.noryx_gateway_url),
                    pairingCodeProvider = { browserPairingCode.orEmpty() },
                    clientId = getString(R.string.noryx_gateway_client_id),
                )
                pairingDialog.dismiss()
                executeGatewayRequest(text, requestDialog)
            }
        }
        pairingDialog.show()
    }

    private fun executeGatewayRequest(text: String, dialog: AlertDialog) {
        gatewayExecutor.execute {
            try {
                val client = gatewayClient ?: throw NoryxGatewayClient.GatewayException("gateway_session_required")
                val result = client.execute(text)
                runOnUiThread {
                    dialog.dismiss()
                    AlertDialog.Builder(this)
                        .setTitle("NORYX7 — Risposta verificata")
                        .setMessage(result.result)
                        .setPositiveButton("OK", null)
                        .show()
                }
            } catch (error: Exception) {
                runOnUiThread {
                    dialog.dismiss()
                    AlertDialog.Builder(this)
                        .setTitle("Gateway rifiutato")
                        .setMessage(error.message ?: "Impossibile completare la richiesta.")
                        .setPositiveButton("OK", null)
                        .show()
                }
            }
        }
    }

    private fun configureWebView() {
        binding.webView.settings.javaScriptEnabled = true
        binding.webView.settings.domStorageEnabled = true
        binding.webView.settings.allowFileAccess = false
        binding.webView.settings.allowContentAccess = false
        binding.webView.settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW
        binding.webView.webViewClient = NoryxWebViewClient(
            onNavigationChanged = { state ->
                runOnUiThread {
                    binding.address.setText(state.url)
                    binding.back.isEnabled = state.canGoBack
                    binding.forward.isEnabled = state.canGoForward
                }
            },
            onError = { runOnUiThread { showError() } },
        )
        binding.webView.webChromeClient = NoryxWebChromeClient { progress ->
            binding.progress.progress = progress
            binding.progress.visibility = if (progress < 100) View.VISIBLE else View.GONE
        }
    }

    private fun updateNavigationState() {
        binding.back.isEnabled = binding.webView.canGoBack()
        binding.forward.isEnabled = binding.webView.canGoForward()
        binding.address.setText(binding.webView.url.orEmpty())
    }

    private fun showError() { binding.errorPanel.visibility = View.VISIBLE }

    private fun clearError() {
        binding.errorPanel.visibility = View.GONE
        binding.address.error = null
    }

    override fun onSaveInstanceState(outState: Bundle) {
        binding.webView.saveState(outState)
        super.onSaveInstanceState(outState)
    }

    override fun onRestoreInstanceState(savedInstanceState: Bundle) {
        super.onRestoreInstanceState(savedInstanceState)
        binding.webView.restoreState(savedInstanceState)
        updateNavigationState()
    }

    override fun onDestroy() {
        gatewayExecutor.shutdownNow()
        binding.webView.stopLoading()
        binding.webView.destroy()
        super.onDestroy()
    }
}
