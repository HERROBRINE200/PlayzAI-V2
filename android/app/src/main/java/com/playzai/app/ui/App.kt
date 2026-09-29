package com.playzai.app.ui

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateContentSize
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.automirrored.filled.VolumeUp
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.Devices
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Badge
import androidx.compose.material3.BottomAppBar
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardColors
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.playzai.app.BuildConfig
import com.playzai.app.MainViewModel
import com.playzai.app.R
import com.playzai.app.model.AppThemeMode
import com.playzai.app.model.ChatMessage
import com.playzai.app.model.ConnectionStatus
import com.playzai.app.model.Conversation
import com.playzai.app.model.DeviceInfo
import com.playzai.app.model.InterfaceLanguage
import com.playzai.app.model.MessageRole
import com.playzai.app.model.SecurityEvent
import com.playzai.app.model.SecurityStatus
import com.playzai.app.model.SettingsState
import com.playzai.app.model.VoiceGender
import com.playzai.app.model.VoiceLanguage
import com.playzai.app.model.formatTimestamp
import com.playzai.app.services.NotificationHelper
import kotlinx.coroutines.launch
import java.util.Locale
import kotlin.math.roundToInt

private val LocalAppLanguage = staticCompositionLocalOf { InterfaceLanguage.ENGLISH }

@Composable
private fun appString(id: Int): String {
    val context = LocalContext.current
    val language = LocalAppLanguage.current
    return remember(id, language) {
        val configuration = android.content.res.Configuration(context.resources.configuration)
        configuration.setLocale(Locale.forLanguageTag(language.tag))
        context.createConfigurationContext(configuration).resources.getString(id)
    }
}

@Composable
private fun AppText(id: Int, modifier: Modifier = Modifier, style: androidx.compose.ui.text.TextStyle = MaterialTheme.typography.bodyLarge, fontWeight: FontWeight? = null) {
    Text(appString(id), modifier = modifier, style = style, fontWeight = fontWeight)
}

private data class Destination(val route: String, val labelId: Int, val icon: androidx.compose.ui.graphics.vector.ImageVector)

private val destinations = listOf(
    Destination("home", R.string.home, Icons.Default.Home),
    Destination("devices", R.string.devices, Icons.Default.Devices),
    Destination("security", R.string.security, Icons.Default.Shield),
    Destination("settings", R.string.settings, Icons.Default.Settings)
)

@Composable
fun PlayzAiApp(viewModel: MainViewModel) {
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    val navController = rememberNavController()
    val currentEntry by navController.currentBackStackEntryAsState()
    val currentRoute = currentEntry?.destination?.route ?: "home"

    PlayzAiTheme(settings.theme) {
        CompositionLocalProvider(LocalAppLanguage provides settings.interfaceLanguage) {
            Scaffold(
                contentWindowInsets = WindowInsets.navigationBars,
                bottomBar = {
                    ClayNavigationBar {
                        destinations.forEach { destination ->
                            ClayNavigationItem(
                                selected = currentRoute == destination.route,
                                labelId = destination.labelId,
                                icon = destination.icon,
                                onClick = {
                                    navController.navigate(destination.route) {
                                        popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                        launchSingleTop = true
                                        restoreState = true
                                    }
                                }
                            )
                        }
                    }
                }
            ) { padding ->
                NavHost(
                    navController = navController,
                    startDestination = "home",
                    modifier = Modifier.padding(padding)
                ) {
                    composable("home") { HomeScreen(viewModel) }
                    composable("devices") { DevicesScreen(viewModel) }
                    composable("security") { SecurityScreen(viewModel) }
                    composable("settings") { SettingsScreen(viewModel) }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun HomeScreen(viewModel: MainViewModel) {
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    val conversations by viewModel.conversations.collectAsStateWithLifecycle()
    val selectedId by viewModel.selectedConversationId.collectAsStateWithLifecycle()
    val isGenerating by viewModel.isGenerating.collectAsStateWithLifecycle()
    val error by viewModel.errorMessage.collectAsStateWithLifecycle()
    val voice by viewModel.voiceService.state.collectAsStateWithLifecycle()
    val backendStatus by viewModel.backendStatus.collectAsStateWithLifecycle()
    val selected = conversations.firstOrNull { it.id == selectedId } ?: conversations.firstOrNull()
    val listState = rememberLazyListState()
    val snackbarHostState = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val clipboard = LocalClipboardManager.current
    val context = LocalContext.current
    val microphoneDeniedText = appString(R.string.microphone_denied)
    val newConversationDescription = appString(R.string.new_conversation)
    val copiedText = appString(R.string.copied)
    var input by rememberSaveable { mutableStateOf("") }
    var showClearDialog by remember { mutableStateOf(false) }
    var showClearAllDialog by remember { mutableStateOf(false) }
    var showMicrophoneDialog by remember { mutableStateOf(false) }
    var showNewNameDialog by remember { mutableStateOf<String?>(null) }
    var showConversationMenu by remember { mutableStateOf(false) }

    val requestMicrophone = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) viewModel.voiceService.startListening(settings.speakingLanguage)
        else scope.launch { snackbarHostState.showSnackbar(microphoneDeniedText) }
    }

    LaunchedEffect(voice.recognizedText) {
        val transcript = voice.recognizedText?.trim().orEmpty()
        if (transcript.isNotBlank()) {
            input = ""
            viewModel.sendVoiceMessage(transcript)
        }
    }
    LaunchedEffect(voice.error) {
        voice.error?.takeIf { it.isNotBlank() }?.let { snackbarHostState.showSnackbar(it) }
    }
    LaunchedEffect(selected?.id, selected?.messages?.size, isGenerating) {
        if (selected != null && selected.messages.isNotEmpty()) {
            listState.animateScrollToItem(selected.messages.lastIndex)
        }
    }
    LaunchedEffect(selected?.messages?.lastOrNull()?.id, settings.voiceEnabled) {
        val last = selected?.messages?.lastOrNull()
        if (settings.voiceEnabled && last?.role == MessageRole.ASSISTANT) {
            viewModel.voiceService.speak(last.text, settings.speakingLanguage, settings.voiceGender, settings.speechRate, settings.pitch)
        }
    }

    Box(Modifier.fillMaxSize().imePadding()) {
        Column(Modifier.fillMaxSize()) {
            TopAppBar(
                title = {
                    Column {
                        Text(appString(R.string.app_name), fontWeight = FontWeight.Bold)
                        Text(
                            appString(if (settings.demoMode) R.string.demo_offline else R.string.backend_status),
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.primary
                        )
                    }
                },
                modifier = Modifier
                    .padding(horizontal = 8.dp, vertical = 4.dp)
                    .shadow(8.dp, RoundedCornerShape(22.dp), clip = false, ambientColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.12f), spotColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.2f))
                    .clip(RoundedCornerShape(22.dp)),
                actions = {
                    IconButton(onClick = viewModel::newConversation, modifier = Modifier.semantics { contentDescription = newConversationDescription }) {
                        Icon(Icons.Default.Add, contentDescription = null)
                    }
                    if (selected != null) {
                        Box {
                            IconButton(onClick = { showConversationMenu = true }) { Icon(Icons.Default.MoreVert, contentDescription = null) }
                            DropdownMenu(expanded = showConversationMenu, onDismissRequest = { showConversationMenu = false }) {
                                DropdownMenuItem(
                                    text = { AppText(R.string.rename) },
                                    onClick = { showConversationMenu = false; showNewNameDialog = selected.id },
                                    leadingIcon = { Icon(Icons.Default.Edit, contentDescription = null) }
                                )
                                DropdownMenuItem(
                                    text = { AppText(R.string.clear_conversation) },
                                    onClick = { showConversationMenu = false; showClearDialog = true },
                                    leadingIcon = { Icon(Icons.Default.Clear, contentDescription = null) }
                                )
                                DropdownMenuItem(
                                    text = { AppText(R.string.delete) },
                                    onClick = { showConversationMenu = false; viewModel.deleteConversation(selected.id) },
                                    leadingIcon = { Icon(Icons.Default.DeleteOutline, contentDescription = null) }
                                )
                                DropdownMenuItem(
                                    text = { AppText(R.string.clear_all) },
                                    onClick = { showConversationMenu = false; showClearAllDialog = true },
                                    leadingIcon = { Icon(Icons.Default.DeleteOutline, contentDescription = null) }
                                )
                            }
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )

            StatusBanner(settings, backendStatus)
            if (conversations.isNotEmpty()) {
                LazyRow(
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    contentPadding = PaddingValues(vertical = 6.dp)
                ) {
                    items(conversations, key = { it.id }) { conversation ->
                        FilterChip(
                            selected = conversation.id == selected?.id,
                            onClick = { viewModel.selectConversation(conversation.id) },
                            label = { Text(conversation.title, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                            leadingIcon = if (conversation.id == selected?.id) ({ Icon(Icons.Default.CheckCircle, contentDescription = null, Modifier.size(16.dp)) }) else null
                        )
                    }
                }
            }
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

            if (selected == null) {
                EmptyClayCard(R.string.no_messages, Modifier.padding(16.dp))
            } else {
                LazyColumn(
                    state = listState,
                    modifier = Modifier.weight(1f).fillMaxWidth(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    if (selected.messages.isEmpty()) {
                        item { WelcomeClayCard() }
                    }
                    items(selected.messages, key = { it.id }) { message ->
                        MessageBubble(message, onCopy = {
                            clipboard.setText(AnnotatedString(message.text))
                            scope.launch { snackbarHostState.showSnackbar(copiedText) }
                        }, onSpeak = if (message.role == MessageRole.ASSISTANT) {
                            {
                                viewModel.voiceService.speak(message.text, settings.speakingLanguage, settings.voiceGender, settings.speechRate, settings.pitch)
                            }
                        } else null, onShare = if (message.role == MessageRole.ASSISTANT) {
                            { shareText(context, message.text) }
                        } else null)
                    }
                    if (isGenerating) {
                        item { TypingIndicator() }
                    }
                    if (error != null) {
                        item {
                            ErrorClayCard(error = error!!, onRetry = viewModel::retryLastMessage)
                        }
                    }
                }
            }

            if (voice.isListening || voice.partialText.isNotBlank()) {
                VoiceListeningPanel(
                    transcript = voice.partialText,
                    onStop = viewModel.voiceService::stopListening
                )
            }
            MessageComposer(
                input = input,
                isGenerating = isGenerating,
                isListening = voice.isListening,
                onInputChange = { input = it },
                onSend = {
                    if (input.isNotBlank()) {
                        viewModel.sendMessage(input)
                        input = ""
                    }
                },
                onStop = viewModel::stopGeneration,
                onMic = {
                    if (voice.isListening) viewModel.voiceService.stopListening()
                    else if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                        viewModel.voiceService.startListening(settings.speakingLanguage)
                    } else showMicrophoneDialog = true
                }
            )
        }
        SnackbarHost(snackbarHostState, Modifier.align(Alignment.BottomCenter).padding(bottom = 8.dp))
    }

    if (showMicrophoneDialog) {
        AlertDialog(
            onDismissRequest = { showMicrophoneDialog = false },
            icon = { Icon(Icons.Default.Mic, contentDescription = null) },
            title = { AppText(R.string.microphone_title) },
            text = { AppText(R.string.microphone_explanation) },
            confirmButton = {
                TextButton(onClick = { showMicrophoneDialog = false; requestMicrophone.launch(Manifest.permission.RECORD_AUDIO) }) { AppText(R.string.allow_microphone) }
            },
            dismissButton = { TextButton(onClick = { showMicrophoneDialog = false }) { AppText(R.string.cancel) } }
        )
    }
    if (showClearDialog) {
        ConfirmDialog(
            titleId = R.string.clear_conversation,
            messageId = R.string.clear_conversation_message,
            onConfirm = { showClearDialog = false; selected?.let { viewModel.clearConversation(it.id) } },
            onDismiss = { showClearDialog = false }
        )
    }
    if (showClearAllDialog) {
        ConfirmDialog(
            titleId = R.string.clear_all,
            messageId = R.string.clear_all_message,
            onConfirm = { showClearAllDialog = false; viewModel.clearAllConversations() },
            onDismiss = { showClearAllDialog = false }
        )
    }
    showNewNameDialog?.let { id ->
        val conversation = conversations.firstOrNull { it.id == id }
        RenameDialog(
            initial = conversation?.title.orEmpty(),
            onDismiss = { showNewNameDialog = null },
            onSave = { title -> viewModel.renameConversation(id, title); showNewNameDialog = null }
        )
    }
}

@Composable
private fun StatusBanner(settings: SettingsState, backendStatus: ConnectionStatus) {
    val detailId = when {
        settings.demoMode -> R.string.ai_disclaimer
        backendStatus == ConnectionStatus.ONLINE -> R.string.online
        backendStatus == ConnectionStatus.AUTHENTICATION_REQUIRED -> R.string.authentication_required
        backendStatus == ConnectionStatus.BLOCKED -> R.string.blocked
        backendStatus == ConnectionStatus.CONNECTING -> R.string.connecting
        backendStatus == ConnectionStatus.OFFLINE -> R.string.offline
        else -> R.string.backend_not_configured
    }
    ClayCard(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
        shape = RoundedCornerShape(18.dp)
    ) {
        Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.Link, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text(appString(if (settings.demoMode) R.string.demo_offline else R.string.backend_status), fontWeight = FontWeight.SemiBold)
                Text(
                    appString(detailId),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )
            }
        }
    }
}

@Composable
private fun WelcomeClayCard() {
    ClayCard(
        modifier = Modifier.fillMaxWidth().animateContentSize(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        shape = RoundedCornerShape(24.dp)
    ) {
        Column(Modifier.padding(22.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(appString(R.string.welcome_title), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(appString(R.string.greeting_subtitle), color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(appString(R.string.welcome_body), style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun MessageBubble(message: ChatMessage, onCopy: () -> Unit, onSpeak: (() -> Unit)?, onShare: (() -> Unit)?) {
    val isUser = message.role == MessageRole.USER
    val copyDescription = appString(R.string.copy)
    val speakDescription = appString(R.string.speak)
    val shareDescription = appString(R.string.share_response)
    Row(Modifier.fillMaxWidth(), horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start) {
        Column(horizontalAlignment = if (isUser) Alignment.End else Alignment.Start, modifier = Modifier.fillMaxWidth(0.9f)) {
            ClayBubble(
                isUser = isUser,
                modifier = Modifier.animateContentSize()
            ) {
                Column(Modifier.padding(horizontal = 16.dp, vertical = 12.dp)) {
                    Text(message.text, style = MaterialTheme.typography.bodyLarge)
                    Spacer(Modifier.height(6.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(formatTimestamp(message.timestamp), style = MaterialTheme.typography.labelSmall, color = LocalContentColor.current.copy(alpha = 0.7f))
                        IconButton(onClick = onCopy, modifier = Modifier.size(28.dp).semantics { contentDescription = copyDescription }) {
                            Icon(Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.size(15.dp))
                        }
                        if (onSpeak != null) {
                            IconButton(onClick = onSpeak, modifier = Modifier.size(28.dp).semantics { contentDescription = speakDescription }) {
                                Icon(Icons.AutoMirrored.Filled.VolumeUp, contentDescription = null, modifier = Modifier.size(16.dp))
                            }
                        }
                        if (onShare != null) {
                            IconButton(onClick = onShare, modifier = Modifier.size(28.dp).semantics { contentDescription = shareDescription }) {
                                Icon(Icons.Default.Share, contentDescription = null, modifier = Modifier.size(16.dp))
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ClayBubble(
    isUser: Boolean,
    modifier: Modifier = Modifier,
    content: @Composable ColumnScope.() -> Unit
) {
    val shape = RoundedCornerShape(22.dp, 22.dp, if (isUser) 6.dp else 22.dp, 22.dp)
    val face = if (isUser) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant
    val ink = if (isUser) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant
    Box(modifier) {
        Box(
            Modifier
                .matchParentSize()
                .offset(y = 6.dp)
                .clip(shape)
                .background(if (isUser) MaterialTheme.colorScheme.primary.copy(alpha = 0.48f) else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.11f), shape)
        )
        CompositionLocalProvider(LocalContentColor provides ink) {
            Column(
                Modifier
                    .shadow(8.dp, shape, clip = false, ambientColor = face.copy(alpha = 0.2f), spotColor = face.copy(alpha = 0.3f))
                    .clip(shape)
                    .background(face)
                    .border(1.dp, Color.White.copy(alpha = if (isUser) 0.22f else 0.12f), shape),
                content = content
            )
        }
    }
}

@Composable
private fun TypingIndicator() {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
        Text(appString(R.string.thinking), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.primary)
    }
}

@Composable
private fun ErrorClayCard(error: String, onRetry: () -> Unit) {
    ClayCard(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer), modifier = Modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Default.ErrorOutline, contentDescription = null, tint = MaterialTheme.colorScheme.onErrorContainer)
            Spacer(Modifier.width(10.dp))
            Text(error, Modifier.weight(1f), color = MaterialTheme.colorScheme.onErrorContainer, style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = onRetry) { AppText(R.string.retry) }
        }
    }
}

@Composable
private fun MessageComposer(
    input: String,
    isGenerating: Boolean,
    isListening: Boolean,
    onInputChange: (String) -> Unit,
    onSend: () -> Unit,
    onStop: () -> Unit,
    onMic: () -> Unit
) {
    val microphoneDescription = appString(if (isListening) R.string.stop_listening else R.string.microphone)
    val sendDescription = appString(if (isGenerating) R.string.stop_generation else R.string.send)
    ClayCard(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 6.dp, vertical = 6.dp),
            verticalAlignment = Alignment.Bottom,
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            ClayIconButton(
                onClick = onMic,
                icon = if (isListening) Icons.Default.Stop else Icons.Default.Mic,
                contentDescription = microphoneDescription,
                active = isListening,
                danger = isListening
            )
            OutlinedTextField(
                value = input,
                onValueChange = onInputChange,
                modifier = Modifier.weight(1f).shadow(3.dp, RoundedCornerShape(22.dp), clip = false),
                placeholder = { AppText(R.string.message_placeholder, style = MaterialTheme.typography.bodyMedium) },
                maxLines = 4,
                keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(imeAction = ImeAction.Send, keyboardType = KeyboardType.Text),
                keyboardActions = androidx.compose.foundation.text.KeyboardActions(onSend = { onSend() }),
                shape = RoundedCornerShape(22.dp)
            )
            ClayIconButton(
                onClick = if (isGenerating) onStop else onSend,
                icon = if (isGenerating) Icons.Default.Stop else Icons.AutoMirrored.Filled.Send,
                contentDescription = sendDescription,
                enabled = isGenerating || input.isNotBlank(),
                active = isGenerating
            )
        }
    }
}

@Composable
private fun VoiceListeningPanel(transcript: String, onStop: () -> Unit) {
    val transition = rememberInfiniteTransition(label = "voicePulse")
    val pulse by transition.animateFloat(
        initialValue = 0.96f,
        targetValue = 1.08f,
        animationSpec = infiniteRepeatable(tween(900), RepeatMode.Reverse),
        label = "voicePulseScale"
    )
    ClayCard(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
    ) {
        Row(
            Modifier.fillMaxWidth().padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Box(Modifier.scale(pulse)) {
                ClayIconButton(
                    onClick = onStop,
                    icon = Icons.Default.Stop,
                    contentDescription = appString(R.string.stop_listening),
                    active = true,
                    danger = true
                )
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(appString(R.string.listening), style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                Text(
                    transcript.ifBlank { appString(R.string.listening) },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis
                )
            }
            ClayButton(
                onClick = onStop,
                modifier = Modifier.width(112.dp),
                color = MaterialTheme.colorScheme.surface,
                contentColor = MaterialTheme.colorScheme.primary
            ) {
                Text(appString(R.string.stop_listening), style = MaterialTheme.typography.labelLarge, maxLines = 1)
            }
        }
    }
}

@Composable
private fun DevicesScreen(viewModel: MainViewModel) {
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    val devices by viewModel.devices.collectAsStateWithLifecycle()
    var showPairing by remember { mutableStateOf(false) }
    var pairingCode by remember { mutableStateOf("") }
    LaunchedEffect(settings.demoMode, settings.backendUrl) { viewModel.refreshDevices() }
    Column(Modifier.fillMaxSize()) {
        ScreenTopBar(R.string.devices, R.string.refresh) { viewModel.refreshDevices(); viewModel.refreshBackendStatus() }
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item { SectionIntro(R.string.devices, R.string.greeting_subtitle) }
            items(devices, key = { it.id }) { device -> DeviceClayCard(device) }
            item {
                Text(appString(R.string.future_devices), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            }
            item { EmptyClayCard(R.string.other_authorized_devices) }
            item {
                ClayButton(
                    onClick = {
                        pairingCode = (100000..999999).random().toString()
                        showPairing = true
                    },
                    modifier = Modifier.fillMaxWidth(),
                    color = MaterialTheme.colorScheme.secondary,
                    contentColor = MaterialTheme.colorScheme.onSecondary
                ) {
                    Icon(Icons.Default.Link, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    AppText(R.string.pair_pc)
                }
            }
            item {
                Text(
                    appString(if (settings.demoMode) R.string.pairing_not_ready else R.string.pairing_not_ready),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
    if (showPairing) {
        AlertDialog(
            onDismissRequest = { showPairing = false },
            icon = { Icon(Icons.Default.Link, contentDescription = null) },
            title = { AppText(R.string.pairing_title) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    AppText(R.string.pairing_description)
                    Text(pairingCode, style = MaterialTheme.typography.displaySmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                    AppText(R.string.pairing_not_ready, style = MaterialTheme.typography.bodySmall)
                }
            },
            confirmButton = { TextButton(onClick = { showPairing = false }) { AppText(R.string.close) } }
        )
    }
}

@Composable
private fun DeviceClayCard(device: DeviceInfo) {
    val icon = if (device.kind == "pc") Icons.Default.Devices else Icons.Default.PhoneAndroid
    ClayCard(Modifier.fillMaxWidth(), shape = RoundedCornerShape(20.dp)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(shape = CircleShape, color = MaterialTheme.colorScheme.primaryContainer, modifier = Modifier.size(46.dp)) {
                    Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(11.dp))
                }
                Spacer(Modifier.width(12.dp))
                Column(Modifier.weight(1f)) {
                    Text(device.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text(if (device.paired) appString(R.string.paired) else appString(R.string.not_paired), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                ConnectionPill(device.status)
            }
            if (device.detail.isNotBlank()) Text(device.detail, style = MaterialTheme.typography.bodyMedium)
            Row(horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                StatusDetail(R.string.connection, statusId = connectionLabelId(device.status))
                StatusDetail(R.string.last_activity, value = device.lastActivity?.let(::formatTimestamp) ?: "—")
            }
        }
    }
}

@Composable
private fun RowScope.StatusDetail(labelId: Int, value: String? = null, statusId: Int? = null) {
    Column(Modifier.weight(1f)) {
        Text(appString(labelId), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(appString(statusId ?: R.string.unknown).takeIf { statusId != null } ?: value.orEmpty(), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun SecurityScreen(viewModel: MainViewModel) {
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    val security by viewModel.security.collectAsStateWithLifecycle()
    var confirmLockdown by remember { mutableStateOf(false) }
    var confirmDisable by remember { mutableStateOf(false) }
    LaunchedEffect(settings.demoMode, settings.backendUrl) { viewModel.refreshSecurity() }
    Column(Modifier.fillMaxSize()) {
        ScreenTopBar(R.string.security_center, R.string.refresh) { viewModel.refreshSecurity() }
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item {
                SecurityStatusClayCard(security.status, security.lockdownEnabled)
            }
            item {
                ClayCard(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
                    Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Lock, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                            Spacer(Modifier.width(10.dp))
                            Text(appString(R.string.lockdown), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        }
                        Text(appString(R.string.lockdown_message), style = MaterialTheme.typography.bodyMedium)
                        if (security.lockdownEnabled) {
                            ClayButton(
                                onClick = { confirmDisable = true },
                                modifier = Modifier.fillMaxWidth(),
                                color = MaterialTheme.colorScheme.error,
                                contentColor = MaterialTheme.colorScheme.onError
                            ) { AppText(R.string.disable_lockdown) }
                        } else {
                            ClayButton(
                                onClick = { confirmLockdown = true },
                                modifier = Modifier.fillMaxWidth(),
                                color = MaterialTheme.colorScheme.errorContainer,
                                contentColor = MaterialTheme.colorScheme.onErrorContainer
                            ) { AppText(R.string.enable_lockdown) }
                        }
                    }
                }
            }
            item { Text(appString(R.string.security_event), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold) }
            if (security.events.isEmpty()) {
                item { EmptyClayCard(R.string.no_security_events) }
            } else {
                items(security.events, key = { it.id }) { event -> SecurityEventClayCard(event) }
            }
        }
    }
    if (confirmLockdown) {
        ConfirmDialog(R.string.lockdown_title, R.string.lockdown_message, { confirmLockdown = false; viewModel.enableLockdown() }) { confirmLockdown = false }
    }
    if (confirmDisable) {
        ConfirmDialog(R.string.disable_lockdown, R.string.logout_message, { confirmDisable = false; viewModel.disableLockdown() }) { confirmDisable = false }
    }
}

@Composable
private fun SecurityStatusClayCard(status: SecurityStatus, lockdown: Boolean) {
    val (label, color, icon) = when (status) {
        SecurityStatus.PROTECTED -> Triple(R.string.status_protected, Color(0xFF2E7D5A), Icons.Default.CheckCircle)
        SecurityStatus.WARNING -> Triple(R.string.warning, Color(0xFF9B6500), Icons.Default.Warning)
        SecurityStatus.ACTION_REQUIRED -> Triple(R.string.action_required, MaterialTheme.colorScheme.error, Icons.Default.ErrorOutline)
    }
    ClayCard(Modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = color.copy(alpha = 0.12f)), shape = RoundedCornerShape(22.dp)) {
        Row(Modifier.padding(20.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(40.dp))
            Spacer(Modifier.width(14.dp))
            Column {
                Text(appString(label), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = color)
                Text(if (lockdown) appString(R.string.lockdown_enabled) else appString(R.string.security_protected_body), style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
private fun SecurityEventClayCard(event: SecurityEvent) {
    ClayCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(event.type, fontWeight = FontWeight.SemiBold)
            Text("${event.device} · ${formatTimestamp(event.timestamp)}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("${appString(R.string.event_result)}: ${event.result}", style = MaterialTheme.typography.bodySmall)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SettingsScreen(viewModel: MainViewModel) {
    val settings by viewModel.settings.collectAsStateWithLifecycle()
    val security by viewModel.security.collectAsStateWithLifecycle()
    val backendStatus by viewModel.backendStatus.collectAsStateWithLifecycle()
    val voiceState by viewModel.voiceService.state.collectAsStateWithLifecycle()
    val authDeviceId by viewModel.authDeviceId.collectAsStateWithLifecycle()
    val hasBackendApiKey by viewModel.hasBackendApiKey.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val voiceTestText = appString(R.string.voice_test_text)
    var backendUrl by remember(settings.backendUrl) { mutableStateOf(settings.backendUrl) }
    var deviceId by remember(authDeviceId) { mutableStateOf(authDeviceId) }
    var apiKey by remember { mutableStateOf("") }
    var showLogout by remember { mutableStateOf(false) }
    val requestNotifications = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        viewModel.setNotificationsEnabled(granted)
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        item { ScreenTopBar(R.string.settings) }
        item { SettingsSectionTitle(R.string.general) }
        item {
            SettingsClayCard {
                SettingsHeader(Icons.Default.Language, R.string.interface_language)
                LanguageChoice(settings.interfaceLanguage) { viewModel.setInterfaceLanguage(it) }
                HorizontalDivider(Modifier.padding(vertical = 14.dp))
                SettingsHeader(Icons.Default.DarkMode, R.string.theme)
                ChoiceChips(
                    items = listOf(AppThemeMode.SYSTEM to R.string.theme_system, AppThemeMode.LIGHT to R.string.theme_light, AppThemeMode.DARK to R.string.theme_dark),
                    selected = settings.theme,
                    onSelected = viewModel::setTheme
                )
                HorizontalDivider(Modifier.padding(vertical = 14.dp))
                SettingSwitch(
                    icon = Icons.Default.Notifications,
                    titleId = R.string.notifications,
                    descriptionId = R.string.notifications_description,
                    checked = settings.notificationsEnabled,
                    onCheckedChange = { enabled ->
                        if (enabled && android.os.Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                            requestNotifications.launch(Manifest.permission.POST_NOTIFICATIONS)
                        } else viewModel.setNotificationsEnabled(enabled)
                    }
                )
            }
        }
        item { SettingsSectionTitle(R.string.voice) }
        item {
            SettingsClayCard {
                SettingsHeader(Icons.AutoMirrored.Filled.VolumeUp, R.string.speaking_language)
                ChoiceChips(
                    items = listOf(VoiceLanguage.ENGLISH to R.string.language_english, VoiceLanguage.HINDI to R.string.language_hindi),
                    selected = settings.speakingLanguage,
                    onSelected = viewModel::setSpeakingLanguage
                )
                HorizontalDivider(Modifier.padding(vertical = 14.dp))
                SettingSwitch(Icons.AutoMirrored.Filled.VolumeUp, R.string.voice_enabled, R.string.voice_enabled_description, settings.voiceEnabled, viewModel::setVoiceEnabled)
                HorizontalDivider(Modifier.padding(vertical = 14.dp))
                SettingsHeader(Icons.Default.Settings, R.string.voice_preference)
                ChoiceChips(
                    items = listOf(VoiceGender.DEFAULT to R.string.voice_default, VoiceGender.MALE to R.string.voice_male, VoiceGender.FEMALE to R.string.voice_female),
                    selected = settings.voiceGender,
                    onSelected = viewModel::setVoiceGender
                )
                Spacer(Modifier.height(8.dp))
                Text(appString(R.string.speech_rate), style = MaterialTheme.typography.labelLarge)
                Slider(value = settings.speechRate, onValueChange = viewModel::setSpeechRate, valueRange = 0.5f..2f)
                Text("${(settings.speechRate * 100).roundToInt()}%", style = MaterialTheme.typography.labelSmall)
                Text(appString(R.string.pitch), style = MaterialTheme.typography.labelLarge)
                Slider(value = settings.pitch, onValueChange = viewModel::setPitch, valueRange = 0.5f..2f)
                Text("${(settings.pitch * 100).roundToInt()}%", style = MaterialTheme.typography.labelSmall)
                Text(appString(R.string.voice_availability), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    ClayButton(
                        onClick = {
                            viewModel.voiceService.speak(voiceTestText, settings.speakingLanguage, settings.voiceGender, settings.speechRate, settings.pitch)
                        },
                        modifier = Modifier.weight(1f),
                        color = MaterialTheme.colorScheme.secondary,
                        contentColor = MaterialTheme.colorScheme.onSecondary
                    ) {
                        Icon(Icons.AutoMirrored.Filled.VolumeUp, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        AppText(R.string.test_voice)
                    }
                    if (voiceState.isSpeaking) {
                        ClayButton(
                            onClick = viewModel.voiceService::stopSpeaking,
                            modifier = Modifier.weight(1f),
                            color = MaterialTheme.colorScheme.errorContainer,
                            contentColor = MaterialTheme.colorScheme.onErrorContainer
                        ) {
                            AppText(R.string.stop_speaking)
                        }
                    }
                }
            }
        }
        item { SettingsSectionTitle(R.string.ai) }
        item {
            SettingsClayCard {
                SettingSwitch(Icons.Default.Settings, R.string.demo_mode, R.string.demo_mode_description, settings.demoMode, viewModel::setDemoMode)
                Spacer(Modifier.height(12.dp))
                OutlinedTextField(
                    value = backendUrl,
                    onValueChange = { backendUrl = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { AppText(R.string.backend_url) },
                    placeholder = { AppText(R.string.backend_url_hint) },
                    singleLine = true,
                    keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Uri, imeAction = ImeAction.Done),
                    supportingText = { Text(appString(R.string.backend_url_empty)) }
                )
                Spacer(Modifier.height(14.dp))
                SettingsHeader(Icons.Default.Lock, R.string.backend_authentication)
                Text(appString(R.string.backend_auth_description), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(8.dp))
                OutlinedTextField(
                    value = deviceId,
                    onValueChange = { deviceId = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { AppText(R.string.backend_device_id) },
                    singleLine = true,
                    keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(imeAction = ImeAction.Next)
                )
                OutlinedTextField(
                    value = apiKey,
                    onValueChange = { apiKey = it },
                    modifier = Modifier.fillMaxWidth(),
                    label = { AppText(R.string.backend_api_key) },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Done),
                    supportingText = { if (hasBackendApiKey) Text(appString(R.string.backend_api_key_saved)) }
                )
                ClayButton(
                    onClick = {
                        viewModel.saveBackendConnection(backendUrl, deviceId, apiKey)
                        apiKey = ""
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.Link, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    AppText(R.string.save_backend_settings)
                }
                BackendStatusRow(backendStatus, settings.demoMode || backendUrl.isBlank())
            }
        }
        item { SettingsSectionTitle(R.string.devices_section) }
        item {
            SettingsClayCard {
                SettingsHeader(Icons.Default.Devices, R.string.paired_devices)
                Text(if (security.events.any { it.type.contains("paired", ignoreCase = true) }) appString(R.string.paired) else appString(R.string.not_paired), style = MaterialTheme.typography.bodyMedium)
                Text(appString(R.string.manage_sessions), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(8.dp))
                ClayButton(
                    onClick = { showLogout = true },
                    modifier = Modifier.fillMaxWidth(),
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    contentColor = MaterialTheme.colorScheme.onSurface
                ) {
                    Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    AppText(R.string.logout)
                }
            }
        }
        item { SettingsSectionTitle(R.string.security_center) }
        item {
            SettingsClayCard {
                SettingsHeader(Icons.Default.Security, R.string.security_center)
                Text(if (security.lockdownEnabled) appString(R.string.action_required) else appString(R.string.status_protected), color = if (security.lockdownEnabled) MaterialTheme.colorScheme.error else Color(0xFF2E7D5A), fontWeight = FontWeight.Bold)
                Text(appString(R.string.security_protected_body), style = MaterialTheme.typography.bodySmall)
            }
        }
        item { SettingsSectionTitle(R.string.about) }
        item {
            SettingsClayCard {
                SettingsHeader(Icons.Default.Info, R.string.app_name)
                Text(appString(R.string.made_by_satyam_playz), style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                Text(appString(R.string.about_description), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Spacer(Modifier.height(8.dp))
                Text("${appString(R.string.version)} ${BuildConfig.VERSION_NAME}", style = MaterialTheme.typography.bodyMedium)
                Text("${appString(R.string.build)} ${BuildConfig.VERSION_CODE}", style = MaterialTheme.typography.bodyMedium)
                Spacer(Modifier.height(8.dp))
                Text(appString(R.string.privacy), fontWeight = FontWeight.SemiBold)
                Text(appString(R.string.privacy_description), style = MaterialTheme.typography.bodySmall)
                Spacer(Modifier.height(8.dp))
                Text(appString(R.string.licenses), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.primary)
            }
        }
    }
    if (showLogout) {
        ConfirmDialog(R.string.logout, R.string.logout_message, { showLogout = false; viewModel.revokeLocalSession() }) { showLogout = false }
    }
}

@Composable
private fun BackendStatusRow(status: ConnectionStatus, demo: Boolean) {
    Row(Modifier.fillMaxWidth().padding(top = 12.dp), verticalAlignment = Alignment.CenterVertically) {
        Text(appString(R.string.backend_status), Modifier.weight(1f), style = MaterialTheme.typography.labelLarge)
        if (demo) Text(appString(R.string.demo_offline), color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelMedium)
        else ConnectionPill(status)
    }
}

@Composable
private fun SettingsClayCard(content: @Composable ColumnScope.() -> Unit) {
    ClayCard(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 6.dp), shape = RoundedCornerShape(20.dp)) {
        Column(Modifier.padding(18.dp), content = content)
    }
}

@Composable
private fun SettingsSectionTitle(id: Int) {
    Text(appString(id), Modifier.padding(start = 20.dp, top = 18.dp, bottom = 4.dp), style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
}

@Composable
private fun SettingsHeader(icon: androidx.compose.ui.graphics.vector.ImageVector, titleId: Int) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(22.dp))
        Spacer(Modifier.width(10.dp))
        Text(appString(titleId), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
private fun SettingSwitch(icon: androidx.compose.ui.graphics.vector.ImageVector, titleId: Int, descriptionId: Int, checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(22.dp))
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(appString(titleId), fontWeight = FontWeight.SemiBold)
            Text(appString(descriptionId), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        ClaySwitch(checked = checked, onCheckedChange = onCheckedChange)
    }
}

@Composable
private fun LanguageChoice(selected: InterfaceLanguage, onSelected: (InterfaceLanguage) -> Unit) {
    ChoiceChips(
        items = listOf(InterfaceLanguage.ENGLISH to R.string.language_english, InterfaceLanguage.HINDI to R.string.language_hindi),
        selected = selected,
        onSelected = onSelected
    )
}

@Composable
private fun <T> ChoiceChips(items: List<Pair<T, Int>>, selected: T, onSelected: (T) -> Unit) {
    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        items.forEach { (value, labelId) ->
            FilterChip(selected = value == selected, onClick = { onSelected(value) }, label = { AppText(labelId) })
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ScreenTopBar(titleId: Int, actionId: Int? = null, onAction: (() -> Unit)? = null) {
    val actionDescription = actionId?.let { appString(it) }
    TopAppBar(
        modifier = Modifier
            .padding(horizontal = 8.dp, vertical = 4.dp)
            .shadow(8.dp, RoundedCornerShape(22.dp), clip = false, ambientColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.12f), spotColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.2f))
            .clip(RoundedCornerShape(22.dp)),
        title = { AppText(titleId, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold) },
        actions = {
            if (actionId != null && onAction != null) IconButton(onClick = onAction, modifier = Modifier.semantics { contentDescription = actionDescription.orEmpty() }) { Icon(Icons.Default.Refresh, contentDescription = null) }
        },
        colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
    )
}

@Composable
private fun ConnectionPill(status: ConnectionStatus) {
    val (text, color) = when (status) {
        ConnectionStatus.ONLINE -> R.string.online to Color(0xFF2E7D5A)
        ConnectionStatus.OFFLINE -> R.string.offline to MaterialTheme.colorScheme.onSurfaceVariant
        ConnectionStatus.CONNECTING -> R.string.connecting to MaterialTheme.colorScheme.primary
        ConnectionStatus.AUTHENTICATION_REQUIRED -> R.string.authentication_required to Color(0xFF9B6500)
        ConnectionStatus.BLOCKED -> R.string.blocked to MaterialTheme.colorScheme.error
        ConnectionStatus.UNKNOWN -> R.string.unknown to MaterialTheme.colorScheme.onSurfaceVariant
    }
    Surface(shape = RoundedCornerShape(50), color = color.copy(alpha = 0.12f)) {
        Row(Modifier.padding(horizontal = 9.dp, vertical = 5.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(7.dp).clip(CircleShape).background(color))
            Spacer(Modifier.width(5.dp))
            Text(appString(text), style = MaterialTheme.typography.labelSmall, color = color, maxLines = 1)
        }
    }
}

private fun shareText(context: Context, text: String) {
    val shareIntent = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_TEXT, text)
    }
    context.startActivity(Intent.createChooser(shareIntent, null))
}

private fun connectionLabelId(status: ConnectionStatus): Int = when (status) {
    ConnectionStatus.ONLINE -> R.string.online
    ConnectionStatus.OFFLINE -> R.string.offline
    ConnectionStatus.CONNECTING -> R.string.connecting
    ConnectionStatus.AUTHENTICATION_REQUIRED -> R.string.authentication_required
    ConnectionStatus.BLOCKED -> R.string.blocked
    ConnectionStatus.UNKNOWN -> R.string.unknown
}

@Composable
private fun SectionIntro(titleId: Int, subtitleId: Int) {
    Column(Modifier.padding(bottom = 2.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(appString(titleId), style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
        Text(appString(subtitleId), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun ClayNavigationBar(content: @Composable RowScope.() -> Unit) {
    val shape = RoundedCornerShape(30.dp)
    Box(
        Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 8.dp)
    ) {
        Box(
            Modifier
                .matchParentSize()
                .offset(y = 6.dp)
                .clip(shape)
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.18f))
        )
        Surface(
            modifier = Modifier
                .fillMaxWidth()
                .shadow(12.dp, shape, clip = false, ambientColor = Color.Black.copy(alpha = 0.22f), spotColor = Color.Black.copy(alpha = 0.28f))
                .border(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.6f), shape),
            shape = shape,
            color = MaterialTheme.colorScheme.surface,
            tonalElevation = 8.dp
        ) {
            Row(
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 6.dp, vertical = 7.dp),
                horizontalArrangement = Arrangement.SpaceEvenly,
                content = content
            )
        }
    }
}

@Composable
private fun RowScope.ClayNavigationItem(
    selected: Boolean,
    labelId: Int,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit
) {
    val shape = RoundedCornerShape(20.dp)
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val offset by animateDpAsState(if (pressed) 3.dp else 0.dp, label = "navPress")
    Box(
        Modifier
            .weight(1f)
            .padding(horizontal = 2.dp)
            .offset(y = offset)
            .clip(shape)
            .background(if (selected) MaterialTheme.colorScheme.primaryContainer else Color.Transparent, shape)
            .border(if (selected) 1.dp else 0.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f), shape)
            .clickable(interactionSource = interactionSource, indication = null, onClick = onClick)
            .padding(vertical = 6.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Icon(icon, contentDescription = appString(labelId), tint = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant)
            Text(appString(labelId), style = MaterialTheme.typography.labelSmall, color = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
        }
    }
}

@Composable
private fun ClayButton(
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    shape: Shape = RoundedCornerShape(18.dp),
    color: Color = MaterialTheme.colorScheme.primary,
    contentColor: Color = MaterialTheme.colorScheme.onPrimary,
    content: @Composable RowScope.() -> Unit
) {
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val pressOffset by animateDpAsState(if (pressed) 4.dp else 0.dp, label = "buttonPress")
    val depthColor = if (enabled) color.copy(alpha = 0.55f) else MaterialTheme.colorScheme.onSurface.copy(alpha = 0.12f)
    Box(modifier.heightIn(min = 52.dp)) {
        Box(
            Modifier
                .matchParentSize()
                .offset(y = 6.dp)
                .clip(shape)
                .background(depthColor)
        )
        Row(
            Modifier
                .fillMaxWidth()
                .offset(y = pressOffset)
                .shadow(8.dp, shape, clip = false, ambientColor = color.copy(alpha = 0.22f), spotColor = color.copy(alpha = 0.34f))
                .clip(shape)
                .background(color)
                .border(1.dp, Color.White.copy(alpha = if (enabled) 0.28f else 0.08f), shape)
                .clickable(enabled = enabled, interactionSource = interactionSource, indication = null, onClick = onClick)
                .padding(horizontal = 18.dp, vertical = 14.dp),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically,
            content = content
        )
    }
}

@Composable
private fun ClayIconButton(
    onClick: () -> Unit,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    contentDescription: String,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    active: Boolean = false,
    danger: Boolean = false
) {
    val shape = CircleShape
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val pressOffset by animateDpAsState(if (pressed) 3.dp else 0.dp, label = "iconPress")
    val face = when {
        danger -> MaterialTheme.colorScheme.errorContainer
        active -> MaterialTheme.colorScheme.primaryContainer
        else -> MaterialTheme.colorScheme.surfaceVariant
    }
    val tint = when {
        danger -> MaterialTheme.colorScheme.error
        active -> MaterialTheme.colorScheme.primary
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }
    Box(modifier.size(50.dp)) {
        Box(Modifier.matchParentSize().offset(y = 5.dp).clip(shape).background(tint.copy(alpha = 0.18f)))
        Box(
            Modifier
                .matchParentSize()
                .offset(y = pressOffset)
                .shadow(8.dp, shape, clip = false, ambientColor = tint.copy(alpha = 0.2f), spotColor = tint.copy(alpha = 0.3f))
                .clip(shape)
                .background(face)
                .border(1.dp, Color.White.copy(alpha = 0.24f), shape)
                .clickable(enabled = enabled, interactionSource = interactionSource, indication = null, onClick = onClick),
            contentAlignment = Alignment.Center
        ) {
            Icon(icon, contentDescription = contentDescription, tint = tint)
        }
    }
}

@Composable
private fun ClaySwitch(checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    val shape = RoundedCornerShape(22.dp)
    val interactionSource = remember { MutableInteractionSource() }
    val pressed by interactionSource.collectIsPressedAsState()
    val pressOffset by animateDpAsState(if (pressed) 2.dp else 0.dp, label = "switchPress")
    val thumbOffset by animateDpAsState(if (checked) 22.dp else 0.dp, label = "switchThumb")
    Box(
        Modifier
            .size(width = 54.dp, height = 34.dp)
            .offset(y = pressOffset)
            .shadow(5.dp, shape, clip = false, ambientColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.18f))
            .clip(shape)
            .background(if (checked) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceVariant)
            .border(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.65f), shape)
            .clickable(interactionSource = interactionSource, indication = null, onClick = { onCheckedChange(!checked) }),
        contentAlignment = Alignment.CenterStart
    ) {
        Box(
            Modifier
                .padding(4.dp)
                .offset(x = thumbOffset)
                .size(26.dp)
                .shadow(4.dp, CircleShape, clip = false)
                .clip(CircleShape)
                .background(if (checked) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.82f))
                .border(1.dp, Color.White.copy(alpha = 0.4f), CircleShape)
        )
    }
}

@Composable
private fun ClayCard(
    modifier: Modifier = Modifier,
    colors: CardColors = CardDefaults.cardColors(),
    shape: Shape = RoundedCornerShape(26.dp),
    content: @Composable ColumnScope.() -> Unit
) {
    Box(modifier) {
        Box(
            Modifier
                .matchParentSize()
                .offset(y = 7.dp)
                .shadow(10.dp, shape, clip = false, ambientColor = Color.Black.copy(alpha = 0.18f), spotColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.28f))
                .clip(shape)
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.16f), shape)
        )
        Box(
            Modifier
                .matchParentSize()
                .offset(y = 2.dp)
                .clip(shape)
                .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.045f), shape)
        )
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .shadow(9.dp, shape, clip = false, ambientColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.15f), spotColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.23f))
                .border(1.dp, MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.52f), shape),
            shape = shape,
            colors = colors,
            elevation = CardDefaults.cardElevation(defaultElevation = 5.dp),
            content = content
        )
    }
}

@Composable
private fun EmptyClayCard(textId: Int, modifier: Modifier = Modifier) {
    ClayCard(modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)) {
        Text(appString(textId), Modifier.padding(18.dp), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun ConfirmDialog(titleId: Int, messageId: Int, onConfirm: () -> Unit, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { AppText(titleId) },
        text = { AppText(messageId) },
        confirmButton = { TextButton(onClick = onConfirm) { AppText(R.string.confirm) } },
        dismissButton = { TextButton(onClick = onDismiss) { AppText(R.string.cancel) } }
    )
}

@Composable
private fun RenameDialog(initial: String, onDismiss: () -> Unit, onSave: (String) -> Unit) {
    var value by rememberSaveable(initial) { mutableStateOf(initial) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { AppText(R.string.rename) },
        text = { OutlinedTextField(value = value, onValueChange = { value = it }, singleLine = true, label = { AppText(R.string.conversation) }) },
        confirmButton = { TextButton(onClick = { onSave(value) }) { AppText(R.string.save) } },
        dismissButton = { TextButton(onClick = onDismiss) { AppText(R.string.cancel) } }
    )
}
