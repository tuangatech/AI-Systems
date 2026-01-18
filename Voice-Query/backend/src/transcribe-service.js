/**
 * AWS Transcribe Streaming Service
 * Manages audio streaming to AWS Transcribe and handles transcript events
 */

const {
    TranscribeStreamingClient,
    StartStreamTranscriptionCommand
} = require('@aws-sdk/client-transcribe-streaming');
const { createLogger } = require('./utils/logger');

// Transcribe configuration
const TRANSCRIBE_CONFIG = {
    region: process.env.AWS_REGION || 'us-east-1',
    languageCode: 'en-US',
    mediaSampleRateHertz: 16000,
    mediaEncoding: 'pcm'
};

// Timeout for waiting for final transcript after stream ends
const FINAL_TRANSCRIPT_TIMEOUT = parseInt(process.env.TRANSCRIBE_TIMEOUT_MS || '5000', 10);

/**
 * TranscribeSession manages a single streaming session to AWS Transcribe
 */
class TranscribeSession {
    constructor(sessionId, onTranscript, onError) {
        this.sessionId = sessionId;
        this.logger = createLogger(sessionId);
        this.onTranscript = onTranscript; // Callback for transcript events
        this.onError = onError; // Callback for errors

        this.client = new TranscribeStreamingClient({ region: TRANSCRIBE_CONFIG.region });
        this.audioStream = null;
        this.isActive = false;
        this.finalTranscriptReceived = false;
        this.finalTranscriptTimer = null;
    }

    /**
     * Start the Transcribe streaming session
     */
    async start() {
        try {
            this.logger.info('Starting Transcribe stream');
            this.isActive = true;

            // Create async generator for audio stream
            const audioStream = this.createAudioStream();
            this.audioStream = audioStream;

            // Configure Transcribe command
            const command = new StartStreamTranscriptionCommand({
                LanguageCode: TRANSCRIBE_CONFIG.languageCode,
                MediaSampleRateHertz: TRANSCRIBE_CONFIG.mediaSampleRateHertz,
                MediaEncoding: TRANSCRIBE_CONFIG.mediaEncoding,
                AudioStream: audioStream,
                EnablePartialResultsStabilization: true,
                PartialResultsStability: 'medium'
            });

            // Start streaming
            const response = await this.client.send(command);

            // Process transcript events
            await this.processTranscriptStream(response.TranscriptResultStream);

            this.logger.info('Transcribe stream ended successfully');
        } catch (error) {
            this.logger.error('Transcribe stream error', { error: error.message });
            this.handleError(error);
        } finally {
            this.cleanup();
        }
    }

    /**
     * Create async generator for audio streaming
     * This generator yields audio chunks as they're pushed via sendAudio()
     */
    async *createAudioStream() {
        const audioQueue = [];
        let resolveNext = null;
        let streamEnded = false;

        // Store references for external access
        this.pushAudio = (chunk) => {
            if (streamEnded) return;

            audioQueue.push(chunk);
            if (resolveNext) {
                resolveNext();
                resolveNext = null;
            }
        };

        this.endAudioStream = () => {
            streamEnded = true;
            if (resolveNext) {
                resolveNext();
                resolveNext = null;
            }
        };

        // Yield audio chunks as they arrive
        while (!streamEnded || audioQueue.length > 0) {
            if (audioQueue.length > 0) {
                const chunk = audioQueue.shift();
                this.logger.debug('Yielding audio chunk', { size: chunk.length });
                yield { AudioEvent: { AudioChunk: chunk } };
            } else if (!streamEnded) {
                // Wait for next chunk
                await new Promise(resolve => { resolveNext = resolve; });
            }
        }

        this.logger.debug('Audio stream generator completed');
    }

    /**
     * Send audio chunk to Transcribe
     */
    sendAudio(audioChunk) {
        if (!this.isActive) {
            this.logger.warn('Attempted to send audio to inactive session');
            return;
        }

        if (!this.pushAudio) {
            this.logger.error('Audio stream not initialized');
            return;
        }

        this.pushAudio(audioChunk);
    }

    /**
     * Signal end of audio stream and wait for final transcript
     */
    endStream() {
        if (!this.isActive) {
            this.logger.warn('Attempted to end inactive session');
            return;
        }

        this.logger.info('Ending audio stream, waiting for final transcript');

        // Signal end of audio stream
        if (this.endAudioStream) {
            this.endAudioStream();
        }

        // Start timeout timer for final transcript
        this.startFinalTranscriptTimer();
    }

    /**
     * Process transcript events from Transcribe
     */
    async processTranscriptStream(transcriptStream) {
        try {
            for await (const event of transcriptStream) {
                if (event.TranscriptEvent) {
                    const results = event.TranscriptEvent.Transcript.Results;

                    if (results && results.length > 0) {
                        const result = results[0];

                        if (result.Alternatives && result.Alternatives.length > 0) {
                            const transcript = result.Alternatives[0].Transcript;

                            if (result.IsPartial) {
                                // Partial transcript
                                this.logger.debug('Partial transcript received', { text: transcript });
                                this.onTranscript({
                                    type: 'partial',
                                    text: transcript
                                });
                            } else {
                                // Final transcript
                                this.logger.info('Final transcript received', { text: transcript });
                                this.finalTranscriptReceived = true;
                                this.clearFinalTranscriptTimer();

                                this.onTranscript({
                                    type: 'final',
                                    text: transcript
                                });
                            }
                        }
                    }
                }
            }
        } catch (error) {
            this.logger.error('Error processing transcript stream', { error: error.message });
            throw error;
        }
    }

    /**
     * Start timer to handle final transcript timeout
     */
    startFinalTranscriptTimer() {
        this.finalTranscriptTimer = setTimeout(() => {
            if (!this.finalTranscriptReceived) {
                this.logger.warn('Final transcript timeout - no response from Transcribe');
                this.onError(new Error('Transcription timeout - no final transcript received'));
            }
        }, FINAL_TRANSCRIPT_TIMEOUT);
    }

    /**
     * Clear final transcript timer
     */
    clearFinalTranscriptTimer() {
        if (this.finalTranscriptTimer) {
            clearTimeout(this.finalTranscriptTimer);
            this.finalTranscriptTimer = null;
        }
    }

    /**
     * Handle errors
     */
    handleError(error) {
        this.isActive = false;
        this.onError(error);
    }

    /**
     * Clean up resources
     */
    cleanup() {
        this.logger.debug('Cleaning up Transcribe session');
        this.isActive = false;
        this.clearFinalTranscriptTimer();
        this.audioStream = null;
        this.pushAudio = null;
        this.endAudioStream = null;
    }
}

/**
 * Create a new Transcribe session
 * @param {string} sessionId - Unique session identifier
 * @param {Function} onTranscript - Callback for transcript events: (transcript) => void
 * @param {Function} onError - Callback for errors: (error) => void
 * @returns {TranscribeSession}
 */
const createTranscribeSession = (sessionId, onTranscript, onError) => {
    return new TranscribeSession(sessionId, onTranscript, onError);
};

module.exports = {
    createTranscribeSession,
    TRANSCRIBE_CONFIG
};