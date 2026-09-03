package com.guardianshield.audio

import java.util.concurrent.CopyOnWriteArrayList
import java.util.concurrent.atomic.AtomicLong
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Thread-safe circular PCM buffer with fan-out listener dispatch.
 * Keeps a rolling window of recent audio frames and exposes real-time audio metrics.
 */
class PCMBuffer(private val maxFrameCapacity: Int = 500) { // 500 frames * 20ms = 10 seconds rolling audio

    private val ringBuffer = ArrayDeque<AudioFrame>(maxFrameCapacity)
    private val bufferLock = Any()

    private val listeners = CopyOnWriteArrayList<AudioFrameListener>()

    val totalFramesIngested = AtomicLong(0)
    val totalBytesIngested = AtomicLong(0)

    // Observable live audio metrics for UI visualizer
    private val _currentRms = MutableStateFlow(0f)
    val currentRms: StateFlow<Float> = _currentRms.asStateFlow()

    private val _currentDecibels = MutableStateFlow(-100f)
    val currentDecibels: StateFlow<Float> = _currentDecibels.asStateFlow()

    /**
     * Ingests a new standardized 16kHz mono AudioFrame, updates metrics,
     * stores it in the rolling buffer, and dispatches to all registered listeners.
     */
    fun pushFrame(frame: AudioFrame) {
        synchronized(bufferLock) {
            if (ringBuffer.size >= maxFrameCapacity) {
                ringBuffer.removeFirst()
            }
            ringBuffer.addLast(frame)
        }

        totalFramesIngested.incrementAndGet()
        totalBytesIngested.addAndGet(frame.pcmData.size.toLong())

        // Calculate and emit live RMS audio energy
        val rms = AudioContract.calculateRms(frame.pcmData)
        val db = AudioContract.calculateDecibels(rms)
        _currentRms.value = rms
        _currentDecibels.value = db

        // Fan-out to all listeners (e.g., visualizer, future Layer 1, Layer 2)
        for (listener in listeners) {
            try {
                listener.onAudioFrame(frame)
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    /**
     * Registers a downstream listener for real-time audio frames.
     */
    fun addListener(listener: AudioFrameListener) {
        if (!listeners.contains(listener)) {
            listeners.add(listener)
        }
    }

    /**
     * Unregisters a downstream listener.
     */
    fun removeListener(listener: AudioFrameListener) {
        listeners.remove(listener)
    }

    /**
     * Retrieves a contiguous byte array of the last [durationSeconds] worth of audio.
     */
    fun getRecentAudioBytes(durationSeconds: Float): ByteArray {
        val requiredFrames = (durationSeconds * 1000 / AudioContract.FRAME_DURATION_MS).toInt()
        synchronized(bufferLock) {
            val framesToTake = ringBuffer.takeLast(requiredFrames)
            val totalBytes = framesToTake.sumOf { it.pcmData.size }
            val result = ByteArray(totalBytes)
            var offset = 0
            for (frame in framesToTake) {
                System.arraycopy(frame.pcmData, 0, result, offset, frame.pcmData.size)
                offset += frame.pcmData.size
            }
            return result
        }
    }

    /**
     * Clears buffer and resets statistics.
     */
    fun clear() {
        synchronized(bufferLock) {
            ringBuffer.clear()
        }
        totalFramesIngested.set(0)
        totalBytesIngested.set(0)
        _currentRms.value = 0f
        _currentDecibels.value = -100f
    }
}
