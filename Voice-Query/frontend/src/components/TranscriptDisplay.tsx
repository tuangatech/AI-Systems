// src/components/TranscriptDisplay.tsx

import React from 'react';
import { TranscriptType } from '../types';
import { UI_TEXT } from '../utils/constants';
import './TranscriptDisplay.css';

interface TranscriptDisplayProps {
    transcript: string;
    transcriptType: TranscriptType | null;
    hasTimeout?: boolean;
    isEmpty?: boolean;
}

export const TranscriptDisplay: React.FC<TranscriptDisplayProps> = ({
    transcript,
    transcriptType,
    hasTimeout = false,
    isEmpty = false,
}) => {
    // Don't show anything if no transcript
    if (!transcript && !isEmpty) {
        return null;
    }

    // Show empty message if transcription produced no result
    if (isEmpty && !transcript) {
        return (
            <div className="transcript-display">
                <div className="transcript-empty">
                    <WarningIcon />
                    <span>{UI_TEXT.NO_TRANSCRIPTION}</span>
                </div>
            </div>
        );
    }

    return (
        <div className="transcript-display">
            <div className="transcript-label">
                {transcriptType === 'partial' ? 'Transcribing...' : 'Transcription'}
            </div>

            <div className={`transcript-text ${transcriptType || 'final'}`}>
                {transcript}
            </div>

            {transcriptType === 'partial' && (
                <div className="transcript-hint">
                    <InfoIcon />
                    <span>Partial result - still processing</span>
                </div>
            )}

            {hasTimeout && (
                <div className="transcript-warning">
                    <WarningIcon />
                    <span>Transcription timeout - showing last result</span>
                </div>
            )}
        </div>
    );
};

const InfoIcon: React.FC = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
);

const WarningIcon: React.FC = () => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" />
        <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
);