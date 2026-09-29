package com.playzai.app

import com.playzai.app.model.ConnectionStatus
import com.playzai.app.model.DeviceInfo
import com.playzai.app.model.InterfaceLanguage
import com.playzai.app.model.MessageRole
import com.playzai.app.model.SecurityState
import com.playzai.app.model.SettingsState
import com.playzai.app.model.VoiceLanguage
import com.playzai.app.services.DemoAiService
import com.playzai.app.services.HttpBackendService
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PlayzAiModelsTest {
    @Test
    fun languageSelectionUsesStableLocaleTags() {
        assertEquals("en", InterfaceLanguage.ENGLISH.tag)
        assertEquals("hi", InterfaceLanguage.HINDI.tag)
        assertEquals("hi-IN", VoiceLanguage.HINDI.localeTag)
    }

    @Test
    fun settingsDefaultToSafeDemoMode() {
        val settings = SettingsState()
        assertTrue(settings.demoMode)
        assertFalse(settings.voiceEnabled)
        assertEquals("", settings.backendUrl)
    }

    @Test
    fun securityStateRequiresActionOnlyDuringLockdown() {
        assertEquals(com.playzai.app.model.SecurityStatus.PROTECTED, SecurityState().status)
        assertTrue(SecurityState(lockdownEnabled = true).status == com.playzai.app.model.SecurityStatus.ACTION_REQUIRED)
    }

    @Test
    fun deviceAndConnectionStatesDoNotPretendPcIsOnline() {
        val pc = DeviceInfo("pc", "Windows PC", "pc", ConnectionStatus.UNKNOWN, paired = false)
        assertEquals(ConnectionStatus.UNKNOWN, pc.status)
        assertFalse(pc.paired)
        assertTrue(ConnectionStatus.OFFLINE != ConnectionStatus.ONLINE)
        assertEquals(MessageRole.USER, MessageRole.valueOf("USER"))
    }

    @Test
    fun demoChatProducesAnExplicitLocalResponse() = runBlocking {
        val result = DemoAiService().sendMessage("conversation", "Hello PlayzAI")
        assertTrue(result.isSuccess)
        assertTrue(result.getOrThrow().contains("Demo Mode"))
    }

    @Test
    fun invalidBackendConfigurationReturnsSafeFailure() = runBlocking {
        val result = HttpBackendService().sendChat("not-a-url", null, null, "conversation", "hello")
        assertTrue(result.isFailure)
    }
}
