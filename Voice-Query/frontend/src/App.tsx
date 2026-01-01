// src/App.tsx

import React, { useState, useCallback } from 'react';
import { VoiceInput } from './components/VoiceInput';
import { QueryResponse } from './components/QueryResponse';
import { ProcessingState, QueryResult } from './types';
import { generateMockResponse, simulateProcessing } from './utils/mockResponses';
import './App.css';

function App() {
  const [inputValue, setInputValue] = useState<string>('');
  const [processingState, setProcessingState] = useState<ProcessingState>('idle');
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);

  const handleSubmit = useCallback(async () => {
    if (!inputValue.trim() || processingState !== 'idle') {
      return;
    }

    const query = inputValue.trim();

    // Start processing
    setProcessingState('processing');

    try {
      // Simulate processing with staged indicators
      await simulateProcessing(
        () => setProcessingState('processing'),
        () => setProcessingState('generating')
      );

      // Generate mock response
      const response = generateMockResponse(query);

      // Set result
      const result: QueryResult = {
        query,
        response,
        timestamp: new Date(),
      };

      setQueryResult(result);
      setProcessingState('complete');

      // Clear input for next query
      setInputValue('');

    } catch (error) {
      console.error('Error processing query:', error);
      setProcessingState('idle');
    }
  }, [inputValue, processingState]);

  const handleNewQuery = useCallback(() => {
    setProcessingState('idle');
    setQueryResult(null);
  }, []);

  // Wrap setInputValue in useCallback to prevent unnecessary re-renders
  const handleInputChange = useCallback((value: string) => {
    setInputValue(value);
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Voice-Enabled Query Interface</h1>
        <p className="subtitle">Proof of Concept - Real-time Speech-to-Text Demo</p>
      </header>

      <main className="app-main">
        <div className="input-section">
          <VoiceInput
            value={inputValue}
            onChange={handleInputChange}
            onSubmit={handleSubmit}
            isProcessing={processingState !== 'idle'}
          />
        </div>

        <div className="response-section">
          <QueryResponse
            processingState={processingState}
            result={queryResult}
          />
        </div>

        {/* New Query button appears after response is complete */}
        {processingState === 'complete' && (
          <div className="action-section">
            <button className="new-query-button" onClick={handleNewQuery}>
              Ask Another Question
            </button>
          </div>
        )}
      </main>

      <footer className="app-footer">
        <div className="poc-badge">POC Demo</div>
        <p>Phase 2: Voice capture with real-time audio processing</p>
        <p className="phase-note">
          WebSocket transcription will be enabled in Phase 3
        </p>
      </footer>
    </div>
  );
}

export default App;