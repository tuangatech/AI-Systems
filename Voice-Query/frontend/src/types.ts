/**
 * Input modes for the query interface
 */
export type InputMode = 'keyboard' | 'voice';

/**
 * Recording states for voice input
 */
export type RecordingState = 'idle' | 'recording' | 'processing' | 'error';

/**
 * Processing states for query submission
 */
export type ProcessingState = 'idle' | 'processing' | 'generating' | 'complete';

/**
 * Transcript types from AWS Transcribe
 */
export type TranscriptType = 'partial' | 'final';

/**
 * WebSocket message from server
 */
export interface TranscriptMessage {
    type: 'partial' | 'final' | 'error';
    text?: string;
    message?: string;
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
 * Query submission result
 */
export interface QueryResult {
    query: string;
    response: string;
    timestamp: Date;
}