/**
 * WebSocket Connection Handler
 * Manages individual WebSocket connections and routes messages
 * FIXED: Proper async handling for Transcribe session initialization
 */

const { v4: uuidv4 } = require('uuid');
const { createLogger } = require('./utils/logger');
const { createTranscribeSession } = require('./transcribe-service');

// Connection timeout (slightly longer than client's 30s recording limit)
const CONNECTION_TIMEOUT = parseInt(process.env.CONNECTION_TIMEOUT_MS || '35000', 10);

// Inactivity timeout (if no audio received)
const INACTIVITY_TIMEOUT = parseInt(process.env.INACTIVITY_TIMEOUT_MS || '60000', 10);

/**
 * Handle a new WebSocket connection
 */
const handleConnection = (ws, request) => {
    const sessionId = uuidv4();
    const logger = createLogger(sessionId);

    logger.info('WebSocket connection established', {
        remoteAddress: request.socket.remoteAddress
    });

    // Connection state
    const state = {
        sessionId,
        transcribeSession: null,
        startTime: Date.now(),
        isActive: true,
        lastActivityTime: Date.now(),
        connectionTimeout: null,
        inactivityTimeout: null,
        isStartingTranscribe: false,  // NEW: Track if session is being initialized
        audioBuffer: []  // NEW: Buffer audio chunks while session starts
    };

    /**
     * Send message to client
     */
    const sendToClient = (message) => {
        if (ws.readyState === ws.OPEN) {
            ws.send(JSON.stringify(message));
        }
    };

    /**
     * Handle transcript events from Transcribe
     */
    const onTranscript = (transcript) => {
        logger.debug(`Sending ${transcript.type} transcript to client`, {
            text: transcript.text.substring(0, 50) // Log first 50 chars
        });

        sendToClient({
            type: transcript.type,
            text: transcript.text
        });
    };

    /**
     * Handle errors from Transcribe
     */
    const onTranscribeError = (error) => {
        logger.error('Transcribe error', { error: error.message });

        sendToClient({
            type: 'error',
            message: 'Transcription failed. Please try again.'
        });

        // Close connection after error
        setTimeout(() => closeConnection(), 1000);
    };

    /**
     * Start Transcribe session
     * FIXED: Now properly async
     */
    const startTranscribeSession = async () => {
        if (state.isStartingTranscribe || state.transcribeSession) {
            logger.warn('Transcribe session already starting or started');
            return;
        }

        state.isStartingTranscribe = true;

        try {
            logger.info('Creating Transcribe session');

            state.transcribeSession = createTranscribeSession(
                sessionId,
                onTranscript,
                onTranscribeError
            );

            // Start streaming (async, runs in background)
            state.transcribeSession.start().catch(err => {
                logger.error('Failed to start Transcribe session', { error: err.message });
                onTranscribeError(err);
            });

            logger.info('Transcribe session started');

            // NEW: Send any buffered audio chunks
            if (state.audioBuffer.length > 0) {
                logger.info(`Sending ${state.audioBuffer.length} buffered audio chunks to Transcribe`);
                for (const chunk of state.audioBuffer) {
                    state.transcribeSession.sendAudio(chunk);
                }
                state.audioBuffer = [];
            }

        } catch (error) {
            logger.error('Error creating Transcribe session', { error: error.message });
            onTranscribeError(error);
        } finally {
            state.isStartingTranscribe = false;
        }
    };

    /**
     * Handle binary message (audio data)
     * FIXED: Buffer audio while Transcribe starts
     */
    const handleAudioChunk = (audioChunk) => {
        if (!state.isActive) {
            logger.warn('Received audio chunk for inactive connection');
            return;
        }

        state.lastActivityTime = Date.now();
        resetInactivityTimeout();

        // Start Transcribe session on first audio chunk
        if (!state.transcribeSession && !state.isStartingTranscribe) {
            logger.info('First audio chunk received, starting Transcribe session');
            startTranscribeSession();
        }

        // Send audio to Transcribe if ready, otherwise buffer it
        if (state.transcribeSession) {
            logger.debug('Forwarding audio chunk to Transcribe', { size: audioChunk.length });
            state.transcribeSession.sendAudio(audioChunk);
        } else if (state.isStartingTranscribe) {
            // Buffer audio chunks while session is initializing
            logger.debug('Buffering audio chunk while Transcribe starts', { 
                size: audioChunk.length,
                bufferSize: state.audioBuffer.length 
            });
            state.audioBuffer.push(audioChunk);
        }
    };

    /**
     * Handle text message (control signals)
     */
    const handleTextMessage = (message) => {
        try {
            const data = JSON.parse(message);

            if (data.type === 'end_stream') {
                logger.info('Received end_stream signal from client');

                if (state.transcribeSession) {
                    state.transcribeSession.endStream();
                } else {
                    logger.warn('Received end_stream but no active Transcribe session');
                    sendToClient({
                        type: 'error',
                        message: 'No active transcription session'
                    });
                }
            } else {
                logger.warn('Unknown message type received', { type: data.type });
            }
        } catch (error) {
            logger.error('Error parsing text message', { error: error.message });
            sendToClient({
                type: 'error',
                message: 'Invalid message format'
            });
        }
    };

    /**
     * Set connection timeout
     */
    const setConnectionTimeout = () => {
        state.connectionTimeout = setTimeout(() => {
            logger.warn('Connection timeout reached');
            sendToClient({
                type: 'error',
                message: 'Connection timeout'
            });
            closeConnection();
        }, CONNECTION_TIMEOUT);
    };

    /**
     * Set/reset inactivity timeout
     */
    const resetInactivityTimeout = () => {
        if (state.inactivityTimeout) {
            clearTimeout(state.inactivityTimeout);
        }

        state.inactivityTimeout = setTimeout(() => {
            logger.warn('Inactivity timeout - no audio received');
            sendToClient({
                type: 'error',
                message: 'Connection inactive'
            });
            closeConnection();
        }, INACTIVITY_TIMEOUT);
    };

    /**
     * Close connection and clean up resources
     */
    const closeConnection = () => {
        if (!state.isActive) {
            return; // Already closed
        }

        logger.info('Closing connection', {
            duration: Date.now() - state.startTime
        });

        state.isActive = false;

        // Clear timeouts
        if (state.connectionTimeout) {
            clearTimeout(state.connectionTimeout);
        }
        if (state.inactivityTimeout) {
            clearTimeout(state.inactivityTimeout);
        }

        // Clean up Transcribe session
        if (state.transcribeSession) {
            state.transcribeSession.cleanup();
            state.transcribeSession = null;
        }

        // Clear audio buffer
        state.audioBuffer = [];

        // Close WebSocket if still open
        if (ws.readyState === ws.OPEN) {
            ws.close();
        }
    };

    // ===== Event Handlers =====

    ws.on('message', (message, isBinary) => {
        if (isBinary) {
            // Binary message = audio chunk
            handleAudioChunk(message);
        } else {
            // Text message = control signal
            handleTextMessage(message.toString());
        }
    });

    ws.on('close', (code, reason) => {
        logger.info('WebSocket closed by client', {
            code,
            reason: reason.toString()
        });
        closeConnection();
    });

    ws.on('error', (error) => {
        logger.error('WebSocket error', { error: error.message });
        closeConnection();
    });

    // Start timeouts
    setConnectionTimeout();
    resetInactivityTimeout();

    // Send ready signal to client
    sendToClient({
        type: 'ready',
        sessionId: sessionId
    });
};

module.exports = {
    handleConnection
};