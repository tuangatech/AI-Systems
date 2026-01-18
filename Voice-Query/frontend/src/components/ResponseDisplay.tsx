// src/components/ResponseDisplay.tsx

import React from 'react';
import { BotResponse } from '../types';
import './ResponseDisplay.css';

interface ResponseDisplayProps {
    response: BotResponse;
    isPlaying: boolean;
}

export const ResponseDisplay: React.FC<ResponseDisplayProps> = ({
    response,
    isPlaying,
}) => {
    if (!response || !response.success) {
        return null;
    }

    return (
        <div className="response-display">
            <div className="response-header">
                <div className="bot-avatar">
                    <span className="avatar-icon">🤖</span>
                </div>
                <div className="bot-name">AI Assistant</div>
                {isPlaying && <div className="speaking-indicator">Speaking...</div>}
            </div>

            <div className="response-content">
                <div className="response-text">
                    {response.text}
                </div>

                {/* Show metadata */}
                {response.metadata && (
                    <div className="response-metadata">
                        {response.duration && (
                            <span className="metadata-item">
                                ⏱️ {response.duration}s audio
                            </span>
                        )}
                        {response.metadata.processingTime && (
                            <span className="metadata-item">
                                ⚡ {response.metadata.processingTime}ms response
                            </span>
                        )}
                    </div>
                )}

                {/* Show warning if no audio */}
                {!response.audio && (
                    <div className="no-audio-warning">
                        ⚠️ Text-only response (audio synthesis unavailable)
                    </div>
                )}

                {/* Show synthesis error if present */}
                {response.metadata?.synthesisError && (
                    <div className="synthesis-error">
                        ⚠️ Audio synthesis error: {response.metadata.synthesisError}
                    </div>
                )}
            </div>
        </div>
    );
};
