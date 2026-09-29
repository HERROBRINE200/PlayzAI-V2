package com.playzai.app.data

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.playzai.app.model.SecurityEvent
import com.playzai.app.model.SecurityState
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException

private val Context.securityDataStore by preferencesDataStore(name = "playzai_security")

class SecurityStore(private val context: Context) {
    private val lockdownKey = booleanPreferencesKey("lockdown_enabled")
    private val eventsKey = stringPreferencesKey("events_json")

    val state: Flow<SecurityState> = context.securityDataStore.data
        .catch { error ->
            if (error is IOException) emit(emptyPreferences()) else throw error
        }
        .map { preferences ->
            SecurityState(
                lockdownEnabled = preferences[lockdownKey] ?: false,
                events = decode(preferences[eventsKey].orEmpty())
            )
        }

    suspend fun setLockdown(enabled: Boolean) {
        context.securityDataStore.edit { it[lockdownKey] = enabled }
    }

    suspend fun addEvent(event: SecurityEvent) {
        context.securityDataStore.edit { preferences ->
            val events = decode(preferences[eventsKey].orEmpty()).toMutableList()
            events.add(0, event)
            preferences[eventsKey] = encode(events.take(100))
        }
    }

    suspend fun replaceEvents(events: List<SecurityEvent>) {
        context.securityDataStore.edit { preferences ->
            preferences[eventsKey] = encode(events.take(100))
        }
    }

    private fun encode(events: List<SecurityEvent>): String = JSONArray().apply {
        events.forEach { event ->
            put(
                JSONObject()
                    .put("id", event.id)
                    .put("type", event.type)
                    .put("device", event.device)
                    .put("result", event.result)
                    .put("timestamp", event.timestamp)
            )
        }
    }.toString()

    private fun decode(raw: String): List<SecurityEvent> = runCatching {
        if (raw.isBlank()) return emptyList()
        val array = JSONArray(raw)
        buildList {
            for (index in 0 until array.length()) {
                val event = array.getJSONObject(index)
                add(
                    SecurityEvent(
                        id = event.optString("id"),
                        type = event.optString("type"),
                        device = event.optString("device"),
                        result = event.optString("result"),
                        timestamp = event.optLong("timestamp", System.currentTimeMillis())
                    )
                )
            }
        }
    }.getOrDefault(emptyList())
}
