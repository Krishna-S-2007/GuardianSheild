package com.guardianshield.webrtc

import android.util.Log
import com.google.gson.Gson
import com.google.gson.JsonObject
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit

enum class ConnectionStatus {
    DISCONNECTED,
    CONNECTING,
    CONNECTED
}

interface SignalingEvents {
    fun onRegistered(deviceId: String)
    fun onIncomingCall(callerDeviceId: String, sessionId: String)
    fun onCallAccepted(sessionId: String)
    fun onCallRejected(sessionId: String)
    fun onOfferReceived(sdp: String, sessionId: String, callerDeviceId: String)
    fun onAnswerReceived(sdp: String, sessionId: String)
    fun onIceCandidateReceived(sdpMid: String?, sdpMLineIndex: Int, candidate: String)
    fun onCallEnded(sessionId: String)
    fun onError(message: String)
}

class SignalingClient(
    private val events: SignalingEvents,
    private val scope: CoroutineScope = CoroutineScope(Dispatchers.IO)
) {
    private val TAG = "SignalingClient"
    private val gson = Gson()
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .pingInterval(15, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    var myDeviceId: String = ""
        private set

    private val _connectionStatus = MutableStateFlow(ConnectionStatus.DISCONNECTED)
    val connectionStatus: StateFlow<ConnectionStatus> = _connectionStatus.asStateFlow()

    fun connect(backendHost: String, deviceId: String) {
        this.myDeviceId = deviceId
        disconnect()

        val normalizedHost = backendHost.trim()
            .removePrefix("http://")
            .removePrefix("https://")
            .removePrefix("ws://")
            .removePrefix("wss://")

        val wsUrl = "ws://$normalizedHost/ws/device/$deviceId"
        Log.i(TAG, "Connecting to WebSocket signaling: $wsUrl")
        _connectionStatus.value = ConnectionStatus.CONNECTING

        val request = Request.Builder().url(wsUrl).build()
        webSocket = client.newWebSocket(request, createWebSocketListener())
    }

    fun disconnect() {
        try {
            webSocket?.close(1000, "User disconnected")
        } catch (e: Exception) {
            Log.e(TAG, "Error closing WebSocket: ${e.message}")
        }
        webSocket = null
        _connectionStatus.value = ConnectionStatus.DISCONNECTED
    }

    private fun createWebSocketListener(): WebSocketListener {
        return object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.i(TAG, "Signaling WebSocket connected successfully.")
                _connectionStatus.value = ConnectionStatus.CONNECTED
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                Log.d(TAG, "Signaling message received: $text")
                scope.launch {
                    handleIncomingMessage(text)
                }
            }

            override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "Signaling WebSocket closing: $reason")
                _connectionStatus.value = ConnectionStatus.DISCONNECTED
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.i(TAG, "Signaling WebSocket closed: $reason")
                _connectionStatus.value = ConnectionStatus.DISCONNECTED
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "Signaling WebSocket error: ${t.message}")
                _connectionStatus.value = ConnectionStatus.DISCONNECTED
                events.onError("Connection failed: ${t.localizedMessage ?: "Unknown error"}")
            }
        }
    }

    private fun handleIncomingMessage(text: String) {
        try {
            val json = gson.fromJson(text, JsonObject::class.java)
            val type = json.get("type")?.asString ?: return
            val sender = json.get("sender_device_id")?.asString ?: ""
            val sessionId = json.get("session_id")?.asString ?: ""

            when (type) {
                "registered" -> {
                    events.onRegistered(myDeviceId)
                }
                "incoming_call" -> {
                    events.onIncomingCall(sender, sessionId)
                }
                "call_accept" -> {
                    events.onCallAccepted(sessionId)
                }
                "call_reject" -> {
                    events.onCallRejected(sessionId)
                }
                "offer" -> {
                    val sdp = json.get("sdp")?.asString ?: ""
                    events.onOfferReceived(sdp, sessionId, sender)
                }
                "answer" -> {
                    val sdp = json.get("sdp")?.asString ?: ""
                    events.onAnswerReceived(sdp, sessionId)
                }
                "ice_candidate" -> {
                    val candObj = json.getAsJsonObject("candidate")
                    if (candObj != null) {
                        val sdp = candObj.get("candidate")?.asString ?: ""
                        val sdpMid = candObj.get("sdpMid")?.asString
                        val sdpMLineIndex = candObj.get("sdpMLineIndex")?.asInt ?: 0
                        events.onIceCandidateReceived(sdpMid, sdpMLineIndex, sdp)
                    }
                }
                "call_end" -> {
                    events.onCallEnded(sessionId)
                }
                "error" -> {
                    val errMsg = json.getAsJsonObject("payload")?.get("error")?.asString ?: "Unknown signaling error"
                    events.onError(errMsg)
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed parsing signaling message: ${e.message}")
        }
    }

    fun initiateCall(targetDeviceId: String, sessionId: String) {
        val msg = JsonObject().apply {
            addProperty("type", "call_initiate")
            addProperty("sender_device_id", myDeviceId)
            addProperty("target_device_id", targetDeviceId)
            addProperty("session_id", sessionId)
        }
        sendMessage(msg)
    }

    fun acceptCall(callerDeviceId: String, sessionId: String) {
        val msg = JsonObject().apply {
            addProperty("type", "call_accept")
            addProperty("sender_device_id", myDeviceId)
            addProperty("target_device_id", callerDeviceId)
            addProperty("session_id", sessionId)
        }
        sendMessage(msg)
    }

    fun rejectCall(callerDeviceId: String, sessionId: String) {
        val msg = JsonObject().apply {
            addProperty("type", "call_reject")
            addProperty("sender_device_id", myDeviceId)
            addProperty("target_device_id", callerDeviceId)
            addProperty("session_id", sessionId)
        }
        sendMessage(msg)
    }

    fun sendOffer(targetDeviceId: String, sessionId: String, sdp: String) {
        val msg = JsonObject().apply {
            addProperty("type", "offer")
            addProperty("sender_device_id", myDeviceId)
            addProperty("target_device_id", targetDeviceId)
            addProperty("session_id", sessionId)
            addProperty("sdp", sdp)
            addProperty("sdp_type", "offer")
        }
        sendMessage(msg)
    }

    fun sendAnswer(targetDeviceId: String, sessionId: String, sdp: String) {
        val msg = JsonObject().apply {
            addProperty("type", "answer")
            addProperty("sender_device_id", myDeviceId)
            addProperty("target_device_id", targetDeviceId)
            addProperty("session_id", sessionId)
            addProperty("sdp", sdp)
            addProperty("sdp_type", "answer")
        }
        sendMessage(msg)
    }

    fun sendIceCandidate(targetDeviceId: String, sessionId: String, sdpMid: String?, sdpMLineIndex: Int, candidate: String) {
        val candObj = JsonObject().apply {
            addProperty("sdpMid", sdpMid)
            addProperty("sdpMLineIndex", sdpMLineIndex)
            addProperty("candidate", candidate)
        }
        val msg = JsonObject().apply {
            addProperty("type", "ice_candidate")
            addProperty("sender_device_id", myDeviceId)
            addProperty("target_device_id", targetDeviceId)
            addProperty("session_id", sessionId)
            add("candidate", candObj)
        }
        sendMessage(msg)
    }

    fun sendCallEnd(targetDeviceId: String, sessionId: String) {
        val msg = JsonObject().apply {
            addProperty("type", "call_end")
            addProperty("sender_device_id", myDeviceId)
            addProperty("target_device_id", targetDeviceId)
            addProperty("session_id", sessionId)
        }
        sendMessage(msg)
    }

    private fun sendMessage(json: JsonObject) {
        val text = json.toString()
        val success = webSocket?.send(text) ?: false
        if (!success) {
            Log.w(TAG, "Failed to send signaling message (WebSocket not ready): $text")
        }
    }
}
