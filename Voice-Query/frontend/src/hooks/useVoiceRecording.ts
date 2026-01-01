// src/hooks/useVoiceRecording.ts

import { useState, useRef, useCallback } from 'react';
import { ErrorType } from '../types';
import { CONFIG } from '../utils/constants';

interface AudioChunk {
    audioData: ArrayBuffer;
    rms: number;
    timestamp: number;
}

interface UseVoiceRecordingReturn {
    startRecording: () => Promise<void>;
    stopRecording: () => void;
    isRecording: boolean;
    audioLevel: number;
    error: ErrorType | null;
    recordingDuration: number;
}

export const useVoiceRecording = (
    onAudioChunk?: (chunk: AudioChunk) => void
): UseVoiceRecordingReturn => {
    const [isRecording, setIsRecording] = useState(false);
    const [audioLevel, setAudioLevel] = useState(0);
    const [error, setError] = useState<ErrorType | null>(null);
    const [recordingDuration, setRecordingDuration] = useState(0);

    // Refs for audio context and streams (don't trigger re-renders)
    const audioContextRef = useRef<AudioContext | null>(null);
    const mediaStreamRef = useRef<MediaStream | null>(null);
    const workletNodeRef = useRef<AudioWorkletNode | null>(null);
    const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
    const startTimeRef = useRef<number>(0);
    const durationTimerRef = useRef<NodeJS.Timeout | null>(null);

    /**
     * Request microphone permission and start recording
     */
    const startRecording = useCallback(async () => {
        try {
            setError(null);

            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1, // Mono
                    sampleRate: CONFIG.AUDIO_SAMPLE_RATE, // Request 16kHz if supported
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });

            mediaStreamRef.current = stream;

            // Create AudioContext with target sample rate
            const audioContext = new AudioContext({
                sampleRate: CONFIG.AUDIO_SAMPLE_RATE,
            });
            audioContextRef.current = audioContext;

            // Load AudioWorklet module
            await audioContext.audioWorklet.addModule(
                `${process.env.PUBLIC_URL}/audio-processor.worklet.js`
            );

            // Create AudioWorklet node
            const workletNode = new AudioWorkletNode(audioContext, 'audio-processor');
            workletNodeRef.current = workletNode;

            // Handle messages from AudioWorklet
            workletNode.port.onmessage = (event) => {
                const { audioData, rms, timestamp } = event.data;

                // Update audio level for visualization
                setAudioLevel(rms);

                // Send chunk to parent (for WebSocket transmission in Phase 3)
                if (onAudioChunk) {
                    onAudioChunk({ audioData, rms, timestamp });
                }
            };

            // Create source from microphone stream
            const source = audioContext.createMediaStreamSource(stream);
            sourceNodeRef.current = source;

            // Connect: Microphone -> AudioWorklet -> (nowhere, we just process)
            source.connect(workletNode);
            // Note: We don't connect to destination (speakers) to avoid feedback

            // Start recording timer
            startTimeRef.current = Date.now();
            durationTimerRef.current = setInterval(() => {
                const duration = Date.now() - startTimeRef.current;
                setRecordingDuration(duration);

                // Auto-stop at max duration
                if (duration >= CONFIG.MAX_RECORDING_DURATION) {
                    stopRecording();
                }
            }, 100); // Update every 100ms

            setIsRecording(true);

        } catch (err) {
            console.error('Error starting recording:', err);

            if (err instanceof Error) {
                if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                    setError('mic_permission_denied');
                } else {
                    setError('transcription_failed');
                }
            }

            cleanup();
        }
    }, [onAudioChunk]);

    /**
     * Stop recording and cleanup resources
     */
    const stopRecording = useCallback(() => {
        cleanup();
        setIsRecording(false);
        setAudioLevel(0);
        setRecordingDuration(0);
    }, []);

    /**
     * Cleanup all audio resources
     */
    const cleanup = useCallback(() => {
        // Stop duration timer
        if (durationTimerRef.current) {
            clearInterval(durationTimerRef.current);
            durationTimerRef.current = null;
        }

        // Disconnect audio nodes
        if (workletNodeRef.current) {
            workletNodeRef.current.port.onmessage = null;
            workletNodeRef.current.disconnect();
            workletNodeRef.current = null;
        }

        if (sourceNodeRef.current) {
            sourceNodeRef.current.disconnect();
            sourceNodeRef.current = null;
        }

        // Stop microphone stream
        if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach(track => track.stop());
            mediaStreamRef.current = null;
        }

        // Close audio context
        if (audioContextRef.current) {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }
    }, []);

    return {
        startRecording,
        stopRecording,
        isRecording,
        audioLevel,
        error,
        recordingDuration,
    };
};