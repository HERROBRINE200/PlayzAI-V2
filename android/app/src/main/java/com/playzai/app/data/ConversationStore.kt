package com.playzai.app.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.playzai.app.model.ChatMessage
import com.playzai.app.model.Conversation
import com.playzai.app.model.MessageRole
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException

private val Context.conversationsDataStore by preferencesDataStore(name = "playzai_conversations")

class ConversationStore(private val context: Context) {
    private val conversationsKey = stringPreferencesKey("conversations_json")

    val conversations: Flow<List<Conversation>> = context.conversationsDataStore.data
        .catch { error ->
            if (error is IOException) emit(emptyPreferences()) else throw error
        }
        .map { decode(it[conversationsKey].orEmpty()) }

    suspend fun saveAll(value: List<Conversation>) {
        context.conversationsDataStore.edit { preferences ->
            preferences[conversationsKey] = encode(value)
        }
    }

    private fun encode(conversations: List<Conversation>): String {
        val array = JSONArray()
        conversations.forEach { conversation ->
            val item = JSONObject()
                .put("id", conversation.id)
                .put("title", conversation.title)
                .put("updatedAt", conversation.updatedAt)
            val messages = JSONArray()
            conversation.messages.forEach { message ->
                messages.put(
                    JSONObject()
                        .put("id", message.id)
                        .put("role", message.role.name)
                        .put("text", message.text)
                        .put("timestamp", message.timestamp)
                )
            }
            item.put("messages", messages)
            array.put(item)
        }
        return array.toString()
    }

    private fun decode(raw: String): List<Conversation> = runCatching {
        if (raw.isBlank()) return emptyList()
        val array = JSONArray(raw)
        buildList {
            for (i in 0 until array.length()) {
                val item = array.getJSONObject(i)
                val messagesJson = item.optJSONArray("messages") ?: JSONArray()
                val messages = buildList {
                    for (j in 0 until messagesJson.length()) {
                        val message = messagesJson.getJSONObject(j)
                        add(
                            ChatMessage(
                                id = message.optString("id"),
                                role = runCatching { MessageRole.valueOf(message.optString("role")) }.getOrDefault(MessageRole.ASSISTANT),
                                text = message.optString("text"),
                                timestamp = message.optLong("timestamp", System.currentTimeMillis())
                            )
                        )
                    }
                }
                add(
                    Conversation(
                        id = item.optString("id"),
                        title = item.optString("title", "Conversation"),
                        messages = messages,
                        updatedAt = item.optLong("updatedAt", System.currentTimeMillis())
                    )
                )
            }
        }.filter { it.id.isNotBlank() }
    }.getOrDefault(emptyList())
}
