// src/utils/constants.ts
// UPDATED VERSION with WebSocket endpoint from environment variable

export const CONFIG = {
    // WebSocket endpoint from Terraform output
    WS_ENDPOINT: process.env.REACT_APP_WS_ENDPOINT || 'ws://localhost:8080',

    // Recording settings
    MAX_RECORDING_DURATION: 30000, // 30 seconds in milliseconds
    SILENCE_DURATION: 2000, // 2 seconds of silence
    MIN_RECORDING_DURATION: 500, // 0.5 seconds minimum

    // VAD settings
    VAD_THRESHOLD: 0.01, // RMS threshold for silence detection
    VAD_SAMPLE_INTERVAL: 100, // Sample audio every 100ms

    // Audio settings
    AUDIO_SAMPLE_RATE: 16000,
    AUDIO_CHANNELS: 1, // Mono
    AUDIO_BIT_DEPTH: 16,

    // Mock response settings
    MOCK_RESPONSE_DELAY: {
        PROCESSING: 2000, // "Processing your query..." delay
        GENERATING: 1000, // "Generating answer..." delay
    },

    // Transcription timeout
    TRANSCRIPTION_TIMEOUT: 5000, // 5 seconds after audio stops
} as const;

export const UI_TEXT = {
    LISTENING: 'Listening...',
    PROCESSING: 'Processing transcription...',
    MAX_DURATION_REACHED: 'Maximum recording time reached',
    NO_TRANSCRIPTION: "I didn't catch that. Please try again.",
    PROCESSING_QUERY: 'Processing your query...',
    GENERATING_ANSWER: 'Generating answer...',
} as const;

export const ERROR_MESSAGES = {
    MIC_PERMISSION_DENIED: 'Microphone access denied. Please grant permission to use voice input.',
    WEBSOCKET_DISCONNECT: 'Connection lost. Please try again.',
    TRANSCRIPTION_TIMEOUT: 'No response from transcription service.',
    TRANSCRIPTION_FAILED: 'Transcription failed. Please try again.',
} as const;