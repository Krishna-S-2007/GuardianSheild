package com.guardianshield.audio

import kotlin.math.log10
import kotlin.math.sqrt

/**
 * Standardized Audio Specifications across GuardianShield.
 * Standard format: 16,000 Hz, 16-bit Linear PCM, Mono, 20ms frame chunking.
 */
object AudioContract {
    const val SAMPLE_RATE = 16000
    const val CHANNELS = 1
    const val BITS_PER_SAMPLE = 16
    const val BYTES_PER_SAMPLE = 2

    // 20ms frames: 16000 * 0.02 = 320 samples = 640 bytes
    const val FRAME_DURATION_MS = 20
    const val SAMPLES_PER_FRAME = (SAMPLE_RATE * FRAME_DURATION_MS) / 1000 // 320 samples
    const val BYTES_PER_FRAME = SAMPLES_PER_FRAME * BYTES_PER_SAMPLE * CHANNELS // 640 bytes

    /**
     * Calculates the Root Mean Square (RMS) energy from 16-bit linear PCM byte array.
     * Normalized between 0.0f (silence) and 1.0f (maximum amplitude).
     */
    fun calculateRms(pcmData: ByteArray): Float {
        if (pcmData.size < 2) return 0f
        var sumSquares = 0.0
        val sampleCount = pcmData.size / 2

        for (i in 0 until sampleCount) {
            val low = pcmData[i * 2].toInt() and 0xFF
            val high = pcmData[i * 2 + 1].toInt()
            val sample = (high shl 8) or low // 16-bit signed integer
            sumSquares += (sample.toDouble() * sample.toDouble())
        }

        val rms = sqrt(sumSquares / sampleCount)
        return (rms / 32768.0).toFloat().coerceIn(0f, 1f)
    }

    /**
     * Calculates decibels (dB) relative to full scale (dBFS).
     */
    fun calculateDecibels(rmsNormalized: Float): Float {
        if (rmsNormalized <= 0.0001f) return -100f
        return (20f * log10(rmsNormalized)).coerceIn(-100f, 0f)
    }
}

/**
 * Represents a single standardized PCM audio frame.
 */
data class AudioFrame(
    val pcmData: ByteArray,
    val timestampMs: Long = System.currentTimeMillis(),
    val sampleRate: Int = AudioContract.SAMPLE_RATE,
    val channels: Int = AudioContract.CHANNELS
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false
        other as AudioFrame
        return pcmData.contentEquals(other.pcmData) && timestampMs == other.timestampMs
    }

    override fun hashCode(): Int {
        var result = pcmData.contentHashCode()
        result = 31 * result + timestampMs.hashCode()
        return result
    }
}

/**
 * Listener interface for downstream audio consumers (e.g. Visualizer, future Layer 1, Layer 2).
 */
fun interface AudioFrameListener {
    fun onAudioFrame(frame: AudioFrame)
}
