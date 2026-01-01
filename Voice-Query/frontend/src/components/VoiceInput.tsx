// src/components/VoiceInput.tsx
// UPDATED VERSION with WebSocket integration

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { InputMode, RecordingState, TranscriptType } from '../types';
import { InputField } from './InputField';
import { AudioVisualizer } from './AudioVisualizer';
import { TranscriptDisplay } from './TranscriptDisplay';
import { ErrorMessage } from './ErrorMessage';
import { useVoiceRecording } from '../hooks/useVoiceRecording';
import { useWebSocketTranscription } from '../hooks/useWebSocketTranscription';
import { useVAD } from '../hooks/useVAD';
import { CONFIG, UI_TEXT } from '../utils/constants';
import './VoiceInput.css';

interface VoiceInputProps {
    value: string;
    onChange: (value: string) => void;
    onSubmit: () => void;
    isProcessing: boolean;
}

export const VoiceInput: React.FC<VoiceInputProps> = ({
    value,
    onChange,
    onSubmit,
    isProcessing,
}) => {
    const [inputMode, setInputMode] = useState<InputMode>('keyboard');
    const [recordingState, setRecordingState] = useState<RecordingState>('idle');
    const [hasTranscriptTimeout, setHasTranscriptTimeout] = useState(false);
    const [isTranscriptEmpty, setIsTranscriptEmpty] = useState(false);
    const [accumulatedTranscript, setAccumulatedTranscript] = useState<string>('');
    const [showVisualizer, setShowVisualizer] = useState<boolean>(true); // NEW: Control visualizer visibility
    
    // Track previous transcript to detect new finals
    const prevTranscriptRef = useRef<{ text: string; type: TranscriptType | null }>({
        text: '',
        type: null
    });

    // WebSocket transcription hook
    const {
        connect: connectWS,
        disconnect: disconnectWS,
        sendAudio,
        sendEndSignal,
        resetTranscript,  // NEW: Get reset function
        transcript,
        transcriptType,
        isConnected,
        error: wsError,
    } = useWebSocketTranscription();

    // Voice recording hook with audio chunk callback
    const handleAudioChunk = useCallback((chunk: { audioData: ArrayBuffer; rms: number; timestamp: number }) => {
        console.log('🎵 Audio chunk received:', { 
            size: chunk.audioData.byteLength, 
            rms: chunk.rms.toFixed(4)
        });
        
        // Send audio to WebSocket (sendAudio checks connection state internally)
        sendAudio(chunk.audioData);
    }, [sendAudio]);

    const {
        startRecording,
        stopRecording,
        isRecording,
        audioLevel,
        error: recordingError,
        recordingDuration,
    } = useVoiceRecording(handleAudioChunk);

    // Voice Activity Detection
    const { shouldAutoStop } = useVAD(audioLevel, recordingDuration, isRecording);

    // Combine errors from recording and WebSocket
    const error = recordingError || wsError;

    // Handle query submission - reset voice state
    const handleSubmit = useCallback(() => {
        // Call parent's onSubmit
        onSubmit();

        // Reset voice-related state
        setAccumulatedTranscript('');
        setRecordingState('idle');
        setHasTranscriptTimeout(false);
        setIsTranscriptEmpty(false);
        setShowVisualizer(false);
        
        // Reset to keyboard mode after submit
        setInputMode('keyboard');
        
        // Reset transcript ref
        prevTranscriptRef.current = { text: '', type: null };

        // Reset WebSocket transcript state
        resetTranscript();

        console.log('✅ Query submitted, voice state reset, switched to keyboard mode');
    }, [onSubmit, resetTranscript]);

    // Auto-stop when VAD detects silence
    useEffect(() => {
        if (shouldAutoStop && isRecording) {
            console.log('🛑 Auto-stopping due to silence');
            handleStopRecording();
        }
    }, [shouldAutoStop, isRecording]);

    // Update input value when transcript changes
    useEffect(() => {
        // Check if this is a NEW final transcript (not the same one we already processed)
        const isNewFinal = 
            transcriptType === 'final' && 
            transcript &&
            (transcript !== prevTranscriptRef.current.text || transcriptType !== prevTranscriptRef.current.type);

        if (isNewFinal) {
            // Append final transcript to accumulated text
            const newAccumulated = accumulatedTranscript 
                ? `${accumulatedTranscript} ${transcript}`
                : transcript;
            
            console.log('📝 Accumulating final transcript:', {
                previous: accumulatedTranscript,
                new: transcript,
                accumulated: newAccumulated
            });
            
            setAccumulatedTranscript(newAccumulated);
            onChange(newAccumulated);
            
            // Update ref to track this transcript as processed
            prevTranscriptRef.current = { text: transcript, type: transcriptType };
        } 
        else if (transcriptType === 'partial' && transcript) {
            // For partial transcripts, just update the ref but don't accumulate
            prevTranscriptRef.current = { text: transcript, type: transcriptType };
        }
    }, [transcript, transcriptType, accumulatedTranscript, onChange]);

    // Update recording state based on isRecording
    useEffect(() => {
        if (isRecording) {
            setRecordingState('recording');
        } else if (recordingState === 'recording') {
            setRecordingState('processing');

            // Set timeout for final transcript
            const timeoutId = setTimeout(() => {
                if (!transcript) {
                    console.warn('⚠️ Transcription timeout - no transcript received');
                    setHasTranscriptTimeout(true);
                    setIsTranscriptEmpty(true);
                }
                setRecordingState('idle');
            }, CONFIG.TRANSCRIPTION_TIMEOUT);

            return () => clearTimeout(timeoutId);
        }
    }, [isRecording, recordingState, transcript]);

    // NEW: Set state back to idle when final transcript arrives
    useEffect(() => {
        if (transcriptType === 'final' && recordingState === 'processing') {
            console.log('✅ Final transcript received, setting state to idle');
            setRecordingState('idle');
        }
    }, [transcriptType, recordingState]);

    // Auto-switch to keyboard mode when user starts typing in voice mode
    const handleInputChange = (newValue: string) => {
        onChange(newValue);

        // If user starts typing while in voice mode (and not currently recording),
        // automatically switch to keyboard mode
        if (inputMode === 'voice' && newValue.length > 0 && !isRecording) {
            setInputMode('keyboard');
        }
    };

    const handleStartRecording = async () => {
        try {
            // Clear previous state
            setHasTranscriptTimeout(false);
            setIsTranscriptEmpty(false);
            setAccumulatedTranscript('');
            setShowVisualizer(true); // NEW: Show visualizer when starting

            console.log('🎤 Starting recording process...');

            // Connect WebSocket and wait for it to be ready
            console.log('📡 Connecting WebSocket...');
            await connectWS();

            console.log('✅ WebSocket connected, starting audio capture...');

            // Start recording
            await startRecording();

            console.log('✅ Recording started successfully');

        } catch (error) {
            console.error('❌ Failed to start recording:', error);
            setRecordingState('error');
            disconnectWS();
        }
    };

    const handleStopRecording = () => {
        // Stop audio recording
        stopRecording();

        // Send end signal to WebSocket
        sendEndSignal();

        // Keep WebSocket open briefly to receive final transcript
        setTimeout(() => {
            disconnectWS();
        }, 1000);
    };

    const handleCancelRecording = () => {
        stopRecording();
        disconnectWS();
        setRecordingState('idle');
        setAccumulatedTranscript(''); // NEW: Clear accumulated
        onChange('');
    };

    const handleModeChange = (mode: InputMode) => {
        // Stop recording if switching away from voice mode
        if (inputMode === 'voice' && isRecording) {
            handleCancelRecording();
        }

        // Clear input when switching modes
        if (mode !== inputMode) {
            onChange('');
            setAccumulatedTranscript('');
        }

        // Show visualizer when switching TO voice mode
        if (mode === 'voice') {
            setShowVisualizer(true);
        }

        setInputMode(mode);
    };

    const handleRetry = () => {
        setRecordingState('idle');
        setHasTranscriptTimeout(false);
        setIsTranscriptEmpty(false);
        handleStartRecording();
    };

    return (
        <div className="voice-input-container">
            {/* Error display */}
            {error && (
                <ErrorMessage
                    error={error}
                    onRetry={handleRetry}
                    onGrantPermission={handleRetry}
                />
            )}

            {/* WebSocket connection status (for debugging) */}
            {inputMode === 'voice' && isRecording && (
                <div style={{ 
                    fontSize: '12px', 
                    color: isConnected ? '#28a745' : '#dc3545',
                    marginBottom: '8px',
                    textAlign: 'center'
                }}>
                    {isConnected ? '🟢 Connected to transcription service' : '🔴 Connecting...'}
                </div>
            )}

            {/* Voice mode: Show audio visualizer */}
            {inputMode === 'voice' && !error && showVisualizer && (
                <AudioVisualizer
                    recordingState={recordingState}
                    audioLevel={audioLevel}
                    recordingDuration={recordingDuration}
                    maxDuration={CONFIG.MAX_RECORDING_DURATION}
                    onStartRecording={handleStartRecording}
                    onStopRecording={handleStopRecording}
                    onCancelRecording={handleCancelRecording}
                />
            )}

            {/* Transcript display (only in voice mode) */}
            {/* Shows CURRENT segment being transcribed (real-time feedback) */}
            {inputMode === 'voice' && transcript && (
                <TranscriptDisplay
                    transcript={transcript}  // Just current segment
                    transcriptType={transcriptType}
                    hasTimeout={hasTranscriptTimeout}
                    isEmpty={isTranscriptEmpty}
                />
            )}

            {/* Input field (works in both modes) */}
            {/* Shows ALL accumulated final transcripts (editable) */}
            <InputField
                value={value}  // Full accumulated text from parent
                onChange={handleInputChange}
                onSubmit={handleSubmit}  // Use our wrapper that resets state
                inputMode={inputMode}
                onModeChange={handleModeChange}
                isProcessing={isProcessing}
                isRecording={isRecording}
                placeholder={
                    inputMode === 'keyboard'
                        ? 'Type your query or switch to voice input...'
                        : recordingState === 'idle' 
                            ? 'Click the microphone to start recording...'
                            : 'Recording in progress...'
                }
            />

            {/* Max duration warning */}
            {recordingDuration >= CONFIG.MAX_RECORDING_DURATION && isRecording && (
                <div className="max-duration-notice">
                    {UI_TEXT.MAX_DURATION_REACHED}
                </div>
            )}
        </div>
    );
};