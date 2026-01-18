// src/App.tsx
// PHASE 2: Simplified - Mock responses removed (handled by backend)

import React, { useState, useCallback } from 'react';
import { VoiceInput } from './components/VoiceInput';
import './App.css';

function App() {
  const [inputValue, setInputValue] = useState<string>('');

  // Wrap setInputValue in useCallback to prevent unnecessary re-renders
  const handleInputChange = useCallback((value: string) => {
    setInputValue(value);
  }, []);

  // This is no longer used - VoiceInput handles submission internally
  // Kept for compatibility, but VoiceInput.tsx calls backend directly
  const handleSubmit = useCallback(() => {
    console.log('App.handleSubmit called (legacy, not used)');
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1>Talk2AI</h1>
        <p className="subtitle">Real-time Voice-Enabled RAG</p>
      </header>

      <main className="app-main">
        <div className="input-section">
          <VoiceInput
            value={inputValue}
            onChange={handleInputChange}
            onSubmit={handleSubmit}
            isProcessing={false}
          />
        </div>
      </main>

      <footer className="app-footer">
        <div className="poc-badge">Talk2AI Conversation</div>
        <div className="tech-stack">
          <span>🎤 AWS Transcribe</span>
          <span>🔊 AWS Polly (Matthew)</span>
          <span>⚡ React + WebSocket</span>
        </div>
      </footer>
    </div>
  );
}

export default App;