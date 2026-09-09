package com.noryx.browser

import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

class NoryxGatewayClient internal constructor(
    private val baseUrl: String,
    private val pairingCodeProvider: () -> String,
    private val clientId: String,
    private val transport: Transport,
) {
    constructor(
        baseUrl: String,
        pairingCodeProvider: () -> String,
        clientId: String,
        connectTimeoutMs: Int = 5000,
        readTimeoutMs: Int = 30000,
    ) : this(
        baseUrl = baseUrl,
        pairingCodeProvider = pairingCodeProvider,
        clientId = clientId,
        transport = HttpUrlConnectionTransport(
            baseUrl = baseUrl,
            connectTimeoutMs = connectTimeoutMs,
            readTimeoutMs = readTimeoutMs,
        ),
    )

    private var sessionToken: String? = null

    @Synchronized
    fun authenticate(): SessionResult {
        require(
            baseUrl.startsWith("https://") ||
                (BuildConfig.DEBUG && baseUrl.startsWith("http://"))
        ) { "gateway_https_required" }
        require(clientId.isNotBlank()) { "gateway_client_id_required" }

        val pairingCode = pairingCodeProvider().trim()
        require(pairingCode.isNotBlank()) { "gateway_pairing_required" }
        val body = JSONObject()
            .put("pairing_code", pairingCode)
            .put("client_id", clientId)
            .toString()

        val response = transport.request("POST", "/v1/browser/session", body, null)
        if (response.code !in 200..299) {
            throw GatewayException("gateway_browser_auth_failed:${response.code}")
        }

        val json = parseObject(response.body)
        val token = json.optString("session_token", "")
        if (token.isBlank()) throw GatewayException("gateway_session_token_missing")

        sessionToken = token
        return SessionResult(
            authenticated = json.optBoolean("authenticated", true),
            clientId = json.optString("client_id", clientId),
        )
    }

    @Synchronized
    fun execute(text: String, executionId: String? = null): ExecuteResult {
        require(text.isNotBlank()) { "gateway_input_required" }

        val token = sessionToken ?: run {
            authenticate()
            sessionToken ?: throw GatewayException("gateway_session_required")
        }

        val json = JSONObject()
            .put("input", text)
            .apply {
                if (!executionId.isNullOrBlank()) put("execution_id", executionId)
            }

        var response = transport.request("POST", "/v1/execute", json.toString(), token)
        if (response.code == 401) {
            authenticate()
            response = transport.request(
                "POST",
                "/v1/execute",
                json.toString(),
                sessionToken ?: throw GatewayException("gateway_session_required"),
            )
        }

        if (response.code !in 200..299) {
            val reason = runCatching { parseObject(response.body).optString("reason", "") }
                .getOrDefault("")
            throw GatewayException(
                if (reason.isNotBlank()) reason else "gateway_execute_failed:${response.code}",
            )
        }

        val result = parseObject(response.body)
        if (result.optString("status", "") != "completed") {
            throw GatewayException("gateway_execution_not_completed")
        }

        val answer = result.optString("result", "")
        if (answer.isBlank()) throw GatewayException("gateway_answer_missing")

        val verification = result.optJSONObject("verification")
            ?: throw GatewayException("gateway_verification_missing")
        if (!verification.optBoolean("valid", false)) {
            throw GatewayException("gateway_result_unverified")
        }

        return ExecuteResult(
            status = "completed",
            taskId = result.optString("task_id", ""),
            executionId = result.optString("execution_id", ""),
            result = answer,
            verificationStage = verification.optString("stage", ""),
        )
    }

    @Synchronized
    fun clearSession() { sessionToken = null }

    internal interface Transport {
        fun request(method: String, path: String, body: String, bearerToken: String?): Response
    }

    internal data class Response(val code: Int, val body: String)

    private class HttpUrlConnectionTransport(
        private val baseUrl: String,
        private val connectTimeoutMs: Int,
        private val readTimeoutMs: Int,
    ) : Transport {
        override fun request(method: String, path: String, body: String, bearerToken: String?): Response {
            val url = URL(baseUrl.trimEnd('/') + path)
            val connection = url.openConnection() as HttpURLConnection
            try {
                connection.requestMethod = method
                connection.connectTimeout = connectTimeoutMs
                connection.readTimeout = readTimeoutMs
                connection.useCaches = false
                connection.doInput = true
                connection.doOutput = true
                connection.setRequestProperty("Accept", "application/json")
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                if (!bearerToken.isNullOrBlank()) connection.setRequestProperty("Authorization", "Bearer $bearerToken")
                val bytes = body.toByteArray(Charsets.UTF_8)
                connection.setFixedLengthStreamingMode(bytes.size)
                connection.outputStream.use { it.write(bytes) }
                val code = connection.responseCode
                val stream = if (code >= 400) connection.errorStream else connection.inputStream
                val responseBody = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()
                return Response(code, responseBody)
            } catch (error: IOException) {
                throw GatewayException("gateway_network_failure", error)
            } finally {
                connection.disconnect()
            }
        }
    }

    private fun parseObject(body: String): JSONObject = try {
        JSONObject(body)
    } catch (error: Exception) {
        throw GatewayException("gateway_invalid_json", error)
    }

    data class SessionResult(val authenticated: Boolean, val clientId: String)
    data class ExecuteResult(
        val status: String,
        val taskId: String,
        val executionId: String,
        val result: String,
        val verificationStage: String,
    )

    class GatewayException(message: String, cause: Throwable? = null) : RuntimeException(message, cause)
}
