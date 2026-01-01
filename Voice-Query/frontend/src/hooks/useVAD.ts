// src/hooks/useVAD.ts

import { useState, useEffect, useRef } from 'react';
import { CONFIG } from '../utils/constants';

interface UseVADReturn {
    isSilent: boolean;
    silenceDuration: number;
    shouldAutoStop: boolean;
}

/**
 * Voice Activity Detection hook
 * Monitors audio level (RMS) to detect when user stops speaking
 * 
 * @param audioLevel - Current RMS value from audio processing (0.0 - 1.0)
 * @param recordingDuration - How long recording has been active (ms)
 * @param isRecording - Whether recording is currently active
 */
export const useVAD = (
    audioLevel: number,
    recordingDuration: number,
    isRecording: boolean
): UseVADReturn => {
    const [isSilent, setIsSilent] = useState(false);
    const [silenceDuration, setSilenceDuration] = useState(0);
    const [shouldAutoStop, setShouldAutoStop] = useState(false);

    const lastCheckTimeRef = useRef<number>(Date.now());
    const silenceStartTimeRef = useRef<number | null>(null);

    useEffect(() => {
        if (!isRecording) {
            // Reset when not recording
            setIsSilent(false);
            setSilenceDuration(0);
            setShouldAutoStop(false);
            silenceStartTimeRef.current = null;
            return;
        }

        // Don't start VAD until minimum recording duration is met
        if (recordingDuration < CONFIG.MIN_RECORDING_DURATION) {
            return;
        }

        const now = Date.now();
        const timeSinceLastCheck = now - lastCheckTimeRef.current;

        // Only check every VAD_SAMPLE_INTERVAL (100ms)
        if (timeSinceLastCheck < CONFIG.VAD_SAMPLE_INTERVAL) {
            return;
        }

        lastCheckTimeRef.current = now;

        // Determine if current audio level indicates silence
        const isCurrentlySilent = audioLevel < CONFIG.VAD_THRESHOLD;

        if (isCurrentlySilent) {
            // Start tracking silence if not already
            if (silenceStartTimeRef.current === null) {
                silenceStartTimeRef.current = now;
            }

            const currentSilenceDuration = now - silenceStartTimeRef.current;
            setSilenceDuration(currentSilenceDuration);
            setIsSilent(true);

            // Check if silence has lasted long enough to trigger auto-stop
            if (currentSilenceDuration >= CONFIG.SILENCE_DURATION) {
                setShouldAutoStop(true);
            }
        } else {
            // Voice detected - reset silence tracking
            silenceStartTimeRef.current = null;
            setSilenceDuration(0);
            setIsSilent(false);
            setShouldAutoStop(false);
        }
    }, [audioLevel, recordingDuration, isRecording]);

    return {
        isSilent,
        silenceDuration,
        shouldAutoStop,
    };
};