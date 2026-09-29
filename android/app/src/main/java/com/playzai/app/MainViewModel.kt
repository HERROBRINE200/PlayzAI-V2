package com.playzai.app

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.playzai.app.data.ConversationStore
import com.playzai.app.data.SecureTokenStore
import com.playzai.app.data.SettingsStore
import com.playzai.app.model.AppThemeMode
import com.playzai.app.model.ChatMessage
import com.playzai.app.model.Conversation
import com.playzai.app.model.InterfaceLanguage
import com.playzai.app.model.MessageRole
import com.playzai.app.model.SecurityState
import com.playzai.app.model.SettingsState
import com.playzai.app.model.VoiceGender
import com.playzai.app.model.VoiceLanguage
import com.playzai.app.services.AiService
import com.playzai.app.services.BackendService
import com.playzai.app.services.DeviceService
import com.playzai.app.services.SecurityService
import com.playzai.app.services.VoiceService
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import java.util.UUID

class MainViewModel(
    private val settingsStore: SettingsStore,
    private val conversationStore: ConversationStore,
    private val aiService: AiService,
    private val backendService: BackendService,
    private val deviceService: DeviceService,
    private val securityService: SecurityService,
    private val tokenStore: SecureTokenStore,
    val voiceService: VoiceService
) : ViewModel() {
    val settings: StateFlow<SettingsState> = settingsStore.state.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        SettingsState()
    )
    val conversations: StateFlow<List<Conversation>> = conversationStore.conversations.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        emptyList()
    )
    val devices = deviceService.devices.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), emptyList())
    val security: StateFlow<SecurityState> = securityService.state
    val selectedConversationId = MutableStateFlow<String?>(null)
    val isGenerating = MutableStateFlow(false)
    val errorMessage = MutableStateFlow<String?>(null)
    val backendStatus = MutableStateFlow(com.playzai.app.model.ConnectionStatus.UNKNOWN)
    val authDeviceId = MutableStateFlow(tokenStore.readDeviceId().orEmpty())
    val hasBackendApiKey = MutableStateFlow(!tokenStore.readToken().isNullOrBlank())

    private val conversationMutex = Mutex()
    private var generationJob: Job? = null
    private var lastFailedText: String? = null
    private var voiceSubmissionInFlight = false

    init {
        viewModelScope.launch {
            val existing = conversations.first()
            if (existing.isEmpty()) selectedConversationId.value = createConversationInternal().id
            else if (selectedConversationId.value == null) selectedConversationId.value = existing.first().id
        }
    }

    fun selectConversation(id: String) {
        selectedConversationId.value = id
        errorMessage.value = null
    }

    fun newConversation() {
        viewModelScope.launch {
            val conversation = createConversationInternal()
            selectedConversationId.value = conversation.id
            errorMessage.value = null
        }
    }

    fun renameConversation(id: String, title: String) {
        val cleanTitle = title.trim().ifBlank { "Conversation" }.take(60)
        viewModelScope.launch { updateConversation(id) { it.copy(title = cleanTitle) } }
    }

    fun deleteConversation(id: String) {
        viewModelScope.launch {
            conversationMutex.withLock {
                val current = conversationStore.conversations.first()
                val remaining = current.filterNot { it.id == id }
                if (remaining.isEmpty()) {
                    val replacement = newConversationModel()
                    conversationStore.saveAll(listOf(replacement))
                    selectedConversationId.value = replacement.id
                } else {
                    conversationStore.saveAll(remaining)
                    if (selectedConversationId.value == id) selectedConversationId.value = remaining.first().id
                }
            }
        }
    }

    fun clearConversation(id: String) {
        viewModelScope.launch { updateConversation(id) { it.copy(messages = emptyList()) } }
    }

    fun clearAllConversations() {
        viewModelScope.launch {
            val replacement = newConversationModel()
            conversationStore.saveAll(listOf(replacement))
            selectedConversationId.value = replacement.id
            errorMessage.value = null
        }
    }

    fun sendMessage(text: String) {
        sendMessageInternal(text, addUserMessage = true)
    }

    fun sendVoiceMessage(text: String) {
        val trimmed = text.trim()
        if (trimmed.isBlank() || isGenerating.value || voiceSubmissionInFlight || selectedConversationId.value == null) return
        voiceSubmissionInFlight = true
        sendMessageInternal(trimmed, addUserMessage = true, fromVoice = true)
    }

    fun retryLastMessage() {
        lastFailedText?.let { sendMessageInternal(it, addUserMessage = false) }
    }

    private fun sendMessageInternal(text: String, addUserMessage: Boolean, fromVoice: Boolean = false) {
        val trimmed = text.trim()
        if (trimmed.isBlank() || isGenerating.value) return
        val conversationId = selectedConversationId.value ?: return
        errorMessage.value = null
        lastFailedText = trimmed
        generationJob?.cancel()
        generationJob = viewModelScope.launch {
            isGenerating.value = true
            try {
                if (addUserMessage) {
                    updateConversation(conversationId) { conversation ->
                        conversation.copy(
                            title = if (conversation.messages.isEmpty()) trimmed.take(40) else conversation.title,
                            messages = conversation.messages + ChatMessage(UUID.randomUUID().toString(), MessageRole.USER, trimmed)
                        )
                    }
                }
                val result = aiService.sendMessage(conversationId, trimmed)
                result.fold(
                    onSuccess = { reply ->
                        updateConversation(conversationId) { conversation ->
                            conversation.copy(
                                messages = conversation.messages + ChatMessage(UUID.randomUUID().toString(), MessageRole.ASSISTANT, reply)
                            )
                        }
                        lastFailedText = null
                    },
                    onFailure = { failure ->
                        errorMessage.value = failure.message?.takeIf { it.isNotBlank() } ?: "The response could not be generated."
                    }
                )
            } catch (cancelled: kotlinx.coroutines.CancellationException) {
                throw cancelled
            } catch (_: Exception) {
                errorMessage.value = "The response could not be generated."
            } finally {
                isGenerating.value = false
                if (fromVoice) voiceSubmissionInFlight = false
            }
        }
    }

    fun stopGeneration() {
        generationJob?.cancel()
        generationJob = null
        voiceSubmissionInFlight = false
        isGenerating.value = false
    }

    fun setInterfaceLanguage(value: InterfaceLanguage) = viewModelScope.launch { settingsStore.setInterfaceLanguage(value) }
    fun setTheme(value: AppThemeMode) = viewModelScope.launch { settingsStore.setTheme(value) }
    fun setNotificationsEnabled(value: Boolean) = viewModelScope.launch { settingsStore.setNotificationsEnabled(value) }
    fun setSpeakingLanguage(value: VoiceLanguage) = viewModelScope.launch { settingsStore.setSpeakingLanguage(value) }
    fun setVoiceEnabled(value: Boolean) = viewModelScope.launch { settingsStore.setVoiceEnabled(value) }
    fun setVoiceGender(value: VoiceGender) = viewModelScope.launch { settingsStore.setVoiceGender(value) }
    fun setSpeechRate(value: Float) = viewModelScope.launch { settingsStore.setSpeechRate(value) }
    fun setPitch(value: Float) = viewModelScope.launch { settingsStore.setPitch(value) }
    fun setDemoMode(value: Boolean) = viewModelScope.launch { settingsStore.setDemoMode(value) }
    fun setBackendUrl(value: String) = viewModelScope.launch { settingsStore.setBackendUrl(value) }

    fun saveBackendConnection(url: String, deviceId: String, apiKey: String) {
        viewModelScope.launch {
            settingsStore.setBackendUrl(url)
            tokenStore.saveDeviceId(deviceId)
            if (apiKey.isNotBlank()) tokenStore.saveToken(apiKey)
            authDeviceId.value = deviceId.trim()
            hasBackendApiKey.value = !tokenStore.readToken().isNullOrBlank()
            refreshBackendStatusNow()
        }
    }

    fun refreshDevices() = viewModelScope.launch { deviceService.refresh() }

    fun refreshBackendStatus() {
        viewModelScope.launch { refreshBackendStatusNow() }
    }

    private suspend fun refreshBackendStatusNow() {
        val current = settingsStore.state.first()
        if (current.demoMode || current.backendUrl.isBlank()) {
            backendStatus.value = com.playzai.app.model.ConnectionStatus.UNKNOWN
            return
        }
        backendStatus.value = com.playzai.app.model.ConnectionStatus.CONNECTING
        backendStatus.value = backendService.checkHealth(current.backendUrl, tokenStore.readDeviceId(), tokenStore.readToken())
    }

    fun refreshSecurity() = viewModelScope.launch { securityService.refresh() }
    fun enableLockdown() = viewModelScope.launch { securityService.enableLockdown() }
    fun disableLockdown() = viewModelScope.launch { securityService.disableLockdown() }
    fun revokeLocalSession() = viewModelScope.launch {
        securityService.revokeLocalSession()
        hasBackendApiKey.value = false
    }

    private suspend fun createConversationInternal(): Conversation {
        val conversation = newConversationModel()
        conversationMutex.withLock {
            val current = conversationStore.conversations.first()
            conversationStore.saveAll(listOf(conversation) + current)
        }
        return conversation
    }

    private suspend fun updateConversation(id: String, transform: (Conversation) -> Conversation) {
        conversationMutex.withLock {
            val current = conversationStore.conversations.first()
            val updated = current.map { if (it.id == id) transform(it).copy(updatedAt = System.currentTimeMillis()) else it }
            conversationStore.saveAll(updated.sortedByDescending { it.updatedAt })
        }
    }

    private fun newConversationModel() = Conversation(
        id = UUID.randomUUID().toString(),
        title = "Conversation",
        messages = emptyList()
    )

    override fun onCleared() {
        generationJob?.cancel()
        super.onCleared()
    }
}
