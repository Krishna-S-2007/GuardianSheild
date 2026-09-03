package com.guardianshield.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.guardianshield.audio.PCMBuffer
import com.guardianshield.ui.components.AudioVisualizer
import kotlinx.coroutines.delay

@Composable
fun CallScreen(
    remotePeerId: String,
    pcmBuffer: PCMBuffer,
    riskScore: Float = 0.0f,
    attackState: String = "NORMAL",
    activeClaim: String? = null,
    actionRequired: String? = null,
    verificationStatus: String? = null,
    verificationMessage: String? = null,
    onEndCall: () -> Unit,
    onSimulateThreat: (() -> Unit)? = null
) {
    var callSeconds by remember { mutableStateOf(0) }
    val rmsEnergy by pcmBuffer.currentRms.collectAsState()
    val decibels by pcmBuffer.currentDecibels.collectAsState()
    val scrollState = rememberScrollState()

    // Call duration timer
    LaunchedEffect(Unit) {
        while (true) {
            delay(1000)
            callSeconds++
        }
    }

    val minutes = callSeconds / 60
    val seconds = callSeconds % 60
    val durationFormatted = String.format("%02d:%02d", minutes, seconds)

    // Dynamic threat colors
    val riskColor by animateColorAsState(
        targetValue = when {
            riskScore >= 0.70f -> Color(0xFFEF4444) // Red - High Threat
            riskScore >= 0.35f -> Color(0xFFF59E0B) // Amber - Suspicious
            else -> Color(0xFF10B981)               // Green - Safe
        },
        label = "riskColorAnim"
    )

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Color(0xFF0B0F19)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 20.dp)
                .verticalScroll(scrollState),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // --- TOP: Peer Info & Status ---
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 28.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(72.dp)
                        .clip(CircleShape)
                        .background(Color(0xFF1E293B))
                        .border(2.dp, riskColor, CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = if (riskScore > 0.7f) Icons.Default.ShieldMoon else Icons.Default.PhoneInTalk,
                        contentDescription = "Active Call",
                        tint = riskColor,
                        modifier = Modifier.size(36.dp)
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Text(
                    text = remotePeerId,
                    color = Color.White,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold
                )

                Spacer(modifier = Modifier.height(4.dp))

                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(8.dp)
                            .clip(CircleShape)
                            .background(riskColor)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "LIVE CALL • $durationFormatted",
                        color = riskColor,
                        fontSize = 13.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // --- MIDDLE: Layer 3 Threat Reasoning Dashboard ---
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                // Threat Risk Level Card
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E293B))
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "AI SCAM THREAT ENGINE",
                                color = Color(0xFF94A3B8),
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                letterSpacing = 1.sp
                            )
                            Surface(
                                shape = RoundedCornerShape(8.dp),
                                color = riskColor.copy(alpha = 0.2f)
                            ) {
                                Text(
                                    text = attackState,
                                    color = riskColor,
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                )
                            }
                        }

                        // Risk Progress Bar
                        LinearProgressIndicator(
                            progress = { riskScore.coerceIn(0.0f, 1.0f) },
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(8.dp)
                                .clip(RoundedCornerShape(4.dp)),
                            color = riskColor,
                            trackColor = Color(0xFF334155)
                        )

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(
                                text = when {
                                    riskScore >= 0.70f -> "CRITICAL THREAT"
                                    riskScore >= 0.35f -> "SUSPICIOUS ACTIVITY"
                                    else -> "NORMAL CONVERSATION"
                                },
                                color = Color(0xFF94A3B8),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Medium
                            )
                            Text(
                                text = "${(riskScore * 100).toInt()}% RISK",
                                color = riskColor,
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }

                // Active Claim Banner (if caller made specific claims)
                AnimatedVisibility(visible = !activeClaim.isNullOrBlank()) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF2D1820))
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.Warning,
                                contentDescription = "Active Claim Warning",
                                tint = Color(0xFFF87171),
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = "ACTIVE CALLER CLAIM",
                                    color = Color(0xFFF87171),
                                    fontSize = 10.sp,
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    text = activeClaim ?: "",
                                    color = Color(0xFFFEE2E2),
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Medium
                                )
                            }
                        }
                    }
                }

                // Layer 4 Intervention Banner
                AnimatedVisibility(visible = !verificationStatus.isNullOrBlank() || !actionRequired.isNullOrBlank()) {
                    val isTerminated = verificationStatus == "CALL_TERMINATED" || actionRequired == "TERMINATE"
                    val isWaiting = verificationStatus == "WAITING_CONTACT" || actionRequired == "OUT_OF_BAND_VERIFY"

                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(
                                width = 1.dp,
                                color = if (isTerminated) Color(0xFFEF4444) else Color(0xFF38BDF8),
                                shape = RoundedCornerShape(12.dp)
                            ),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = if (isTerminated) Color(0xFF3B1218) else Color(0xFF0C243C)
                        )
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp)
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = if (isTerminated) Icons.Default.GppBad else Icons.Default.Security,
                                    contentDescription = "Intervention",
                                    tint = if (isTerminated) Color(0xFFEF4444) else Color(0xFF38BDF8),
                                    modifier = Modifier.size(18.dp)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = if (isTerminated) "INTERVENTION: TERMINATE CALL" else "LAYER 4 VERIFICATION ACTIVE",
                                    color = if (isTerminated) Color(0xFFEF4444) else Color(0xFF38BDF8),
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = verificationMessage ?: (
                                    if (isTerminated) "Critical fraud pattern detected. Disconnect immediately."
                                    else "Out-of-band verification challenge dispatched to trusted contact."
                                ),
                                color = Color.White,
                                fontSize = 12.sp
                            )
                        }
                    }
                }

                // Live Audio Waveform Visualizer
                AudioVisualizer(
                    rmsEnergy = rmsEnergy,
                    decibels = decibels
                )

                // Audio Telemetry Card
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = Color(0xFF1E293B))
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(14.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = "AUDIO INGESTION STREAM",
                            color = Color(0xFF38BDF8),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            letterSpacing = 1.sp
                        )

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text("Frames Ingested", color = Color(0xFF94A3B8), fontSize = 12.sp)
                            Text("${pcmBuffer.totalFramesIngested.get()} frames", color = Color(0xFF10B981), fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text("Buffered Volume", color = Color(0xFF94A3B8), fontSize = 12.sp)
                            Text("${pcmBuffer.totalBytesIngested.get() / 1024} KB", color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                        }
                    }
                }

                // Demo Trigger Helper (for live presentation demo)
                if (onSimulateThreat != null) {
                    OutlinedButton(
                        onClick = onSimulateThreat,
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFF38BDF8))
                    ) {
                        Icon(imageVector = Icons.Default.PlayArrow, contentDescription = "Simulate", modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Simulate Threat Telemetry (Demo)", fontSize = 12.sp)
                    }
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            // --- BOTTOM: End Call Action ---
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 24.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                IconButton(
                    onClick = onEndCall,
                    modifier = Modifier
                        .size(68.dp)
                        .clip(CircleShape)
                        .background(Color(0xFFEF4444))
                ) {
                    Icon(
                        imageVector = Icons.Default.CallEnd,
                        contentDescription = "End Call",
                        tint = Color.White,
                        modifier = Modifier.size(32.dp)
                    )
                }

                Spacer(modifier = Modifier.height(6.dp))

                Text(
                    text = "End Call",
                    color = Color(0xFF94A3B8),
                    fontSize = 12.sp
                )
            }
        }
    }
}
