package com.playzai.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.playzai.app.ui.PlayzAiApp

class MainActivity : ComponentActivity() {
    private val viewModel: MainViewModel by viewModels {
        val container = (application as PlayzAiApplication).container
        object : ViewModelProvider.Factory {
            @Suppress("UNCHECKED_CAST")
            override fun <T : ViewModel> create(modelClass: Class<T>): T = MainViewModel(
                settingsStore = container.settingsStore,
                conversationStore = container.conversationStore,
                aiService = container.aiService,
                backendService = container.backendService,
                deviceService = container.deviceService,
                securityService = container.securityService,
                tokenStore = container.tokenStore,
                voiceService = container.voiceService
            ) as T
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            PlayzAiApp(viewModel)
        }
    }
}
