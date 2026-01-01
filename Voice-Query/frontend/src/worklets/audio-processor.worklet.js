// src/worklets/audio-processor.worklet.js

/**
 * AudioWorklet processor for real-time audio capture
 * Runs in separate audio thread for low-latency processing
 * 
 * Responsibilities:
 * - Downsample from mic sample rate (typically 48kHz) to 16kHz
 * - Convert stereo to mono
 * - Convert Float32 to Int16 (PCM format)
 * - Calculate RMS for volume detection
 * - Send processed chunks to main thread
 */

class AudioProcessor extends AudioWorkletProcessor {
    constructor() {
        super();

        // Target sample rate for AWS Transcribe
        this.targetSampleRate = 16000;

        // Buffer for downsampling
        this.buffer = [];

        // Downsampling ratio (e.g., 48000/16000 = 3)
        this.downsampleRatio = sampleRate / this.targetSampleRate;

        // Counter for downsampling
        this.sampleCount = 0;
    }

    /**
     * Process audio in 128-sample chunks (called ~375 times per second at 48kHz)
     */
    process(inputs, outputs, parameters) {
        const input = inputs[0];

        // No input means microphone disconnected
        if (!input || input.length === 0) {
            return true;
        }

        // Get first channel (mono, or left channel if stereo)
        const inputChannel = input[0];

        if (!inputChannel) {
            return true;
        }

        // Process each sample
        for (let i = 0; i < inputChannel.length; i++) {
            this.sampleCount++;

            // Downsample: only keep every Nth sample
            if (this.sampleCount >= this.downsampleRatio) {
                this.sampleCount = 0;

                // Get sample value (Float32 between -1.0 and 1.0)
                const sample = inputChannel[i];

                // Convert to Int16 (PCM format: -32768 to 32767)
                const int16Sample = Math.max(-32768, Math.min(32767, Math.floor(sample * 32768)));

                this.buffer.push(int16Sample);
            }
        }

        // Send buffer when it reaches ~100ms worth of audio (1600 samples at 16kHz)
        const targetBufferSize = 1600; // 100ms at 16kHz

        if (this.buffer.length >= targetBufferSize) {
            // Calculate RMS (Root Mean Square) for volume detection
            const rms = this.calculateRMS(this.buffer);

            // Create Int16Array from buffer
            const audioData = new Int16Array(this.buffer);

            // Send to main thread
            this.port.postMessage({
                audioData: audioData.buffer, // Transfer as ArrayBuffer
                rms: rms,
                timestamp: currentTime
            }, [audioData.buffer]); // Transfer ownership for efficiency

            // Clear buffer
            this.buffer = [];
        }

        // Return true to keep processor alive
        return true;
    }

    /**
     * Calculate Root Mean Square for volume level
     * Returns value between 0.0 (silence) and 1.0 (max volume)
     */
    calculateRMS(samples) {
        if (samples.length === 0) return 0;

        let sumSquares = 0;
        for (let i = 0; i < samples.length; i++) {
            // Normalize Int16 back to -1.0 to 1.0 range
            const normalized = samples[i] / 32768;
            sumSquares += normalized * normalized;
        }

        return Math.sqrt(sumSquares / samples.length);
    }
}

// Register the processor
registerProcessor('audio-processor', AudioProcessor);