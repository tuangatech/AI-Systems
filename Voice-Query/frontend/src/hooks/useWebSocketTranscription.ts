// src/hooks/useWebSocketTranscription.ts

import { useState, useRef, useCallback, useEffect } from 'react';
import { TranscriptMessage, TranscriptType, ErrorType } from '../types';
import { CONFIG } from '../utils/constants';

interface UseWebSocketTranscriptionReturn {
    connect: () => Promise<void>;  // Returns Promise<void>
    disconnect: () => void;
    sendAudio: (audioData: ArrayBuffer) => void;
    sendEndSignal: () => void;
    resetTranscript: () => void;  // NEW: Reset function
    transcript: string;
    transcriptType: TranscriptType | null;
    isConnected: boolean;
    error: ErrorType | null;
}

export const useWebSocketTranscription = (): UseWebSocketTranscriptionReturn => {
    const [transcript, setTranscript] = useState<string>('');
    const [transcriptType, setTranscriptType] = useState<TranscriptType | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [error, setError] = useState<ErrorType | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    /**
     * Connect to WebSocket server
     * Returns a Promise that resolves when connected or rejects on error
     */
    const connect = useCallback((): Promise<void> => {
        // Don't reconnect if already connected
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            console.log('WebSocket already connected');
            return Promise.resolve();
        }

        return new Promise<void>((resolve, reject) => {
            try {
                console.log('Creating WebSocket connection to:', CONFIG.WS_ENDPOINT);
                const ws = new WebSocket(CONFIG.WS_ENDPOINT);

                // Set timeout for connection
                const connectionTimeout = setTimeout(() => {
                    console.error('❌ WebSocket connection timeout');
                    ws.close();
                    reject(new Error('WebSocket connection timeout'));
                }, 5000);

                ws.onopen = () => {
                    clearTimeout(connectionTimeout);
                    console.log('✅ WebSocket connected to:', CONFIG.WS_ENDPOINT);
                    setIsConnected(true);
                    setError(null);
                    resolve();
                };

                ws.onmessage = (event) => {
                    try {
                        const message: TranscriptMessage = JSON.parse(event.data);

                        if (message.type === 'partial' && message.text) {
                            console.log('📝 Partial transcript:', message.text);
                            setTranscript(message.text);
                            setTranscriptType('partial');
                        } else if (message.type === 'final' && message.text) {
                            console.log('✅ Final transcript:', message.text);
                            setTranscript(message.text);
                            setTranscriptType('final');
                        } else if (message.type === 'error') {
                            console.error('❌ Transcription error:', message.message);
                            setError('transcription_failed');
                        }
                    } catch (err) {
                        console.error('Error parsing WebSocket message:', err);
                    }
                };

                ws.onerror = (event) => {
                    clearTimeout(connectionTimeout);
                    console.error('❌ WebSocket error:', event);
                    setError('websocket_disconnect');
                    setIsConnected(false);
                    reject(new Error('WebSocket connection failed'));
                };

                ws.onclose = (event) => {
                    console.log('🔌 WebSocket closed:', event.code, event.reason);
                    setIsConnected(false);

                    // Only set error if it wasn't a clean close
                    if (!event.wasClean) {
                        setError('websocket_disconnect');
                    }
                };

                wsRef.current = ws;

            } catch (err) {
                console.error('Error creating WebSocket:', err);
                setError('websocket_disconnect');
                reject(err);
            }
        });
    }, []);

    /**
     * Disconnect from WebSocket server
     */
    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
        }

        if (wsRef.current) {
            if (wsRef.current.readyState === WebSocket.OPEN) {
                wsRef.current.close(1000, 'Client disconnecting');
            }
            wsRef.current = null;
        }

        setIsConnected(false);
    }, []);

    /**
     * Send audio data to server
     */
    const sendAudio = useCallback((audioData: ArrayBuffer) => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            try {
                wsRef.current.send(audioData);
            } catch (err) {
                console.error('Error sending audio data:', err);
                setError('websocket_disconnect');
            }
        } else {
            console.warn('WebSocket not open, cannot send audio. State:', wsRef.current?.readyState);
        }
    }, []);

    /**
     * Send end of stream signal to server
     */
    const sendEndSignal = useCallback(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
            try {
                const endMessage = JSON.stringify({ type: 'end_stream' });
                wsRef.current.send(endMessage);
                console.log('📤 Sent end_stream signal');
            } catch (err) {
                console.error('Error sending end signal:', err);
            }
        }
    }, []);

    /**
     * Reset transcript state (for new query)
     */
    const resetTranscript = useCallback(() => {
        setTranscript('');
        setTranscriptType(null);
        setError(null);
    }, []);

    /**
     * Cleanup on unmount
     */
    useEffect(() => {
        return () => {
            disconnect();
        };
    }, [disconnect]);

    return {
        connect,
        disconnect,
        sendAudio,
        sendEndSignal,
        resetTranscript,  // NEW: Export reset function
        transcript,
        transcriptType,
        isConnected,
        error,
    };
};