package com.playzai.app.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Shapes
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.playzai.app.model.AppThemeMode

private val LightColors = lightColorScheme(
    primary = Color(0xFF7167D9),
    onPrimary = Color.White,
    primaryContainer = Color(0xFFE8E4FF),
    onPrimaryContainer = Color(0xFF27205F),
    secondary = Color(0xFF6E647C),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFF0E4F6),
    onSecondaryContainer = Color(0xFF2C2432),
    tertiary = Color(0xFFB66A84),
    background = Color(0xFFF9F7FC),
    onBackground = Color(0xFF1B1A20),
    surface = Color(0xFFFCFAFF),
    onSurface = Color(0xFF1B1A20),
    surfaceVariant = Color(0xFFF0EDF7),
    onSurfaceVariant = Color(0xFF5E5A68),
    outlineVariant = Color(0xFFE0DCE9)
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFFD0C8FF),
    onPrimary = Color(0xFF352B86),
    primaryContainer = Color(0xFF5147A2),
    onPrimaryContainer = Color(0xFFF0ECFF),
    secondary = Color(0xFFD6C8DD),
    onSecondary = Color(0xFF382D3D),
    secondaryContainer = Color(0xFF514354),
    onSecondaryContainer = Color(0xFFF3E6F7),
    tertiary = Color(0xFFF3B8CF),
    background = Color(0xFF121116),
    onBackground = Color(0xFFE8E3EA),
    surface = Color(0xFF1A181F),
    onSurface = Color(0xFFE8E3EA),
    surfaceVariant = Color(0xFF292631),
    onSurfaceVariant = Color(0xFFC9C1CE),
    outlineVariant = Color(0xFF46414D)
)

private val ClayShapes = Shapes(
    extraSmall = androidx.compose.foundation.shape.RoundedCornerShape(12.dp),
    small = androidx.compose.foundation.shape.RoundedCornerShape(16.dp),
    medium = androidx.compose.foundation.shape.RoundedCornerShape(22.dp),
    large = androidx.compose.foundation.shape.RoundedCornerShape(28.dp),
    extraLarge = androidx.compose.foundation.shape.RoundedCornerShape(34.dp)
)

@Composable
fun PlayzAiTheme(theme: AppThemeMode, content: @Composable () -> Unit) {
    val dark = when (theme) {
        AppThemeMode.SYSTEM -> isSystemInDarkTheme()
        AppThemeMode.LIGHT -> false
        AppThemeMode.DARK -> true
    }
    MaterialTheme(
        colorScheme = if (dark) DarkColors else LightColors,
        typography = Typography(),
        shapes = ClayShapes,
        content = content
    )
}
