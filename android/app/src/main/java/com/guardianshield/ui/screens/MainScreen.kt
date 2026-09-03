package com.guardianshield.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.PhoneInTalk
import androidx.compose.material.icons.filled.Security
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.guardianshield.webrtc.ConnectionStatus

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    deviceId: String,
    onDeviceIdChange: (String) -> Unit,
    backendHost: String,
    onBackendHostChange: (String) -> Unit,
    targetDeviceId: String,
    onTargetDeviceIdChange: (String) -> Unit,
    connectionStatus: ConnectionStatus,
    onConnectToggle: () -> Unit,
    onInitiateCall: () -> Unit,
    incomingCallerId: String?,
    onAcceptIncomingCall: () -> Unit,
    onRejectIncomingCall: () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Color(0xFF0B0F19)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // Header
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.fillMaxWidth()
            ) {
                Spacer(modifier = Modifier.height(24.dp))
                Icon(
                    imageVector = Icons.Default.Security,
                    contentDescription = "GuardianShield",
                    tint = Color(0xFF38BDF8),
                    modifier = Modifier.size(54.dp)
                )
                Spacer(modifier = Modifier.height(12.dp))
                Text(
                    text = "GUARDIANSHIELD",
                    color = Color.White,
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 2.sp
                )
                Text(
                    text = "Real-Time WebRTC Audio Stream Platform",
                    color = Color(0xFF94A3B8),
                    fontSize = 13.sp
                )
            }

            // Connection & Setup Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1E293B))
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Status Badge
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Signaling Status",
                            color = Color(0xFF94A3B8),
                            fontSize = 14.sp
                        )
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier
                                .clip(RoundedCornerShape(12.dp))
                                .background(
                                    when (connectionStatus) {
                                        ConnectionStatus.CONNECTED -> Color(0xFF064E3B)
                                        ConnectionStatus.CONNECTING -> Color(0xFF78350F)
                                        ConnectionStatus.DISCONNECTED -> Color(0xFF450A0A)
                                    }
                                )
                                .padding(horizontal = 10.dp, vertical = 4.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(
                                        when (connectionStatus) {
                                            ConnectionStatus.CONNECTED -> Color(0xFF10B981)
                                            ConnectionStatus.CONNECTING -> Color(0xFFF59E0B)
                                            ConnectionStatus.DISCONNECTED -> Color(0xFFEF4444)
                                        }
                                    )
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = connectionStatus.name,
                                color = when (connectionStatus) {
                                    ConnectionStatus.CONNECTED -> Color(0xFF34D399)
                                    ConnectionStatus.CONNECTING -> Color(0xFFFBBF24)
                                    ConnectionStatus.DISCONNECTED -> Color(0xFFF87171)
                                },
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }

                    // Device ID Input
                    OutlinedTextField(
                        value = deviceId,
                        onValueChange = onDeviceIdChange,
                        label = { Text("My Device ID", color = Color(0xFF94A3B8)) },
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            focusedBorderColor = Color(0xFF38BDF8),
                            unfocusedBorderColor = Color(0xFF475569)
                        ),
                        modifier = Modifier.fillMaxWidth()
                    )

                    // Backend Host Input
                    OutlinedTextField(
                        value = backendHost,
                        onValueChange = onBackendHostChange,
                        label = { Text("Backend Host (e.g., 192.168.1.50:8000)", color = Color(0xFF94A3B8)) },
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            focusedBorderColor = Color(0xFF38BDF8),
                            unfocusedBorderColor = Color(0xFF475569)
                        ),
                        modifier = Modifier.fillMaxWidth()
                    )

                    // Connect / Disconnect Button
                    Button(
                        onClick = onConnectToggle,
                        colors = ButtonDefaults.buttonColors(
                            containerColor = if (connectionStatus == ConnectionStatus.CONNECTED) Color(0xFFDC2626) else Color(0xFF0284C7)
                        ),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = if (connectionStatus == ConnectionStatus.CONNECTED) "Disconnect from Backend" else "Connect to Backend",
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }

            // Call Initiation Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF1E293B))
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    Text(
                        text = "Start WebRTC Voice Call",
                        color = Color.White,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.SemiBold
                    )

                    OutlinedTextField(
                        value = targetDeviceId,
                        onValueChange = onTargetDeviceIdChange,
                        label = { Text("Target Callee Device ID", color = Color(0xFF94A3B8)) },
                        singleLine = true,
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            focusedBorderColor = Color(0xFF38BDF8),
                            unfocusedBorderColor = Color(0xFF475569)
                        ),
                        modifier = Modifier.fillMaxWidth()
                    )

                    Button(
                        onClick = onInitiateCall,
                        enabled = connectionStatus == ConnectionStatus.CONNECTED && targetDeviceId.isNotBlank(),
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF10B981)),
                        shape = RoundedCornerShape(12.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(50.dp)
                    ) {
                        Icon(imageVector = Icons.Default.Call, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(text = "Start Live Call", fontSize = 16.sp, fontWeight = FontWeight.Bold)
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))
        }

        // Incoming Call Alert Dialog
        if (incomingCallerId != null) {
            AlertDialog(
                onDismissRequest = onRejectIncomingCall,
                containerColor = Color(0xFF1E293B),
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.PhoneInTalk,
                            contentDescription = null,
                            tint = Color(0xFF38BDF8)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(text = "Incoming Call", color = Color.White, fontWeight = FontWeight.Bold)
                    }
                },
                text = {
                    Column {
                        Text(text = "Incoming GuardianShield call from:", color = Color(0xFF94A3B8))
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = incomingCallerId,
                            color = Color(0xFF38BDF8),
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                },
                confirmButton = {
                    Button(
                        onClick = onAcceptIncomingCall,
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF10B981))
                    ) {
                        Text("Accept", fontWeight = FontWeight.Bold)
                    }
                },
                dismissButton = {
                    Button(
                        onClick = onRejectIncomingCall,
                        colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFEF4444))
                    ) {
                        Text("Reject", fontWeight = FontWeight.Bold)
                    }
                }
            )
        }
    }
}
