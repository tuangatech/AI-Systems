// src/components/QueryResponse.tsx

import React from 'react';
import { ProcessingState, QueryResult } from '../types';
import { UI_TEXT } from '../utils/constants';
import './QueryResponse.css';

interface QueryResponseProps {
    processingState: ProcessingState;
    result: QueryResult | null;
}

export const QueryResponse: React.FC<QueryResponseProps> = ({
    processingState,
    result,
}) => {
    if (processingState === 'idle' && !result) {
        return null;
    }

    return (
        <div className="query-response-container">
            {/* Processing indicator */}
            {processingState !== 'idle' && processingState !== 'complete' && (
                <div className="processing-indicator">
                    <LoadingSpinner />
                    <span className="processing-text">
                        {processingState === 'processing' && UI_TEXT.PROCESSING_QUERY}
                        {processingState === 'generating' && UI_TEXT.GENERATING_ANSWER}
                    </span>
                </div>
            )}

            {/* Query and Response Display */}
            {result && processingState === 'complete' && (
                <div className="response-content">
                    <div className="query-section">
                        <div className="section-label">Your Query:</div>
                        <div className="query-text">{result.query}</div>
                        <div className="timestamp">
                            {result.timestamp.toLocaleTimeString()}
                        </div>
                    </div>

                    <div className="response-section">
                        <div className="section-label">Response:</div>
                        <div className="response-text">{result.response}</div>
                    </div>

                    <div className="poc-notice">
                        <InfoIcon />
                        <span>
                            This is a mock response for POC demonstration. In production,
                            this would show results from the RAG system.
                        </span>
                    </div>
                </div>
            )}
        </div>
    );
};

const LoadingSpinner: React.FC = () => (
    <svg
        className="spinner"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
    >
        <circle cx="12" cy="12" r="10" opacity="0.25" />
        <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
    </svg>
);

const InfoIcon: React.FC = () => (
    <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
    >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="16" x2="12" y2="12" />
        <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
);