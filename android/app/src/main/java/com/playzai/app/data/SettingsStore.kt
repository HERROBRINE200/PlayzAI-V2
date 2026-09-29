package com.playzai.app.data

import android.content.Context
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.playzai.app.BuildConfig
import com.playzai.app.model.AppThemeMode
import com.playzai.app.model.InterfaceLanguage
import com.playzai.app.model.SettingsState
import com.playzai.app.model.VoiceGender
import com.playzai.app.model.VoiceLanguage
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import java.io.IOException

private val Context.settingsDataStore by preferencesDataStore(name = "playzai_preferences")

class SettingsStore(private val context: Context) {
    private object Keys {
        val interfaceLanguage = stringPreferencesKey("interface_language")
        val theme = stringPreferencesKey("theme")
        val notifications = booleanPreferencesKey("notifications")
        val speakingLanguage = stringPreferencesKey("speaking_language")
        val voiceEnabled = booleanPreferencesKey("voice_enabled")
        val voiceGender = stringPreferencesKey("voice_gender")
        val speechRate = floatPreferencesKey("speech_rate")
        val pitch = floatPreferencesKey("pitch")
        val demoMode = booleanPreferencesKey("demo_mode")
        val backendUrl = stringPreferencesKey("backend_url")
    }

    val state: Flow<SettingsState> = context.settingsDataStore.data
        .catch { error ->
            if (error is IOException) emit(androidx.datastore.preferences.core.emptyPreferences()) else throw error
        }
        .map { preferences -> preferences.toSettings() }
        .distinctUntilChanged()

    suspend fun setInterfaceLanguage(value: InterfaceLanguage) = update { it[Keys.interfaceLanguage] = value.name }
    suspend fun setTheme(value: AppThemeMode) = update { it[Keys.theme] = value.name }
    suspend fun setNotificationsEnabled(value: Boolean) = update { it[Keys.notifications] = value }
    suspend fun setSpeakingLanguage(value: VoiceLanguage) = update { it[Keys.speakingLanguage] = value.name }
    suspend fun setVoiceEnabled(value: Boolean) = update { it[Keys.voiceEnabled] = value }
    suspend fun setVoiceGender(value: VoiceGender) = update { it[Keys.voiceGender] = value.name }
    suspend fun setSpeechRate(value: Float) = update { it[Keys.speechRate] = value.coerceIn(0.5f, 2f) }
    suspend fun setPitch(value: Float) = update { it[Keys.pitch] = value.coerceIn(0.5f, 2f) }
    suspend fun setDemoMode(value: Boolean) = update { it[Keys.demoMode] = value }
    suspend fun setBackendUrl(value: String) = update { it[Keys.backendUrl] = value.trim() }

    suspend fun update(transform: suspend (androidx.datastore.preferences.core.MutablePreferences) -> Unit) {
        context.settingsDataStore.edit(transform)
    }

    private fun Preferences.toSettings(): SettingsState = SettingsState(
        interfaceLanguage = InterfaceLanguage.from(this[Keys.interfaceLanguage]),
        theme = runCatching { AppThemeMode.valueOf(this[Keys.theme] ?: AppThemeMode.SYSTEM.name) }.getOrDefault(AppThemeMode.SYSTEM),
        notificationsEnabled = this[Keys.notifications] ?: false,
        speakingLanguage = runCatching { VoiceLanguage.valueOf(this[Keys.speakingLanguage] ?: VoiceLanguage.ENGLISH.name) }.getOrDefault(VoiceLanguage.ENGLISH),
        voiceEnabled = this[Keys.voiceEnabled] ?: false,
        voiceGender = runCatching { VoiceGender.valueOf(this[Keys.voiceGender] ?: VoiceGender.DEFAULT.name) }.getOrDefault(VoiceGender.DEFAULT),
        speechRate = (this[Keys.speechRate] ?: 1f).coerceIn(0.5f, 2f),
        pitch = (this[Keys.pitch] ?: 1f).coerceIn(0.5f, 2f),
        demoMode = this[Keys.demoMode] ?: true,
        backendUrl = this[Keys.backendUrl] ?: BuildConfig.BACKEND_BASE_URL
    )
}
