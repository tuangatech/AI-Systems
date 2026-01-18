// src/components/VoiceInput.tsx
// PHASE 2: Updated with conversation state machine and TTS integration

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { InputMode, RecordingState, TranscriptType, ConversationState, BotResponse } from '../types';
import { InputField } from './InputField';
import { AudioVisualizer } from './AudioVisualizer';
import { TranscriptDisplay } from './TranscriptDisplay';
import { ResponseDisplay } from './ResponseDisplay';
import { AudioPlayer } from './AudioPlayer';
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
    const [conversationState, setConversationState] = useState<ConversationState>('idle');
    const [hasTranscriptTimeout, setHasTranscriptTimeout] = useState(false);
    const [isTranscriptEmpty, setIsTranscriptEmpty] = useState(false);
    const [accumulatedTranscript, setAccumulatedTranscript] = useState<string>('');
    const [showVisualizer, setShowVisualizer] = useState<boolean>(true);
    const [botResponse, setBotResponse] = useState<BotResponse | null>(null);
    const [isAudioPlaying, setIsAudioPlaying] = useState(false);

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

    // Send query to backend
    const sendQueryToBackend = useCallback(async (queryText: string) => {
        if (!queryText.trim()) {
            console.warn('Cannot send empty query');
            return;
        }

        console.log('📤 Sending query to backend:', queryText);
        setConversationState('bot_generating');

        try {
            const response = await fetch('http://localhost:8080/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: queryText }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data: BotResponse = await response.json();

            console.log('✅ Received bot response:', {
                hasAudio: !!data.audio,
                duration: data.duration,
                textLength: data.text.length
            });

            setBotResponse(data);

            // Transition to bot_speaking if audio is available
            if (data.audio) {
                setConversationState('bot_speaking');
            } else {
                // No audio, just show text and go back to idle
                setConversationState('idle');
            }

        } catch (error) {
            console.error('❌ Failed to send query:', error);
            setConversationState('error');
            setBotResponse({
                success: false,
                text: '',
                audio: null,
                duration: null,
                error: error instanceof Error ? error.message : 'Failed to send query'
            });
        }
    }, []);

    // Handle query submission
    const handleSubmit = useCallback(() => {
        if (!value.trim()) {
            console.warn('Cannot submit empty query');
            return;
        }

        console.log('📨 Submitting query:', value);

        // Send to backend
        sendQueryToBackend(value);

        // Don't call parent's onSubmit anymore since we're handling it
        // onSubmit();
    }, [value, sendQueryToBackend]);

    // Handle audio playback completion
    const handleAudioPlaybackEnd = useCallback(() => {
        console.log('🔇 Audio playback ended');
        setIsAudioPlaying(false);
        setConversationState('idle');
        
        // Clear the response after audio finishes
        setTimeout(() => {
            setBotResponse(null);
        }, 500);
    }, []);

    // Handle audio playback start
    const handleAudioPlaybackStart = useCallback(() => {
        console.log('🔊 Audio playback started');
        setIsAudioPlaying(true);
    }, []);

    // Handle interruption (user clicks mic while bot is speaking)
    const handleInterrupt = useCallback(() => {
        console.log('🛑 User interrupted bot');

        // Stop audio playback
        setIsAudioPlaying(false);

        // Clear bot response
        setBotResponse(null);

        // Clear input
        onChange('');
        setAccumulatedTranscript('');

        // Start new recording immediately
        setConversationState('user_recording');
        setInputMode('voice');
        
        // Start recording inline to avoid dependency issues
        (async () => {
            try {
                setHasTranscriptTimeout(false);
                setIsTranscriptEmpty(false);
                setAccumulatedTranscript('');
                setShowVisualizer(true);

                console.log('🎤 Starting recording process...');
                console.log('📡 Connecting WebSocket...');
                await connectWS();

                console.log('✅ WebSocket connected, starting audio capture...');
                await startRecording();

                console.log('✅ Recording started successfully');
                setConversationState('user_recording');
            } catch (error) {
                console.error('❌ Failed to start recording:', error);
                setRecordingState('error');
                setConversationState('error');
                disconnectWS();
            }
        })();
    }, [onChange, connectWS, startRecording, disconnectWS]);

    // Auto-stop when VAD detects silence
    useEffect(() => {
        if (shouldAutoStop && isRecording) {
            console.log('🛑 Auto-stopping due to silence');
            stopRecording();
            sendEndSignal();

            setTimeout(() => {
                disconnectWS();
            }, 1000);
        }
    }, [shouldAutoStop, isRecording, stopRecording, sendEndSignal, disconnectWS]);

    // Update input value when transcript changes
    useEffect(() => {
        const isNewFinal =
            transcriptType === 'final' &&
            transcript &&
            (transcript !== prevTranscriptRef.current.text || transcriptType !== prevTranscriptRef.current.type);

        if (isNewFinal) {
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

            prevTranscriptRef.current = { text: transcript, type: transcriptType };
        }
        else if (transcriptType === 'partial' && transcript) {
            prevTranscriptRef.current = { text: transcript, type: transcriptType };
        }
    }, [transcript, transcriptType, accumulatedTranscript, onChange]);

    // Update recording state based on isRecording
    useEffect(() => {
        if (isRecording) {
            setRecordingState('recording');
            setConversationState('user_recording');
        } else if (recordingState === 'recording') {
            setRecordingState('processing');

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

    // Set state back to idle when final transcript arrives
    useEffect(() => {
        if (transcriptType === 'final' && recordingState === 'processing') {
            console.log('✅ Final transcript received, setting state to idle');
            setRecordingState('idle');
            setConversationState('idle');
        }
    }, [transcriptType, recordingState]);

    // Auto-switch to keyboard mode when user starts typing in voice mode
    const handleInputChange = (newValue: string) => {
        onChange(newValue);

        if (inputMode === 'voice' && newValue.length > 0 && !isRecording) {
            setInputMode('keyboard');
        }
    };

    const handleStartRecording = async () => {
        try {
            setHasTranscriptTimeout(false);
            setIsTranscriptEmpty(false);
            setAccumulatedTranscript('');
            setShowVisualizer(true);

            console.log('🎤 Starting recording process...');

            console.log('📡 Connecting WebSocket...');
            await connectWS();

            console.log('✅ WebSocket connected, starting audio capture...');
            await startRecording();

            console.log('✅ Recording started successfully');
            setConversationState('user_recording');

        } catch (error) {
            console.error('❌ Failed to start recording:', error);
            setRecordingState('error');
            setConversationState('error');
            disconnectWS();
        }
    };

    const handleStopRecording = () => {
        stopRecording();
        sendEndSignal();

        setTimeout(() => {
            disconnectWS();
        }, 1000);
    };

    const handleCancelRecording = () => {
        stopRecording();
        disconnectWS();
        setRecordingState('idle');
        setConversationState('idle');
        setAccumulatedTranscript('');
        onChange('');
    };

    const handleModeChange = (mode: InputMode) => {
        if (inputMode === 'voice' && isRecording) {
            handleCancelRecording();
        }

        if (mode !== inputMode) {
            onChange('');
            setAccumulatedTranscript('');
        }

        if (mode === 'voice') {
            setShowVisualizer(true);
        }

        setInputMode(mode);
    };

    const handleRetry = () => {
        setRecordingState('idle');
        setConversationState('idle');
        setHasTranscriptTimeout(false);
        setIsTranscriptEmpty(false);
        handleStartRecording();
    };

    // Determine if input should be disabled
    const isInputDisabled = conversationState === 'bot_speaking' || 
                           conversationState === 'bot_generating';

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

            {/* WebSocket connection status */}
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

            {/* Bot response display */}
            {botResponse && botResponse.success && (
                <>
                    <ResponseDisplay 
                        response={botResponse}
                        isPlaying={isAudioPlaying}
                    />
                    
                    {/* Audio player */}
                    {botResponse.audio && (
                        <AudioPlayer
                            audioData={botResponse.audio}
                            autoPlay={true}
                            playbackRate={1.25}
                            onPlaybackStart={handleAudioPlaybackStart}
                            onPlaybackEnd={handleAudioPlaybackEnd}
                            onPlaybackError={(error) => {
                                console.error('Audio playback error:', error);
                                setIsAudioPlaying(false);
                            }}
                        />
                    )}
                </>
            )}

            {/* Voice mode: Show audio visualizer */}
            {inputMode === 'voice' && !error && showVisualizer && 
             conversationState !== 'bot_speaking' && conversationState !== 'bot_generating' && (
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

            {/* Transcript display (only in voice mode, not during bot speaking) */}
            {inputMode === 'voice' && transcript && 
             conversationState !== 'bot_speaking' && conversationState !== 'bot_generating' && (
                <TranscriptDisplay
                    transcript={transcript}
                    transcriptType={transcriptType}
                    hasTimeout={hasTranscriptTimeout}
                    isEmpty={isTranscriptEmpty}
                />
            )}

            {/* Loading indicator during bot generation */}
            {conversationState === 'bot_generating' && (
                <div className="generating-indicator">
                    <div className="spinner"></div>
                    <span>Processing your query...</span>
                </div>
            )}

            {/* Input field */}
            <InputField
                value={value}
                onChange={handleInputChange}
                onSubmit={handleSubmit}
                inputMode={inputMode}
                onModeChange={handleModeChange}
                isProcessing={isInputDisabled}
                isRecording={isRecording}
                conversationState={conversationState}
                onInterrupt={handleInterrupt}
                placeholder={
                    isInputDisabled
                        ? 'Listening to AI Assistant...'
                        : inputMode === 'keyboard'
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