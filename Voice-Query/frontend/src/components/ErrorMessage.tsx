// src/components/ErrorMessage.tsx

import React from 'react';
import { ErrorType } from '../types';
import { ERROR_MESSAGES } from '../utils/constants';
import './ErrorMessage.css';

interface ErrorMessageProps {
    error: ErrorType;
    onRetry?: () => void;
    onGrantPermission?: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
    error,
    onRetry,
    onGrantPermission,
}) => {
    if (!error) return null;

    const getErrorMessage = (): string => {
        switch (error) {
            case 'mic_permission_denied':
                return ERROR_MESSAGES.MIC_PERMISSION_DENIED;
            case 'websocket_disconnect':
                return ERROR_MESSAGES.WEBSOCKET_DISCONNECT;
            case 'transcription_timeout':
                return ERROR_MESSAGES.TRANSCRIPTION_TIMEOUT;
            case 'transcription_failed':
                return ERROR_MESSAGES.TRANSCRIPTION_FAILED;
            default:
                return 'An unexpected error occurred.';
        }
    };

    const showGrantPermissionButton = error === 'mic_permission_denied';
    const showRetryButton = error !== 'mic_permission_denied' && onRetry;

    return (
        <div className="error-message">
            <div className="error-content">
                <ErrorIcon />
                <div className="error-text">
                    <div className="error-title">Error</div>
                    <div className="error-description">{getErrorMessage()}</div>
                </div>
            </div>

            <div className="error-actions">
                {showGrantPermissionButton && onGrantPermission && (
                    <button className="error-button primary" onClick={onGrantPermission}>
                        Grant Permission
                    </button>
                )}

                {showRetryButton && (
                    <button className="error-button secondary" onClick={onRetry}>
                        Try Again
                    </button>
                )}
            </div>

            {error === 'mic_permission_denied' && (
                <div className="error-instructions">
                    <strong>How to grant permission:</strong>
                    <ol>
                        <li>Click the camera/microphone icon in your browser's address bar</li>
                        <li>Select "Always allow" for microphone access</li>
                        <li>Click "Grant Permission" above to retry</li>
                    </ol>
                </div>
            )}
        </div>
    );
};

const ErrorIcon: React.FC = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
);