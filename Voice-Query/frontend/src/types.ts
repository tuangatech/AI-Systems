// src/types.ts
// Consolidated type definitions for the application

/**
 * Input modes for the query interface
 */
export type InputMode = 'keyboard' | 'voice';

/**
 * Recording states for voice input
 */
export type RecordingState = 'idle' | 'recording' | 'processing' | 'error';

/**
 * Processing states for query submission (legacy - kept for compatibility)
 */
export type ProcessingState = 'idle' | 'processing' | 'generating' | 'complete';

/**
 * Conversation state machine for voice-to-voice interaction
 */
export type ConversationState =
    | 'idle'              // Ready for user input
    | 'user_recording'    // User is speaking
    | 'processing'        // Transcription finalized, sending query
    | 'bot_generating'    // Waiting for backend response
    | 'bot_speaking'      // Playing TTS audio
    | 'error';            // Any failure state

/**
 * Transcript types from AWS Transcribe
 */
export type TranscriptType = 'partial' | 'final';

/**
 * WebSocket message from server
 */
export interface TranscriptMessage {
    type: 'partial' | 'final' | 'error' | 'ready';
    text?: string;
    message?: string;
    sessionId?: string;
}

/**
 * Error types for user-facing error handling
 */
export type ErrorType =
    | 'mic_permission_denied'
    | 'websocket_disconnect'
    | 'transcription_timeout'
    | 'transcription_failed'
    | null;

/**
 * Query submission result (legacy - kept for compatibility)
 */
export interface QueryResult {
    query: string;
    response: string;
    timestamp: Date;
}

/**
 * Bot response from backend query API
 */
export interface BotResponse {
    success: boolean;
    text: string;
    audio: string | null;  // data:audio/mp3;base64,...
    duration: number | null;  // Audio duration in seconds
    format?: string;
    voiceId?: string;
    metadata?: {
        requestId: string;
        processingTime: number;
        synthesisTime?: number;
        queryLength: number;
        responseLength: number;
        hasAudio: boolean;
        synthesisError?: string;
    };
    error?: string;
}

/**
 * Audio player state
 */
export type AudioPlayerState =
    | 'loading'
    | 'playing'
    | 'paused'
    | 'ended'
    | 'error';