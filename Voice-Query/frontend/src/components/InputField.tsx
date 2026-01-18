// src/components/InputField.tsx
// PHASE 2: Updated with interruption handling

import React from 'react';
import { InputMode, ConversationState } from '../types';
import './InputField.css';

interface InputFieldProps {
    value: string;
    onChange: (value: string) => void;
    onSubmit: () => void;
    inputMode: InputMode;
    onModeChange: (mode: InputMode) => void;
    isProcessing: boolean;
    isRecording?: boolean;
    conversationState?: ConversationState;
    onInterrupt?: () => void;
    placeholder?: string;
}

export const InputField: React.FC<InputFieldProps> = ({
    value,
    onChange,
    onSubmit,
    inputMode,
    onModeChange,
    isProcessing,
    isRecording = false,
    conversationState = 'idle',
    onInterrupt,
    placeholder = 'Type your query or use voice input...',
}) => {
    const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        // Submit on Enter (without Shift)
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (value.trim() && !isProcessing) {
                onSubmit();
            }
        }
    };

    const handleModeToggle = () => {
        // If bot is speaking, interrupt it
        if (conversationState === 'bot_speaking' && onInterrupt) {
            onInterrupt();
            return;
        }

        // Otherwise, toggle voice mode normally
        const newMode: InputMode = inputMode === 'keyboard' ? 'voice' : 'keyboard';
        onModeChange(newMode);
    };

    const getMicButtonClass = () => {
        const baseClass = 'mode-toggle';

        if (conversationState === 'bot_speaking') {
            return `${baseClass} interrupt-mode`;
        }

        if (conversationState === 'bot_generating') {
            return `${baseClass} disabled`;
        }

        return `${baseClass} ${inputMode}`;
    };

    const getMicButtonTitle = () => {
        if (conversationState === 'bot_speaking') {
            return 'Click to interrupt and speak';
        }
        if (conversationState === 'bot_generating') {
            return 'Generating response...';
        }
        return inputMode === 'keyboard' ? 'Switch to voice input' : 'Switch to keyboard input';
    };

    const isMicButtonDisabled = conversationState === 'bot_generating';

    return (
        <div className="input-field-container">
            <div className="input-field-wrapper">
                <textarea
                    className="input-field"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder={placeholder}
                    disabled={isProcessing || isRecording}
                    rows={3}
                />

                <div className="input-controls">
                    <button
                        className={getMicButtonClass()}
                        onClick={handleModeToggle}
                        disabled={isMicButtonDisabled}
                        title={getMicButtonTitle()}
                    >
                        {conversationState === 'bot_speaking' ? (
                            <StopIcon />
                        ) : inputMode === 'keyboard' ? (
                            <MicrophoneIcon />
                        ) : (
                            <KeyboardIcon />
                        )}
                    </button>

                    <button
                        className="submit-button"
                        onClick={onSubmit}
                        disabled={!value.trim() || isProcessing}
                    >
                        {isProcessing ? 'Processing...' : 'Send'}
                    </button>
                </div>
            </div>

            {/* Only show mode indicator when in voice mode, no value, and not processing */}
            {inputMode === 'voice' && !value && !isProcessing && conversationState === 'idle' && (
                <div className="mode-indicator">
                    Voice input mode - Click microphone to start recording
                </div>
            )}

            {/* Show interrupt hint when bot is speaking */}
            {conversationState === 'bot_speaking' && (
                <div className="interrupt-hint">
                    💡 Click the red stop button to interrupt and speak
                </div>
            )}
        </div>
    );
};

// Simple SVG icons
const MicrophoneIcon: React.FC = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
        <line x1="12" y1="19" x2="12" y2="23" />
        <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
);

const KeyboardIcon: React.FC = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="2" y="4" width="20" height="16" rx="2" />
        <path d="M6 8h.01M10 8h.01M14 8h.01M18 8h.01M8 12h.01M12 12h.01M16 12h.01M7 16h10" />
    </svg>
);

const StopIcon: React.FC = () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
        <rect x="6" y="6" width="12" height="12" rx="2" />
    </svg>
);