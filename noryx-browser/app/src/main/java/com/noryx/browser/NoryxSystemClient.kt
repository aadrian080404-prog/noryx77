package com.noryx.browser

import org.json.JSONObject
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

/** First-party NORYX System Protocol client. WebView is deliberately outside this path. */
class NoryxSystemClient internal constructor(
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
        baseUrl,
        pairingCodeProvider,
        clientId,
        HttpUrlConnectionTransport(baseUrl, connectTimeoutMs, readTimeoutMs),
    )

    private var sessionToken: String? = null
    private var sessionId: String? = null

    @Synchronized
    fun authenticate(): SessionResult {
        require(baseUrl.startsWith("https://") || (BuildConfig.DEBUG && baseUrl.startsWith("http://"))) { "noryx_system_https_required" }
        require(clientId.isNotBlank()) { "noryx_system_client_id_required" }
        val body = JSONObject().put("pairing_code", pairingCodeProvider().trim()).put("client_id", clientId).toString()
        val response = transport.request("POST", "/v1/browser/session", body, null)
        if (response.code !in 200..299) throw SystemException("noryx_system_auth_failed:${response.code}")
        val json = parseObject(response.body)
        val token = json.optString("session_token", "")
        val id = json.optString("session_id", "")
        if (token.isBlank() || id.isBlank()) throw SystemException("noryx_system_session_identity_missing")
        sessionToken = token
        sessionId = id
        return SessionResult(json.optBoolean("authenticated", true), json.optString("client_id", clientId), id)
    }

    @Synchronized
    fun execute(text: String, executionId: String? = null): ExecuteResult {
        require(text.isNotBlank()) { "noryx_system_input_required" }
        val token = sessionToken ?: run { authenticate(); sessionToken ?: throw SystemException("noryx_system_session_required") }
        val sid = sessionId ?: throw SystemException("noryx_system_session_identity_missing")
        val eid = executionId?.takeIf { it.isNotBlank() } ?: UUID.randomUUID().toString()
        val envelope = JSONObject()
            .put("protocol", "NORYX_SYSTEM_PROTOCOL")
            .put("version", "1")
            .put("message_type", "execute")
            .put("request_id", UUID.randomUUID().toString())
            .put("execution_id", eid)
            .put("session_id", sid)
            .put("principal_id", clientId)
            .put("client_id", clientId)
            .put("source", "noryx-browser")
            .put("input", JSONObject().put("text", text))
            .toString()

        var response = transport.request("POST", "/v1/system/execute", envelope, token)
        if (response.code == 401) {
            authenticate()
            response = transport.request("POST", "/v1/system/execute", envelope, sessionToken ?: throw SystemException("noryx_system_session_required"))
        }
        if (response.code !in 200..299) {
            val reason = runCatching { parseObject(response.body).optString("reason", "") }.getOrDefault("")
            throw SystemException(if (reason.isNotBlank()) reason else "noryx_system_execute_failed:${response.code}")
        }

        val envelopeResult = parseObject(response.body)
        if (envelopeResult.optString("protocol", "") != "NORYX_SYSTEM_PROTOCOL") throw SystemException("noryx_system_protocol_mismatch")
        if (envelopeResult.optString("execution_id", "") != eid) throw SystemException("noryx_system_execution_identity_mismatch")
        if (envelopeResult.optString("principal_id", "") != clientId) throw SystemException("noryx_system_principal_identity_mismatch")
        val result = envelopeResult.optJSONObject("result") ?: throw SystemException("noryx_system_result_missing")
        if (result.optString("status", "") != "completed") throw SystemException("noryx_system_execution_not_completed")
        val answer = result.optString("result", "")
        if (answer.isBlank()) throw SystemException("noryx_system_answer_missing")
        val verification = result.optJSONObject("verification") ?: throw SystemException("noryx_system_verification_missing")
        if (!verification.optBoolean("valid", false)) throw SystemException("noryx_system_result_unverified")
        return ExecuteResult(
            status = "completed",
            taskId = result.optString("task_id", ""),
            executionId = eid,
            result = answer,
            verificationStage = verification.optString("stage", ""),
        )
    }

    @Synchronized fun clearSession() { sessionToken = null; sessionId = null }

    internal interface Transport { fun request(method: String, path: String, body: String, bearerToken: String?): Response }
    internal data class Response(val code: Int, val body: String)

    private class HttpUrlConnectionTransport(private val baseUrl: String, private val connectTimeoutMs: Int, private val readTimeoutMs: Int) : Transport {
        override fun request(method: String, path: String, body: String, bearerToken: String?): Response {
            val connection = (URL(baseUrl.trimEnd('/') + path).openConnection() as HttpURLConnection)
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
                return Response(code, stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty())
            } catch (error: IOException) {
                throw SystemException("noryx_system_network_failure", error)
            } finally { connection.disconnect() }
        }
    }

    private fun parseObject(body: String): JSONObject = try { JSONObject(body) } catch (error: Exception) { throw SystemException("noryx_system_invalid_json", error) }

    data class SessionResult(val authenticated: Boolean, val clientId: String, val sessionId: String)
    data class ExecuteResult(val status: String, val taskId: String, val executionId: String, val result: String, val verificationStage: String)
    class SystemException(message: String, cause: Throwable? = null) : RuntimeException(message, cause)
}
