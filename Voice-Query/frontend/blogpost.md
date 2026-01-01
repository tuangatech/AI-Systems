


## Voice Capturing

### High-Level Flow
```
User clicks Mic Button
    ↓
Request Microphone Permission
    ↓
Start Audio Capture (MediaStream)
    ↓
Process Audio in AudioWorklet (separate thread)
    ↓
Convert to PCM 16-bit, 16kHz, mono
    ↓
Send chunks to Main Thread
    ↓
Apply Voice Activity Detection (VAD)
    ↓
Stream to Backend via WebSocket
    ↓
Receive Transcripts
    ↓
Display in UI
```

### Components

1. VoiceInput Component (Orchestrator)
Role: Main coordinator that brings everything together

Responsibilities:
- Manages recording state (idle → recording → processing → complete)
- Coordinates between all hooks and child components
- Handles user interactions (start/stop/cancel)
- Displays appropriate UI based on state

Uses:
- `useVoiceRecording` hook for microphone + audio processing
- `useWebSocket` hook for backend connection
- `useVAD` hook for silence detection
- `AudioVisualizer` component for pulsing animation
- `TranscriptDisplay` component for showing partial/final text

2. useVoiceRecording Hook
Role: Manages microphone access and audio processing

Responsibilities:
- Request microphone permission
- Initialize `MediaStream` from `getUserMedia`
- Create and connect AudioContext
- Load and configure AudioWorklet
- Handle audio stream lifecycle (start/stop/cleanup)
- Provide audio chunks to parent component

Interacts with:
- Browser's `navigator.mediaDevices.getUserMedia`
- `AudioWorkletNode` (audio-processor.worklet.js)
- VoiceInput component (parent)

3. AudioWorklet (audio-processor.worklet.js)
Role: Low-latency audio processing in separate thread

Why AudioWorklet?
- Runs on separate thread (doesn't block UI)
- Real-time audio processing (128 samples at a time)
- Lower latency than ScriptProcessorNode

Responsibilities:
- Receive raw audio samples from microphone
- Downsample from 48kHz (typical mic) to 16kHz (required by AWS Transcribe)
- Convert to PCM 16-bit mono format
- Calculate RMS (Root Mean Square) for volume level
- Send processed chunks via MessagePort to main thread

Data Flow:
```
Microphone (48kHz stereo)
    ↓
AudioWorklet receives 128 samples
    ↓
Downsample to 16kHz
    ↓
Convert stereo → mono (if needed)
    ↓
Convert Float32 → Int16 (PCM)
    ↓
Calculate RMS for volume
    ↓
postMessage({audioData: Int16Array, rms: number})
    ↓
Main thread receives chunk
```

4. useVAD Hook (Voice Activity Detection)
Role: Detect when user stops speaking (at client side, Faster feedback: No network round-trip)

Responsibilities:
- Monitor RMS values from AudioWorklet
- Track silence duration
- Trigger auto-stop after 2 seconds of silence
- Prevent immediate stop (minimum 0.5s recording)

5. AudioVisualizer Component
Role: Visual feedback during recording

Responsibilities:
- Show pulsing microphone icon
- Animate based on audio level (RMS)
- Display recording timer
- Show "Listening..." text

Visual States:
- Idle: Static mic icon
- Recording: Pulsing animation (scales with audio level)
- Processing: Spinner animation

---

6. TranscriptDisplay Component
Role: Show partial and final transcripts

Responsibilities:
- Display partial transcripts in lighter gray italic
- Replace with final transcript in solid black
- Handle empty transcripts ("I didn't catch that")
- Show timeout warnings

7. useWebSocket Hook
Role: Communicate with backend STT service

Responsibilities:
- Open WebSocket connection to ECS
- Send binary audio chunks
- Send end-of-stream signal `{type: "end_stream"}`
- Receive partial/final transcripts
- Handle connection errors
- Clean up on unmount

### Complete Integration Flow

**When User Clicks Mic Button:**
```
1. VoiceInput calls startRecording()
   ↓
2. useVoiceRecording requests mic permission
   ↓
3. getUserMedia returns MediaStream
   ↓
4. AudioContext created (16kHz sample rate)
   ↓
5. AudioWorklet loaded and connected
   ↓
6. useWebSocket opens connection (Phase 3)
   ↓
7. AudioVisualizer starts pulsing
   ↓
8. AudioWorklet processes audio every ~3ms
   ↓
9. Chunks sent to useVoiceRecording via postMessage
   ↓
10. useVoiceRecording forwards to useWebSocket (Phase 3)
   ↓
11. useVAD monitors RMS values
   ↓
12. If silence detected for 2s → auto-stop
```

**When Recording Stops (Auto or Manual):**
```
1. VoiceInput calls stopRecording()
   ↓
2. useVoiceRecording stops MediaStream
   ↓
3. AudioWorklet disconnected
   ↓
4. useWebSocket sends {"type": "end_stream"}
   ↓
5. useWebSocket waits for final transcript (5s timeout)
   ↓
6. TranscriptDisplay shows final text
   ↓
7. AudioVisualizer stops pulsing
   ↓
8. User can edit transcript before submitting
```

VoiceInput Component State:
```typescript
{
  recordingState: 'idle' | 'recording' | 'processing' | 'error',
  transcript: string,
  transcriptType: 'partial' | 'final',
  audioLevel: number,
  recordingDuration: number,
  error: ErrorType | null
}
```

VoiceInput UI Components
- AudioVisualizer
  - Pulsing mic button
  - Recording timer
  - "Listening..." text
- TranscriptDisplay
  - Partial transcript (gray italic)
  - Final transcript (black normal)
- InputField 
  - Editable text area
  - Submit button

### Why Hooks?
- Separation of concerns: Each hook has single responsibility
- Reusability: Can be used in other components if needed
- Testability: Easier to test logic separately from UI
- State isolation: Each hook manages its own state

Audio Chunk Format
```typescript
{
  audioData: Int16Array,  // PCM 16-bit samples
  rms: number,            // Volume level (0.0 - 1.0)
  timestamp: number       // When captured
}
```


## Backend STT Service

### High-Level Flow
```
Client Audio Stream
       ↓
WebSocket Connection (via ALB)
       ↓
ECS Fargate Container (server.js)
       ↓
WebSocket Handler (websocket-handler.js)
       ↓
Transcribe Service (transcribe-service.js)
       ↓
AWS Transcribe Streaming API
       ↓
Partial/Final Transcripts
       ↓
Back to Client via WebSocket
```

Key Principle: Each WebSocket connection = One recording session = One AWS Transcribe stream. Lifecycle is: connect → stream audio → send end signal → receive final transcript → close.

### Component Relationships

```
┌─────────────────────────────────────────────────────┐
│                    server.js                        │
│  • HTTP server + WebSocket upgrade handling         │
│  • Health check endpoint (/health)                  │
│  • Initializes WebSocket server (ws library)        │
│  • Delegates connections to websocket-handler       │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│              websocket-handler.js                   │
│  • Manages individual WebSocket connection          │
│  • Routes binary frames → transcribe-service        │
│  • Routes text messages (end_stream signal)         │
│  • Sends transcripts back to client                 │
│  • Handles connection cleanup on close/error        │
└────────────────────┬────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────┐
│             transcribe-service.js                   │
│  • Creates AWS Transcribe streaming session         │
│  • Manages audio buffering (PCM chunks)             │
│  • Handles partial/final transcript events          │
│  • Properly closes Transcribe stream                │
│  • Returns transcripts via callback                 │
└─────────────────────────────────────────────────────┘
```

### Data Flow
1. Connection Establishment
```
Client clicks mic
  ↓
Client opens WebSocket to ALB endpoint
  ↓
ALB routes to ECS Fargate task
  ↓
server.js upgrades HTTP → WebSocket
  ↓
websocket-handler.js creates session
  ↓
transcribe-service.js starts AWS Transcribe stream
  ↓
Ready to receive audio
```

2. Audio Streaming (Loop)
```
Client captures audio chunk (100ms PCM)
  ↓
Sends binary WebSocket frame
  ↓
websocket-handler receives binary message
  ↓
Forwards to transcribe-service
  ↓
transcribe-service buffers and sends to AWS Transcribe
  ↓
AWS Transcribe processes audio
  ↓
Partial transcript event fires
  ↓
transcribe-service emits partial transcript
  ↓
websocket-handler sends to client:
  {"type": "partial", "text": "hello world"}
```

3. Stream Finalization
```
Client detects silence (VAD) or user clicks stop
  ↓
Client sends final audio chunk (binary)
  ↓
Client sends end signal (text): {"type": "end_stream"}
  ↓
websocket-handler receives end signal
  ↓
transcribe-service closes Transcribe stream
  ↓
AWS Transcribe sends final transcript event
  ↓
transcribe-service emits final transcript
  ↓
websocket-handler sends to client:
  {"type": "final", "text": "hello world"}
  ↓
Client receives final transcript
  ↓
Client closes WebSocket connection
  ↓
Server cleanup: release resources, log session end
```

### Key Technical Decisions
1. WebSocket Library: `ws`
Why:
- Mature, widely-used Node.js WebSocket library
- Handles binary and text frames natively
- Simple API for server-side WebSocket management
- Works seamlessly with AWS ALB WebSocket support

2. AWS SDK: `@aws-sdk/client-transcribe-streaming`
Why:
- Official AWS SDK v3 for Transcribe Streaming
- Supports streaming protocol with event-driven architecture
- Uses IAM role credentials (no hardcoded keys)
- Handles backpressure and retries internally

Configuration
```javascript
{
  region: process.env.AWS_REGION || 'us-east-1',
  languageCode: 'en-US',
  mediaSampleRateHertz: 16000,
  mediaEncoding: 'pcm',
  enablePartialResultsStabilization: true,
  partialResultsStability: 'medium'
}
```

### Docker Strategy

**Base Image:** `node:18-alpine`
- Alpine Linux for minimal size (~50MB vs ~900MB for full Node)
- Node 18 LTS for stability
- Includes npm for dependency installation

**Key Dockerfile decisions:**
1. Run as non-root user for security
2. Use `.dockerignore` to exclude dev files
3. `npm ci` instead of `npm install` (faster, deterministic)
4. Health check command for ECS

### **Deployment Architecture**
```
┌─────────────────────────────────────────────────┐
│  Application Load Balancer (WebSocket-enabled)  │
│  • Target: ECS Fargate service                  │
│  • Health check: /health endpoint               │
│  • Sticky sessions: Not needed (stateless)      │
└────────────────────┬────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────┐
│        ECS Fargate Service (1 task)             │
│  • Task Definition:                             │
│    - 0.5 vCPU, 1 GB memory                      │
│    - Task role: TranscribeAccess                │
│    - Container port: 8080                       │
│    - Health check: /health                      │
│  • Desired count: 1 (single user POC)           │
│  • Auto-restart on failure                      │
└─────────────────────────────────────────────────┘
```


### `src/transcribe-service.js` Flow:
1. new TranscribeSession() → Create session instance
2. start() → Begin Transcribe streaming (async generator runs in background)
3. sendAudio(chunk) → Push audio, generator yields to Transcribe
4. Transcribe → Sends partial transcripts back → onTranscript callback
5. endStream() → Signal end, wait for final transcript
6. Transcribe → Sends final transcript → onTranscript callback
7. cleanup() → Release resources


Increase sending chunk interval from 100ms to 200ms?


### `src/websocket-handler.js`

Key Responsibilities:
- Connection Management: Each WebSocket connection gets a unique session ID
- Message Routing: Binary → audio, Text → control signals
- Transcribe Lifecycle: Starts session on first audio chunk, ends on end_stream signal
- Timeout Management: Connection timeout (35s) + inactivity timeout (60s)
- Error Handling: Sends errors to client, cleans up resources

Message Protocol:

Client → Server:
- Binary frames: Raw PCM audio chunks (sent directly to Transcribe)
- Text: {"type": "end_stream"} (signal end of recording)

Server → Client:
- {"type": "ready", "sessionId": "abc-123"} (connection established)
- {"type": "partial", "text": "hello"} (partial transcript)
- {"type": "final", "text": "hello world"} (final transcript)
- {"type": "error", "message": "..."} (error occurred)

### `src/server.js`

Server Structure:
- HTTP Server: Handles health checks and provides basic info endpoint
- WebSocket Server: Attached to HTTP server, handles upgrade requests
- Graceful Shutdown: Handles SIGTERM/SIGINT for clean ECS task termination
- Error Handling: Catches uncaught exceptions and unhandled rejections

Endpoints:
- `GET /health` → ALB health check (required)
- `GET /` → Service info (optional, useful for debugging)
- `WebSocket /` → STT streaming connection


====================
## Demo Scenarios

### Cancel Recording → Start Typing
- Mode automatically switches to keyboard
- Microphone icon appears in toggle button (not keyboard icon)
- "Voice input mode..." message disappears

