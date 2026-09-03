package com.guardianshield.network

import android.util.Log
import com.google.gson.Gson
import com.google.gson.JsonObject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.util.concurrent.TimeUnit

class ApiClient {
    private val TAG = "ApiClient"
    private val gson = Gson()
    private val client = OkHttpClient.Builder()
        .connectTimeout(5, TimeUnit.SECONDS)
        .readTimeout(5, TimeUnit.SECONDS)
        .build()

    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    suspend fun checkHealth(backendHost: String): Boolean = withContext(Dispatchers.IO) {
        val url = "http://${normalizeHost(backendHost)}/api/health"
        try {
            val request = Request.Builder().url(url).get().build()
            val response = client.newCall(request).execute()
            response.isSuccessful
        } catch (e: Exception) {
            Log.e(TAG, "Health check failed for $url: ${e.message}")
            false
        }
    }

    suspend fun registerDevice(backendHost: String, deviceId: String, userName: String): Boolean =
        withContext(Dispatchers.IO) {
            val url = "http://${normalizeHost(backendHost)}/api/signaling/register"
            val payload = JsonObject().apply {
                addProperty("device_id", deviceId)
                addProperty("user_name", userName)
            }
            try {
                val body = payload.toString().toRequestBody(jsonMediaType)
                val request = Request.Builder().url(url).post(body).build()
                val response = client.newCall(request).execute()
                response.isSuccessful
            } catch (e: Exception) {
                Log.e(TAG, "Device registration failed: ${e.message}")
                false
            }
        }

    private fun normalizeHost(host: String): String {
        return host.trim()
            .removePrefix("http://")
            .removePrefix("https://")
            .removePrefix("ws://")
            .removePrefix("wss://")
    }
}
