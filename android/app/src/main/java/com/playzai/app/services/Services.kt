package com.playzai.app.services

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import androidx.core.app.NotificationCompat
import com.playzai.app.R
import com.playzai.app.data.SecurityStore
import com.playzai.app.data.SecureTokenStore
import com.playzai.app.data.SettingsStore
import com.playzai.app.model.ConnectionStatus
import com.playzai.app.model.DeviceInfo
import com.playzai.app.model.SecurityEvent
import com.playzai.app.model.SecurityState
import com.playzai.app.model.SettingsState
import com.playzai.app.model.VoiceGender
import com.playzai.app.model.VoiceLanguage
import com.playzai.app.model.VoiceState
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URI
import java.util.Locale
import java.util.UUID
import kotlin.coroutines.resume
import kotlin.coroutines.suspendCoroutine

interface AiService {
    suspend fun sendMessage(conversationId: String, text: String): Result<String>
}

interface BackendService {
    suspend fun checkHealth(baseUrl: String, deviceId: String?, token: String?): ConnectionStatus
    suspend fun sendChat(baseUrl: String, deviceId: String?, token: String?, conversationId: String, text: String): Result<String>
    suspend fun fetchDevices(baseUrl: String, deviceId: String?, token: String?): Result<List<DeviceInfo>>
    suspend fun fetchSecurityEvents(baseUrl: String, deviceId: String?, token: String?): Result<List<SecurityEvent>>
}

interface DeviceService {
    val devices: Flow<List<DeviceInfo>>
    suspend fun refresh()
}

interface SecurityService {
    val state: StateFlow<SecurityState>
    suspend fun refresh()
    suspend fun enableLockdown()
    suspend fun disableLockdown()
    suspend fun revokeLocalSession()
}

interface VoiceService {
    val state: StateFlow<VoiceState>
    fun startListening(language: VoiceLanguage)
    fun stopListening()
    fun speak(text: String, language: VoiceLanguage, gender: VoiceGender, speechRate: Float, pitch: Float)
    fun stopSpeaking()
    fun shutdown()
}

interface MessagingService {
    suspend fun sendOfficialMessage(message: String): Result<Unit>
}

class DemoAiService : AiService {
    override suspend fun sendMessage(conversationId: String, text: String): Result<String> {
        delay(650)
        val normalized = text.trim().lowercase(Locale.getDefault())
        val reply = when {
            normalized.matches(Regex("(hi|hello|hey).*")) ->
                "Hello! I’m PlayzAI. How can I help?\n\nDemo Mode is active, so this reply was generated locally."
            normalized.contains("status") ->
                "You are in Demo / Offline Mode. No backend, PC agent, or remote AI connection is being claimed."
            normalized.contains("security") ->
                "Your local Security Center is ready. It will show real events recorded on this device; it will not invent remote activity."
            normalized.contains("hindi") || normalized.contains("हिंदी") ->
                "नमस्ते! यह स्थानीय डेमो उत्तर है। आप सेटिंग्स में बोलने की भाषा बदल सकते हैं।"
            else ->
                "I’m ready to help with planning, explanations, and safe device workflows. This is a local Demo Mode response until an authorized backend is configured."
        }
        return Result.success(reply)
    }
}

class HybridAiService(
    private val settingsStore: SettingsStore,
    private val backendService: BackendService,
    private val demoService: AiService,
    private val tokenStore: SecureTokenStore
) : AiService {
    override suspend fun sendMessage(conversationId: String, text: String): Result<String> {
        val settings = settingsStore.state.first()
        if (settings.demoMode || settings.backendUrl.isBlank()) return demoService.sendMessage(conversationId, text)
        return backendService.sendChat(settings.backendUrl, tokenStore.readDeviceId(), tokenStore.readToken(), conversationId, text)
    }
}

data class BackendHealth(val status: ConnectionStatus, val detail: String = "")

class HttpBackendService : BackendService {
    override suspend fun checkHealth(baseUrl: String, deviceId: String?, token: String?): ConnectionStatus = withContext(Dispatchers.IO) {
        if (!isValidBaseUrl(baseUrl)) return@withContext ConnectionStatus.UNKNOWN
        val health = request(baseUrl, "/health", deviceId = null, token = null, method = "GET")
        if (health == null) return@withContext ConnectionStatus.OFFLINE
        if (health.first == 401) return@withContext ConnectionStatus.AUTHENTICATION_REQUIRED
        if (health.first == 403) return@withContext ConnectionStatus.BLOCKED
        if (health.first !in 200..299) return@withContext ConnectionStatus.OFFLINE
        if (deviceId.isNullOrBlank() || token.isNullOrBlank()) return@withContext ConnectionStatus.AUTHENTICATION_REQUIRED
        val auth = request(baseUrl, "/api/auth/status", deviceId, token, "GET")
        when {
            auth == null -> ConnectionStatus.OFFLINE
            auth.first in 200..299 -> ConnectionStatus.ONLINE
            auth.first == 401 -> ConnectionStatus.AUTHENTICATION_REQUIRED
            auth.first == 403 -> ConnectionStatus.BLOCKED
            else -> ConnectionStatus.OFFLINE
        }
    }

    override suspend fun sendChat(
        baseUrl: String,
        deviceId: String?,
        token: String?,
        conversationId: String,
        text: String
    ): Result<String> = withContext(Dispatchers.IO) {
        if (!isValidBaseUrl(baseUrl)) return@withContext Result.failure(IllegalArgumentException("A valid HTTPS backend URL is required."))
        runCatching {
            val connection = open(baseUrl, "/api/chat", deviceId, token, "POST")
            try {
                connection.doOutput = true
                val payload = JSONObject()
                    .put("conversation_id", conversationId)
                    .put("message", text)
                    .toString()
                connection.outputStream.use { it.write(payload.toByteArray(Charsets.UTF_8)) }
                val responseText = (if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream)
                    ?.bufferedReader()
                    ?.use { it.readText() }
                    .orEmpty()
                if (connection.responseCode !in 200..299) error(parseBackendError(responseText, connection.responseCode))
                val response = JSONObject(responseText)
                response.optString("reply").ifBlank { response.optString("message") }.ifBlank {
                    error("The configured backend did not return a chat reply.")
                }
            } finally {
                connection.disconnect()
            }
        }
    }

    override suspend fun fetchDevices(
        baseUrl: String,
        deviceId: String?,
        token: String?
    ): Result<List<DeviceInfo>> = withContext(Dispatchers.IO) {
        if (!isValidBaseUrl(baseUrl)) return@withContext Result.failure(IllegalArgumentException("A valid HTTPS backend URL is required."))
        runCatching {
            val response = request(baseUrl, "/api/devices", deviceId, token, "GET")
                ?: error("The backend could not be reached.")
            if (response.first !in 200..299) error(parseBackendError(response.second, response.first))
            val array = JSONObject(response.second).optJSONArray("devices")
                ?: error("The configured backend did not return a device list.")
            buildList {
                for (index in 0 until array.length()) {
                    val item = array.optJSONObject(index) ?: continue
                    val status = when (item.optString("status").lowercase(Locale.ROOT)) {
                        "online" -> ConnectionStatus.ONLINE
                        "blocked" -> ConnectionStatus.BLOCKED
                        "offline" -> ConnectionStatus.OFFLINE
                        else -> ConnectionStatus.UNKNOWN
                    }
                    add(
                        DeviceInfo(
                            id = item.optString("device_id"),
                            name = item.optString("name").ifBlank { "Registered device" },
                            kind = if (item.optString("name").contains("windows", ignoreCase = true)) "pc" else "device",
                            status = status,
                            lastActivity = item.optDouble("last_seen", Double.NaN).takeUnless { it.isNaN() }?.times(1000)?.toLong(),
                            paired = item.optBoolean("authenticated", false),
                            detail = "Backend reported ${item.optString("status", "unknown")}"
                        )
                    )
                }
            }
        }
    }

    override suspend fun fetchSecurityEvents(
        baseUrl: String,
        deviceId: String?,
        token: String?
    ): Result<List<SecurityEvent>> = withContext(Dispatchers.IO) {
        if (!isValidBaseUrl(baseUrl)) return@withContext Result.failure(IllegalArgumentException("A valid HTTPS backend URL is required."))
        runCatching {
            val response = request(baseUrl, "/api/security/events", deviceId, token, "GET")
                ?: error("The backend could not be reached.")
            if (response.first !in 200..299) error(parseBackendError(response.second, response.first))
            val array = JSONObject(response.second).optJSONArray("events")
                ?: error("The configured backend did not return security events.")
            buildList {
                for (index in 0 until array.length()) {
                    val item = array.optJSONObject(index) ?: continue
                    add(
                        SecurityEvent(
                            id = item.optString("id", UUID.randomUUID().toString()),
                            type = item.optString("event", "Backend event"),
                            device = item.optString("source", "Backend"),
                            result = item.optString("detail", "Observed by backend"),
                            timestamp = item.optDouble("ts", Double.NaN).takeUnless { it.isNaN() }?.times(1000)?.toLong()
                                ?: System.currentTimeMillis()
                        )
                    )
                }
            }
        }
    }

    private fun request(baseUrl: String, path: String, deviceId: String?, token: String?, method: String): Pair<Int, String>? = runCatching {
        val connection = open(baseUrl, path, deviceId, token, method)
        try {
            val body = (if (connection.responseCode in 200..299) connection.inputStream else connection.errorStream)
                ?.bufferedReader()?.use { it.readText() }.orEmpty()
            connection.responseCode to body
        } finally {
            connection.disconnect()
        }
    }.getOrNull()

    private fun parseBackendError(body: String, statusCode: Int): String = runCatching {
        val error = JSONObject(body).optJSONObject("error")
        error?.optString("message")?.takeIf { it.isNotBlank() }
    }.getOrNull() ?: when (statusCode) {
        401 -> "Authentication is required."
        403 -> "This session is blocked by the backend."
        429 -> "The backend rate limit was reached. Try again later."
        502, 503 -> "The backend or AI provider is unavailable."
        504 -> "The AI provider timed out. Try again later."
        else -> "The backend returned HTTP $statusCode."
    }

    private fun open(baseUrl: String, path: String, deviceId: String?, token: String?, method: String): HttpURLConnection {
        val url = URI.create(baseUrl.trimEnd('/') + path).toURL()
        return (url.openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 8_000
            readTimeout = 12_000
            useCaches = false
            setRequestProperty("Accept", "application/json")
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("X-Request-ID", UUID.randomUUID().toString())
            if (!deviceId.isNullOrBlank()) setRequestProperty("X-Device-ID", deviceId)
            if (!token.isNullOrBlank()) setRequestProperty("X-API-Key", token)
        }
    }

    private fun isValidBaseUrl(value: String): Boolean = runCatching {
        val uri = URI.create(value.trim())
        uri.scheme == "https" && !uri.host.isNullOrBlank()
    }.getOrDefault(false)
}

class LocalDeviceService(
    private val context: Context,
    private val settingsStore: SettingsStore,
    private val tokenStore: SecureTokenStore,
    private val backendService: BackendService
) : DeviceService {
    private val _devices = MutableStateFlow(buildDevices())
    override val devices: StateFlow<List<DeviceInfo>> = _devices.asStateFlow()

    override suspend fun refresh() {
        val settings = settingsStore.state.first()
        if (!settings.demoMode && settings.backendUrl.isNotBlank()) {
            backendService.fetchDevices(settings.backendUrl, tokenStore.readDeviceId(), tokenStore.readToken())
                .onSuccess { remoteDevices ->
                    _devices.value = remoteDevices
                    return
                }
        }
        _devices.value = buildDevices()
    }

    private fun buildDevices(): List<DeviceInfo> {
        val packageInfo = runCatching {
            context.packageManager.getPackageInfo(context.packageName, 0)
        }.getOrNull()
        val appVersion = packageInfo?.versionName ?: "unknown"
        return listOf(
            DeviceInfo(
                id = "this-phone",
                name = Build.MODEL.ifBlank { "Android phone" },
                kind = "phone",
                status = ConnectionStatus.ONLINE,
                lastActivity = System.currentTimeMillis(),
                paired = true,
                detail = "Android ${Build.VERSION.RELEASE} · PlayzAI $appVersion"
            ),
            DeviceInfo(
                id = "windows-pc",
                name = "Windows PC",
                kind = "pc",
                status = ConnectionStatus.UNKNOWN,
                lastActivity = null,
                paired = false,
                detail = "PC agent not connected"
            )
        )
    }
}

class LocalSecurityService(
    private val store: SecurityStore,
    private val tokenStore: SecureTokenStore,
    private val settingsStore: SettingsStore,
    private val backendService: BackendService,
    scope: CoroutineScope
) : SecurityService {
    override val state: StateFlow<SecurityState> = store.state.stateIn(
        scope,
        SharingStarted.WhileSubscribed(5_000),
        SecurityState()
    )

    override suspend fun refresh() {
        val settings = settingsStore.state.first()
        if (!settings.demoMode && settings.backendUrl.isNotBlank()) {
            backendService.fetchSecurityEvents(settings.backendUrl, tokenStore.readDeviceId(), tokenStore.readToken())
                .onSuccess { events -> store.replaceEvents(events) }
        }
    }

    override suspend fun enableLockdown() {
        store.setLockdown(true)
        store.addEvent(
            SecurityEvent(UUID.randomUUID().toString(), "Local lockdown enabled", "This phone", "ACTION REQUIRED", System.currentTimeMillis())
        )
    }

    override suspend fun disableLockdown() {
        store.setLockdown(false)
        store.addEvent(
            SecurityEvent(UUID.randomUUID().toString(), "Local lockdown disabled", "This phone", "RE-AUTHENTICATION REQUIRED", System.currentTimeMillis())
        )
    }

    override suspend fun revokeLocalSession() {
        tokenStore.clearToken()
        store.addEvent(
            SecurityEvent(UUID.randomUUID().toString(), "Local session revoked", "This phone", "COMPLETED", System.currentTimeMillis())
        )
    }
}

class UnsupportedMessagingService : MessagingService {
    override suspend fun sendOfficialMessage(message: String): Result<Unit> =
        Result.failure(UnsupportedOperationException("Official messaging is configured by the backend, not the Android client."))
}

class AndroidVoiceService(context: Context) : VoiceService {
    private val appContext = context.applicationContext
    private val _state = MutableStateFlow(VoiceState())
    override val state: StateFlow<VoiceState> = _state.asStateFlow()
    private var recognizer: SpeechRecognizer? = null
    private var textToSpeech: TextToSpeech? = null
    private var ttsReady = false

    init {
        if (SpeechRecognizer.isRecognitionAvailable(appContext)) {
            recognizer = SpeechRecognizer.createSpeechRecognizer(appContext).also { it.setRecognitionListener(listener) }
        }
        textToSpeech = TextToSpeech(appContext) { status ->
            ttsReady = status == TextToSpeech.SUCCESS
        }
    }

    override fun startListening(language: VoiceLanguage) {
        val speechRecognizer = recognizer
        if (speechRecognizer == null) {
            _state.value = _state.value.copy(error = "Speech recognition is not available on this device.")
            return
        }
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, language.localeTag)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, language.localeTag)
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }
        _state.value = VoiceState(isListening = true)
        runCatching { speechRecognizer.startListening(intent) }
            .onFailure { _state.value = VoiceState(error = "Could not start speech recognition.") }
    }

    override fun stopListening() {
        recognizer?.stopListening()
        _state.value = _state.value.copy(isListening = false)
    }

    override fun speak(text: String, language: VoiceLanguage, gender: VoiceGender, speechRate: Float, pitch: Float) {
        val tts = textToSpeech ?: return
        if (!ttsReady) {
            _state.value = _state.value.copy(error = "Text-to-speech is not ready yet.")
            return
        }
        val locale = Locale.forLanguageTag(language.localeTag)
        val result = tts.setLanguage(locale)
        if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
            tts.language = Locale.ENGLISH
        }
        tts.voice = tts.voices
            ?.filter { it.locale.language == locale.language }
            ?.firstOrNull { voice ->
                when (gender) {
                    VoiceGender.MALE -> voice.name.contains("male", ignoreCase = true)
                    VoiceGender.FEMALE -> voice.name.contains("female", ignoreCase = true)
                    VoiceGender.DEFAULT -> true
                }
            } ?: tts.voice
        tts.setSpeechRate(speechRate.coerceIn(0.5f, 2f))
        tts.setPitch(pitch.coerceIn(0.5f, 2f))
        _state.value = _state.value.copy(isSpeaking = true, error = null)
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "playzai-${UUID.randomUUID()}")
    }

    override fun stopSpeaking() {
        textToSpeech?.stop()
        _state.value = _state.value.copy(isSpeaking = false)
    }

    override fun shutdown() {
        recognizer?.destroy()
        textToSpeech?.stop()
        textToSpeech?.shutdown()
        recognizer = null
        textToSpeech = null
    }

    private val listener: RecognitionListener get() = object : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) = Unit
        override fun onBeginningOfSpeech() = Unit
        override fun onRmsChanged(rmsdB: Float) = Unit
        override fun onBufferReceived(buffer: ByteArray?) = Unit
        override fun onEndOfSpeech() { _state.value = _state.value.copy(isListening = false) }
        override fun onError(error: Int) {
            _state.value = _state.value.copy(isListening = false, error = "Speech recognition ended. Try again.")
        }
        override fun onResults(results: Bundle?) {
            val result = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull()
            _state.value = _state.value.copy(isListening = false, partialText = "", recognizedText = result, error = null)
        }
        override fun onPartialResults(partialResults: Bundle?) {
            val result = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()
            _state.value = _state.value.copy(partialText = result)
        }
        override fun onEvent(eventType: Int, params: Bundle?) = Unit
    }
}

class NotificationHelper(private val context: Context) {
    private val channelId = "playzai_security"

    fun notifySecurityEvent(title: String, body: String) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            manager.createNotificationChannel(
                NotificationChannel(channelId, "PlayzAI security", NotificationManager.IMPORTANCE_DEFAULT)
            )
        }
        val notification = NotificationCompat.Builder(context, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .build()
        manager.notify(1001, notification)
    }
}
