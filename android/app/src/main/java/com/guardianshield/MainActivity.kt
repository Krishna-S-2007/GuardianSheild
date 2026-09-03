package com.guardianshield

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.runtime.*
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.guardianshield.ui.screens.CallScreen
import com.guardianshield.ui.screens.MainScreen
import com.guardianshield.webrtc.*
import kotlinx.coroutines.launch
import org.webrtc.IceCandidate
import org.webrtc.SessionDescription
import java.util.UUID

class MainActivity : ComponentActivity(), SignalingEvents, WebRTCCallback {

    private val TAG = "MainActivity"

    private lateinit var webRTCManager: WebRTCManager
    private lateinit var signalingClient: SignalingClient

    // UI States
    private val deviceIdState = mutableStateOf("GS-" + UUID.randomUUID().toString().take(4).uppercase())
    private val backendHostState = mutableStateOf("10.0.2.2:8000") // 10.0.2.2 for emulator, or PC LAN IP
    private val targetDeviceIdState = mutableStateOf("")
    private val isCallActiveState = mutableStateOf(false)
    private val activeRemotePeerState = mutableStateOf("")
    private val incomingCallerState = mutableStateOf<String?>(null)
    private var currentSessionId: String = ""
    private val riskScoreState = mutableStateOf(0.0f)
    private val attackStateState = mutableStateOf("NORMAL")
    private val activeClaimState = mutableStateOf<String?>(null)
    private val actionRequiredState = mutableStateOf<String?>(null)
    private val verificationStatusState = mutableStateOf<String?>(null)
    private val verificationMessageState = mutableStateOf<String?>(null)

    private val requestPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted: Boolean ->
        if (!isGranted) {
            Toast.makeText(this, "Microphone permission is required for voice calling", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        checkPermissions()

        webRTCManager = WebRTCManager(applicationContext).apply {
            callback = this@MainActivity
        }

        signalingClient = SignalingClient(this, lifecycleScope)

        setContent {
            val connectionStatus by signalingClient.connectionStatus.collectAsState()
            val isCallActive by isCallActiveState
            val incomingCallerId by incomingCallerState

            if (isCallActive) {
                CallScreen(
                    remotePeerId = activeRemotePeerState.value,
                    pcmBuffer = webRTCManager.pcmBuffer,
                    riskScore = riskScoreState.value,
                    attackState = attackStateState.value,
                    activeClaim = activeClaimState.value,
                    actionRequired = actionRequiredState.value,
                    verificationStatus = verificationStatusState.value,
                    verificationMessage = verificationMessageState.value,
                    onEndCall = { hangupCall() },
                    onSimulateThreat = {
                        signalingClient.sendTelemetry(
                            sessionId = currentSessionId,
                            transcriptDelta = "This is CBI officer Sharma. Your bank accounts are under digital arrest. Transfer funds to safe escrow now.",
                            deepfakeScore = 0.88f,
                            isCritical = true
                        )
                    }
                )
            } else {
                MainScreen(
                    deviceId = deviceIdState.value,
                    onDeviceIdChange = { deviceIdState.value = it },
                    backendHost = backendHostState.value,
                    onBackendHostChange = { backendHostState.value = it },
                    targetDeviceId = targetDeviceIdState.value,
                    onTargetDeviceIdChange = { targetDeviceIdState.value = it },
                    connectionStatus = connectionStatus,
                    onConnectToggle = {
                        if (connectionStatus == ConnectionStatus.CONNECTED) {
                            signalingClient.disconnect()
                        } else {
                            signalingClient.connect(backendHostState.value, deviceIdState.value)
                        }
                    },
                    onInitiateCall = { startOutgoingCall() },
                    incomingCallerId = incomingCallerId,
                    onAcceptIncomingCall = { acceptIncomingCall() },
                    onRejectIncomingCall = { rejectIncomingCall() }
                )
            }
        }
    }

    private fun checkPermissions() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
        }
    }

    private fun startOutgoingCall() {
        val target = targetDeviceIdState.value.trim()
        if (target.isEmpty()) return

        currentSessionId = "CALL-" + UUID.randomUUID().toString().take(8).uppercase()
        activeRemotePeerState.value = target

        Log.i(TAG, "Initiating call to $target with session $currentSessionId")
        webRTCManager.startPeerConnection()
        webRTCManager.createOffer()
    }

    private fun acceptIncomingCall() {
        val caller = incomingCallerState.value ?: return
        incomingCallerState.value = null
        activeRemotePeerState.value = caller
        isCallActiveState.value = true

        Log.i(TAG, "Accepting incoming call from $caller for session $currentSessionId")
        signalingClient.acceptCall(caller, currentSessionId)
    }

    private fun rejectIncomingCall() {
        val caller = incomingCallerState.value ?: return
        incomingCallerState.value = null
        signalingClient.rejectCall(caller, currentSessionId)
    }

    private fun hangupCall() {
        val remotePeer = activeRemotePeerState.value
        if (remotePeer.isNotEmpty() && currentSessionId.isNotEmpty()) {
            signalingClient.sendCallEnd(remotePeer, currentSessionId)
        }
        cleanupCall()
    }

    private fun cleanupCall() {
        runOnUiThread {
            isCallActiveState.value = false
            activeRemotePeerState.value = ""
            incomingCallerState.value = null
            currentSessionId = ""
            riskScoreState.value = 0.0f
            attackStateState.value = "NORMAL"
            activeClaimState.value = null
            actionRequiredState.value = null
            verificationStatusState.value = null
            verificationMessageState.value = null
            webRTCManager.closePeerConnection()
        }
    }

    // --- WebRTC Manager Callbacks ---

    override fun onLocalDescriptionCreated(sdp: SessionDescription) {
        val target = activeRemotePeerState.value
        if (sdp.type == SessionDescription.Type.OFFER) {
            Log.i(TAG, "Sending SDP Offer to $target")
            signalingClient.sendOffer(target, currentSessionId, sdp.description)
        } else if (sdp.type == SessionDescription.Type.ANSWER) {
            Log.i(TAG, "Sending SDP Answer to $target")
            signalingClient.sendAnswer(target, currentSessionId, sdp.description)
        }
    }

    override fun onIceCandidateGenerated(candidate: IceCandidate) {
        val target = activeRemotePeerState.value
        if (target.isNotEmpty()) {
            signalingClient.sendIceCandidate(
                targetDeviceId = target,
                sessionId = currentSessionId,
                sdpMid = candidate.sdpMid,
                sdpMLineIndex = candidate.sdpMLineIndex,
                candidate = candidate.sdp
            )
        }
    }

    override fun onCallConnected() {
        Log.i(TAG, "WebRTC Audio Call Connected successfully!")
        runOnUiThread {
            isCallActiveState.value = true
        }
    }

    override fun onCallDisconnected() {
        Log.i(TAG, "WebRTC Call Disconnected.")
        cleanupCall()
    }

    override fun onError(error: String) {
        Log.e(TAG, "WebRTC Error: $error")
        runOnUiThread {
            Toast.makeText(this, error, Toast.LENGTH_SHORT).show()
        }
    }

    // --- Signaling Client Callbacks ---

    override fun onRegistered(deviceId: String) {
        runOnUiThread {
            Toast.makeText(this, "Connected as $deviceId", Toast.LENGTH_SHORT).show()
        }
    }

    override fun onIncomingCall(callerDeviceId: String, sessionId: String) {
        currentSessionId = sessionId
        runOnUiThread {
            incomingCallerState.value = callerDeviceId
        }
    }

    override fun onCallAccepted(sessionId: String) {
        Log.i(TAG, "Peer accepted call session $sessionId")
        runOnUiThread {
            isCallActiveState.value = true
        }
    }

    override fun onCallRejected(sessionId: String) {
        runOnUiThread {
            Toast.makeText(this, "Call was rejected", Toast.LENGTH_SHORT).show()
            cleanupCall()
        }
    }

    override fun onOfferReceived(sdp: String, sessionId: String, callerDeviceId: String) {
        currentSessionId = sessionId
        activeRemotePeerState.value = callerDeviceId
        webRTCManager.startPeerConnection()
        webRTCManager.setRemoteDescription(sdp, SessionDescription.Type.OFFER)
    }

    override fun onAnswerReceived(sdp: String, sessionId: String) {
        webRTCManager.setRemoteDescription(sdp, SessionDescription.Type.ANSWER)
    }

    override fun onIceCandidateReceived(sdpMid: String?, sdpMLineIndex: Int, candidate: String) {
        webRTCManager.addIceCandidate(sdpMid, sdpMLineIndex, candidate)
    }

    override fun onCallEnded(sessionId: String) {
        runOnUiThread {
            Toast.makeText(this, "Call ended by peer", Toast.LENGTH_SHORT).show()
            cleanupCall()
        }
    }

    override fun onStateUpdate(sessionId: String, payload: com.google.gson.JsonObject) {
        runOnUiThread {
            riskScoreState.value = payload.get("risk_score")?.asFloat ?: 0.0f
            attackStateState.value = payload.get("current_state")?.asString ?: "NORMAL"
            activeClaimState.value = payload.get("active_claim")?.let { if (it.isJsonNull) null else it.asString }
            actionRequiredState.value = payload.get("action_required")?.let { if (it.isJsonNull) null else it.asString }
        }
    }

    override fun onVerificationUpdate(sessionId: String, payload: com.google.gson.JsonObject) {
        runOnUiThread {
            verificationStatusState.value = payload.get("status")?.let { if (it.isJsonNull) null else it.asString }
            verificationMessageState.value = payload.get("message")?.let { if (it.isJsonNull) null else it.asString }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        signalingClient.disconnect()
        webRTCManager.release()
    }
}
