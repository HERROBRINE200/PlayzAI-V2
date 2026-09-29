package com.playzai.app

import android.app.Application
import com.playzai.app.data.ConversationStore
import com.playzai.app.data.SecurityStore
import com.playzai.app.data.SecureTokenStore
import com.playzai.app.data.SettingsStore
import com.playzai.app.services.AndroidVoiceService
import com.playzai.app.services.DemoAiService
import com.playzai.app.services.HttpBackendService
import com.playzai.app.services.HybridAiService
import com.playzai.app.services.LocalDeviceService
import com.playzai.app.services.LocalSecurityService
import com.playzai.app.services.MessagingService
import com.playzai.app.services.SecurityService
import com.playzai.app.services.UnsupportedMessagingService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

class PlayzAiApplication : Application() {
    val container: AppContainer by lazy { AppContainer(this) }

    override fun onTerminate() {
        container.voiceService.shutdown()
        super.onTerminate()
    }
}

class AppContainer(application: Application) {
    private val appScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    val settingsStore = SettingsStore(application)
    val conversationStore = ConversationStore(application)
    val securityStore = SecurityStore(application)
    val tokenStore = SecureTokenStore(application)
    val backendService = HttpBackendService()
    val aiService = HybridAiService(settingsStore, backendService, DemoAiService(), tokenStore)
    val deviceService = LocalDeviceService(application, settingsStore, tokenStore, backendService)
    val securityService: SecurityService = LocalSecurityService(securityStore, tokenStore, settingsStore, backendService, appScope)
    val voiceService = AndroidVoiceService(application)
    val messagingService: MessagingService = UnsupportedMessagingService()
}
