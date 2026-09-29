package com.playzai.app.model

import java.util.Locale

enum class InterfaceLanguage(val tag: String) {
    ENGLISH("en"),
    HINDI("hi");

    companion object {
        fun from(value: String?): InterfaceLanguage = entries.firstOrNull { it.name == value } ?: ENGLISH
    }
}

enum class AppThemeMode { SYSTEM, LIGHT, DARK }

enum class VoiceLanguage(val localeTag: String) {
    ENGLISH("en-IN"),
    HINDI("hi-IN"),
    HINGLISH("en-IN")
}

enum class VoiceGender { DEFAULT, MALE, FEMALE }

enum class ConnectionStatus {
    ONLINE, OFFLINE, CONNECTING, AUTHENTICATION_REQUIRED, BLOCKED, UNKNOWN
}

enum class MessageRole { USER, ASSISTANT }

data class ConfirmationPrompt(
    val id: String,
    val action: String,
    val command: String = "",
    val riskLevel: String = "LEVEL 3 — HIGH RISK / HEAVY",
    val riskExplanation: String = "Explicit user confirmation is required."
)

data class SettingsState(
    val interfaceLanguage: InterfaceLanguage = InterfaceLanguage.ENGLISH,
    val theme: AppThemeMode = AppThemeMode.SYSTEM,
    val notificationsEnabled: Boolean = false,
    val speakingLanguage: VoiceLanguage = VoiceLanguage.ENGLISH,
    val voiceEnabled: Boolean = false,
    val voiceGender: VoiceGender = VoiceGender.DEFAULT,
    val speechRate: Float = 1f,
    val pitch: Float = 1f,
    val demoMode: Boolean = true,
    val backendUrl: String = "",
    val selectedProvider: String = "",
    val selectedModel: String = ""
)

data class ChatMessage(
    val id: String,
    val role: MessageRole,
    val text: String,
    val timestamp: Long = System.currentTimeMillis(),
    val providerUsed: String? = null,
    val modelUsed: String? = null,
    val fallbackOccurred: Boolean = false,
    val confirmation: ConfirmationPrompt? = null
)

data class Conversation(
    val id: String,
    val title: String,
    val messages: List<ChatMessage> = emptyList(),
    val updatedAt: Long = System.currentTimeMillis()
)

data class DeviceInfo(
    val id: String,
    val name: String,
    val kind: String,
    val status: ConnectionStatus,
    val lastActivity: Long? = null,
    val paired: Boolean = false,
    val detail: String = ""
)

data class SecurityEvent(
    val id: String,
    val type: String,
    val device: String,
    val result: String,
    val timestamp: Long
)

data class SecurityState(
    val lockdownEnabled: Boolean = false,
    val events: List<SecurityEvent> = emptyList()
) {
    val status: SecurityStatus
        get() = if (lockdownEnabled) SecurityStatus.ACTION_REQUIRED else SecurityStatus.PROTECTED
}

enum class SecurityStatus { PROTECTED, WARNING, ACTION_REQUIRED }

data class VoiceState(
    val isListening: Boolean = false,
    val partialText: String = "",
    val recognizedText: String? = null,
    val isSpeaking: Boolean = false,
    val error: String? = null
)

fun formatTimestamp(timestamp: Long): String {
    val formatter = java.text.SimpleDateFormat("dd MMM, HH:mm", Locale.getDefault())
    return formatter.format(java.util.Date(timestamp))
}
