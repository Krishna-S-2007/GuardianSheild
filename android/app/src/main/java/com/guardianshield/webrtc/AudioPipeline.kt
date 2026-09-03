package com.guardianshield.webrtc

import android.util.Log
import com.guardianshield.audio.AudioAdapter
import com.guardianshield.audio.PCMBuffer
import org.webrtc.AudioTrack
import org.webrtc.AudioTrackSink
import org.webrtc.audio.JavaAudioDeviceModule

/**
 * WebRTC Remote Audio Interception Pipeline.
 * Connects directly to the incoming WebRTC remote audio track / audio device module,
 * receives raw decoded PCM audio samples, transforms them via AudioAdapter,
 * and feeds them into the PCMBuffer for local analysis.
 */
class AudioPipeline(val pcmBuffer: PCMBuffer = PCMBuffer()) : AudioTrackSink,
    JavaAudioDeviceModule.AudioSamplesReadyCallback {

    private val TAG = "AudioPipeline"
    private val audioAdapter = AudioAdapter()
    private var attachedAudioTrack: AudioTrack? = null

    /**
     * Attaches this pipeline as an AudioTrackSink to a WebRTC remote AudioTrack.
     */
    fun attachToRemoteAudioTrack(audioTrack: AudioTrack) {
        detach()
        this.attachedAudioTrack = audioTrack
        try {
            audioTrack.addSink(this)
            Log.i(TAG, "Successfully attached AudioPipeline sink to remote AudioTrack: ${audioTrack.id()}")
        } catch (e: Exception) {
            Log.e(TAG, "Error attaching sink to AudioTrack: ${e.message}")
        }
    }

    /**
     * Detaches this pipeline from the currently attached AudioTrack.
     */
    fun detach() {
        attachedAudioTrack?.let { track ->
            try {
                track.removeSink(this)
                Log.i(TAG, "Detached AudioPipeline sink from AudioTrack: ${track.id()}")
            } catch (e: Exception) {
                Log.e(TAG, "Error detaching sink: ${e.message}")
            }
        }
        attachedAudioTrack = null
        audioAdapter.reset()
    }

    /**
     * Callback invoked by WebRTC AudioTrackSink when raw PCM audio frames arrive.
     */
    override fun onData(
        audioData: ByteArray?,
        bitsPerSample: Int,
        sampleRate: Int,
        numberOfChannels: Int,
        numberOfFrames: Int
    ) {
        if (audioData == null || audioData.isEmpty()) return

        // Ingest and adapt PCM samples to standardized 16kHz mono 20ms frames
        val frames = audioAdapter.processIncomingPcm(
            inputBytes = audioData,
            inputSampleRate = sampleRate,
            inputChannels = numberOfChannels
        )

        // Push standardized frames into circular PCMBuffer
        for (frame in frames) {
            pcmBuffer.pushFrame(frame)
        }
    }

    /**
     * Callback invoked if using JavaAudioDeviceModule AudioSamplesReadyCallback directly.
     */
    override fun onWebRtcAudioRecordSamplesReady(audioSamples: JavaAudioDeviceModule.AudioSamples?) {
        // Handled if capturing microphone stream
    }
}
