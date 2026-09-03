package com.guardianshield.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlin.math.sin

/**
 * Animated real-time waveform visualizer showing live incoming PCM audio stream energy.
 */
@Composable
fun AudioVisualizer(
    rmsEnergy: Float,
    decibels: Float,
    modifier: Modifier = Modifier
) {
    val barCount = 18
    val infiniteTransition = rememberInfiniteTransition(label = "audio_anim")
    val phase by infiniteTransition.animateFloat(
        initialValue = 0f,
        targetValue = 360f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = LinearEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "phase"
    )

    Column(
        modifier = modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(Color(0xFF131C2E))
            .padding(16.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(70.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.CenterVertically
        ) {
            for (i in 0 until barCount) {
                val waveOffset = sin(Math.toRadians((phase + i * 20).toDouble())).toFloat()
                val minHeight = 6.dp
                val maxHeight = 60.dp

                // Height scales dynamically with real PCM RMS energy
                val dynamicScale = (rmsEnergy * 2.5f).coerceIn(0.05f, 1f)
                val barHeight = minHeight + (maxHeight - minHeight) * (0.3f + 0.7f * waveOffset.coerceAtLeast(0f)) * dynamicScale

                val barColor = when {
                    rmsEnergy > 0.4f -> Color(0xFFEF4444) // High audio intensity
                    rmsEnergy > 0.15f -> Color(0xFF38BDF8) // Normal speech
                    else -> Color(0xFF475569) // Silence / ambient
                }

                Box(
                    modifier = Modifier
                        .width(4.dp)
                        .height(barHeight)
                        .clip(RoundedCornerShape(2.dp))
                        .background(barColor)
                )
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(
                text = "Live Remote Audio PCM",
                color = Color(0xFF94A3B8),
                fontSize = 12.sp,
                fontWeight = FontWeight.Medium
            )
            Text(
                text = "${decibels.toInt()} dBFS (RMS: ${(rmsEnergy * 100).toInt()}%)",
                color = if (rmsEnergy > 0.05f) Color(0xFF10B981) else Color(0xFF64748B),
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}
