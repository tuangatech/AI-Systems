// src/components/AudioVisualizer.tsx

import React from 'react';
import { RecordingState } from '../types';
import { UI_TEXT } from '../utils/constants';
import './AudioVisualizer.css';

interface AudioVisualizerProps {
    recordingState: RecordingState;
    audioLevel: number;
    recordingDuration: number;
    maxDuration: number;
    onStartRecording: () => void;
    onStopRecording: () => void;
    onCancelRecording: () => void;
}

export const AudioVisualizer: React.FC<AudioVisualizerProps> = ({
    recordingState,
    audioLevel,
    recordingDuration,
    maxDuration,
    onStartRecording,
    onStopRecording,
    onCancelRecording,
}) => {
    const formatTime = (ms: number): string => {
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    };

    const formatMaxTime = (ms: number): string => {
        const seconds = Math.floor(ms / 1000);
        return `0:${seconds.toString().padStart(2, '0')}`;
    };

    // Scale factor based on audio level (for pulsing animation)
    // Map audioLevel (0.0 - 1.0) to scale (1.0 - 1.5)
    const pulseScale = recordingState === 'recording'
        ? 1.0 + (audioLevel * 0.5)
        : 1.0;

    return (
        <div className="audio-visualizer">
            {recordingState === 'idle' && (
                <button
                    className="mic-button idle"
                    onClick={onStartRecording}
                    title="Start recording"
                >
                    <MicrophoneIcon />
                </button>
            )}

            {recordingState === 'recording' && (
                <div className="recording-controls">
                    <div
                        className="mic-button recording"
                        style={{ transform: `scale(${pulseScale})` }}
                    >
                        <MicrophoneIcon />
                    </div>

                    <div className="recording-info">
                        <div className="recording-status">
                            <span className="recording-dot" />
                            <span className="recording-text">{UI_TEXT.LISTENING}</span>
                        </div>

                        <div className="recording-timer">
                            {formatTime(recordingDuration)} / {formatMaxTime(maxDuration)}
                        </div>

                        <div className="audio-level-bar">
                            <div
                                className="audio-level-fill"
                                style={{ width: `${audioLevel * 100}%` }}
                            />
                        </div>
                    </div>

                    <div className="recording-actions">
                        <button
                            className="action-button cancel"
                            onClick={onCancelRecording}
                            title="Cancel recording"
                        >
                            Cancel
                        </button>
                        <button
                            className="action-button stop"
                            onClick={onStopRecording}
                            title="Stop recording"
                        >
                            Stop
                        </button>
                    </div>
                </div>
            )}

            {recordingState === 'processing' && (
                <div className="processing-state">
                    <div className="spinner-icon">
                        <SpinnerIcon />
                    </div>
                    <span className="processing-text">{UI_TEXT.PROCESSING}</span>
                </div>
            )}
        </div>
    );
};

const MicrophoneIcon: React.FC = () => (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
);

const SpinnerIcon: React.FC = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" opacity="0.25" />
        <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
    </svg>
);