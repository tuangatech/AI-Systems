# Voice Query Frontend - Phase 2

Frontend for the Voice-Enabled Query Interface POC.

## Phase 2 Status ✅

**Completed:**
- ✅ AudioWorklet for low-latency audio capture
- ✅ useVoiceRecording hook (microphone access + audio processing)
- ✅ useVAD hook (Voice Activity Detection with RMS threshold)
- ✅ AudioVisualizer component (pulsing mic animation)
- ✅ TranscriptDisplay component (partial/final text display)
- ✅ ErrorMessage component (permission denied, retry logic)
- ✅ VoiceInput orchestrator component
- ✅ Real-time audio level visualization
- ✅ Auto-stop after 2 seconds of silence
- ✅ 30-second max recording duration with timer
- ✅ Cancel recording functionality

**Not Yet Implemented:**
- ⏳ WebSocket connection to backend (Phase 3)
- ⏳ Real transcription from AWS Transcribe (Phase 3)
- ⏳ Partial transcript streaming (Phase 3)

## Getting Started

### Prerequisites

- Node.js 16+ and npm

### Installation

```bash
cd frontend
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env.local

# Start development server
npm start
```

The app will open at [http://localhost:3000](http://localhost:3000)

## Testing Phase 2

### Voice Recording Tests

1. **Test 1: Start/Stop Recording**
   - Switch to voice mode (click microphone icon in input field)
   - Click the large microphone button
   - Grant microphone permission if prompted
   - Speak for a few seconds
   - Click "Stop" button
   - Expected: See mock transcript appear, audio level bar animates

2. **Test 2: Auto-Stop on Silence**
   - Start recording
   - Speak briefly, then stay silent for 2 seconds
   - Expected: Recording automatically stops after silence detected

3. **Test 3: Cancel Recording**
   - Start recording
   - Click "Cancel" button mid-recording
   - Expected: Recording stops immediately, no transcript shown

4. **Test 4: Maximum Duration**
   - Start recording
   - Let it run for 30 seconds (or speak continuously)
   - Expected: Recording auto-stops at 30 seconds with notice message

5. **Test 5: Audio Level Visualization**
   - Start recording
   - Speak at different volumes (whisper, normal, loud)
   - Expected: Microphone pulses and audio level bar reacts to volume

6. **Test 6: Mode Switching**
   - Start recording in voice mode
   - Switch to keyboard mode
   - Expected: Recording stops, transcript cleared

7. **Test 7: Permission Denied**
   - Deny microphone permission (in browser settings)
   - Try to start recording
   - Expected: Error message with instructions appears

### What Works in Phase 2

✅ Microphone access and permission handling
✅ Real-time audio capture at 16kHz PCM format
✅ Voice Activity Detection (silence = auto-stop after 2s)
✅ Pulsing microphone animation based on audio level
✅ Recording timer (shows elapsed time / max time)
✅ Manual stop and cancel buttons
✅ 30-second max duration enforcement
✅ Error handling with retry buttons
✅ Mock transcript for demo (Phase 3 will add real transcription)

## Project Structure

```
src/
├── components/
│   ├── VoiceInput.tsx          # Main voice input orchestrator
│   ├── VoiceInput.css
│   ├── AudioVisualizer.tsx     # Pulsing mic + recording controls
│   ├── AudioVisualizer.css
│   ├── TranscriptDisplay.tsx   # Partial/final transcript display
│   ├── TranscriptDisplay.css
│   ├── ErrorMessage.tsx        # Error handling UI
│   ├── ErrorMessage.css
│   ├── InputField.tsx          # Text input field
│   ├── InputField.css
│   ├── QueryResponse.tsx       # Response display
│   └── QueryResponse.css
├── hooks/
│   ├── useVoiceRecording.ts    # Microphone + AudioWorklet manager
│   └── useVAD.ts               # Voice Activity Detection
├── worklets/
│   └── audio-processor.worklet.js  # Low-latency audio processing
├── utils/
│   ├── constants.ts            # Configuration values
│   └── mockResponses.ts        # Mock response generator
├── types.ts                    # TypeScript type definitions
├── App.tsx                     # Main application
├── App.css
└── index.tsx                   # Entry point

public/
└── audio-processor.worklet.js  # (Copy of worklet for runtime loading)
```

## Available Scripts

### `npm start`
Runs the app in development mode at [http://localhost:3000](http://localhost:3000)

### `npm run build`
Builds the app for production to the `build` folder

### `npm test`
Launches the test runner

## Next Steps (Phase 3)

1. Implement `useWebSocket` hook for backend connection
2. Connect audio chunks to WebSocket (binary frames)
3. Receive and display partial transcripts in real-time
4. Receive and display final transcripts
5. Handle WebSocket errors and reconnection
6. Remove mock transcript logic
7. Implement transcription timeout (5s after recording stops)

## Phase 2 Completion Checklist

- [x] AudioWorklet processor for PCM conversion
- [x] useVoiceRecording hook with microphone access
- [x] useVAD hook for silence detection
- [x] AudioVisualizer with pulsing animation
- [x] TranscriptDisplay for partial/final text
- [x] ErrorMessage with retry logic
- [x] VoiceInput orchestrator
- [x] Real-time audio level visualization
- [x] 30-second max duration with timer
- [x] Cancel functionality
- [x] Mode switching (keyboard ↔ voice)
- [x] Permission error handling

**Phase 2 is complete!** ✅ Ready to proceed to Phase 3 (WebSocket + Backend Integration).