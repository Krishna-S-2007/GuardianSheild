package com.guardianshield.audio

import java.io.ByteArrayOutputStream

/**
 * Adapts incoming WebRTC PCM audio samples (which may arrive at 48kHz stereo/mono in arbitrary frame sizes)
 * into standardized 16kHz 16-bit Mono Linear PCM 20ms frames (640 bytes).
 */
class AudioAdapter {

    private val pendingBuffer = ByteArrayOutputStream()
    private val lock = Any()

    /**
     * Ingests raw PCM bytes from WebRTC, resamples/downmixes them to 16kHz mono,
     * and partitions them into standardized 20ms frames.
     *
     * @param inputBytes Raw PCM data from WebRTC sink
     * @param inputSampleRate Native sample rate (e.g., 48000, 44100, or 16000)
     * @param inputChannels Channel count (1 for mono, 2 for stereo)
     * @return List of standardized 16kHz mono 20ms AudioFrames
     */
    fun processIncomingPcm(
        inputBytes: ByteArray,
        inputSampleRate: Int,
        inputChannels: Int
    ): List<AudioFrame> {
        val readyFrames = mutableListOf<AudioFrame>()
        if (inputBytes.isEmpty()) return readyFrames

        // 1. Convert byte array to 16-bit short samples
        val inputShorts = bytesToShorts(inputBytes)

        // 2. Downmix to Mono if stereo
        val monoShorts = if (inputChannels > 1) {
            downmixToMono(inputShorts, inputChannels)
        } else {
            inputShorts
        }

        // 3. Resample to 16kHz if necessary
        val resampledShorts = if (inputSampleRate != AudioContract.SAMPLE_RATE) {
            resampleLinear(monoShorts, inputSampleRate, AudioContract.SAMPLE_RATE)
        } else {
            monoShorts
        }

        // 4. Convert standardized samples back to 16-bit Little-Endian bytes
        val standardBytes = shortsToBytes(resampledShorts)

        // 5. Buffer and slice into exact 20ms frames (640 bytes = 320 samples)
        synchronized(lock) {
            pendingBuffer.write(standardBytes)
            val allBuffered = pendingBuffer.toByteArray()
            var offset = 0
            val frameSize = AudioContract.BYTES_PER_FRAME // 640 bytes

            while (offset + frameSize <= allBuffered.size) {
                val frameBytes = allBuffered.copyOfRange(offset, offset + frameSize)
                readyFrames.add(AudioFrame(pcmData = frameBytes))
                offset += frameSize
            }

            pendingBuffer.reset()
            if (offset < allBuffered.size) {
                pendingBuffer.write(allBuffered, offset, allBuffered.size - offset)
            }
        }

        return readyFrames
    }

    private fun bytesToShorts(bytes: ByteArray): ShortArray {
        val shorts = ShortArray(bytes.size / 2)
        for (i in shorts.indices) {
            val low = bytes[i * 2].toInt() and 0xFF
            val high = bytes[i * 2 + 1].toInt()
            shorts[i] = ((high shl 8) or low).toShort()
        }
        return shorts
    }

    private fun shortsToBytes(shorts: ShortArray): ByteArray {
        val bytes = ByteArray(shorts.size * 2)
        for (i in shorts.indices) {
            val sample = shorts[i].toInt()
            bytes[i * 2] = (sample and 0xFF).toByte()
            bytes[i * 2 + 1] = ((sample ushr 8) and 0xFF).toByte()
        }
        return bytes
    }

    private fun downmixToMono(stereoShorts: ShortArray, channels: Int): ShortArray {
        val monoLength = stereoShorts.size / channels
        val mono = ShortArray(monoLength)
        for (i in 0 until monoLength) {
            var sum = 0
            for (c in 0 until channels) {
                sum += stereoShorts[i * channels + c].toInt()
            }
            mono[i] = (sum / channels).toShort()
        }
        return mono
    }

    /**
     * Fast, lightweight linear interpolation resampler for zero-latency mobile execution.
     */
    private fun resampleLinear(input: ShortArray, fromRate: Int, toRate: Int): ShortArray {
        if (input.isEmpty()) return ShortArray(0)
        val ratio = fromRate.toDouble() / toRate.toDouble()
        val outputLength = (input.size / ratio).toInt()
        val output = ShortArray(outputLength)

        for (i in 0 until outputLength) {
            val srcPos = i * ratio
            val srcIndex = srcPos.toInt()
            val fraction = srcPos - srcIndex

            if (srcIndex + 1 < input.size) {
                val s0 = input[srcIndex].toDouble()
                val s1 = input[srcIndex + 1].toDouble()
                output[i] = (s0 + fraction * (s1 - s0)).toInt().toShort()
            } else if (srcIndex < input.size) {
                output[i] = input[srcIndex]
            }
        }
        return output
    }

    fun reset() {
        synchronized(lock) {
            pendingBuffer.reset()
        }
    }
}
