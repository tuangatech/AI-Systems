// src/components/AudioPlayer.tsx

import React, { useEffect, useRef, useState } from 'react';
import { AudioPlayerState } from '../types';
import './AudioPlayer.css';

interface AudioPlayerProps {
    audioData: string | null;  // data:audio/mp3;base64,...
    autoPlay?: boolean;
    playbackRate?: number;
    onPlaybackStart?: () => void;
    onPlaybackEnd?: () => void;
    onPlaybackError?: (error: Error) => void;
}

export const AudioPlayer: React.FC<AudioPlayerProps> = ({
    audioData,
    autoPlay = true,
    playbackRate = 1.25,  // 1.25x speed for natural conversation
    onPlaybackStart,
    onPlaybackEnd,
    onPlaybackError,
}) => {
    const audioRef = useRef<HTMLAudioElement | null>(null);
    const [playerState, setPlayerState] = useState<AudioPlayerState>('loading');
    const [currentTime, setCurrentTime] = useState(0);
    const [duration, setDuration] = useState(0);
    const [progress, setProgress] = useState(0);

    // Initialize audio element
    useEffect(() => {
        if (!audioData) {
            return;
        }

        const audio = new Audio(audioData);
        audioRef.current = audio;

        // Set playback rate
        audio.playbackRate = playbackRate;

        // Event listeners
        audio.addEventListener('loadedmetadata', handleLoadedMetadata);
        audio.addEventListener('timeupdate', handleTimeUpdate);
        audio.addEventListener('playing', handlePlaying);
        audio.addEventListener('pause', handlePause);
        audio.addEventListener('ended', handleEnded);
        audio.addEventListener('error', handleError);

        // Auto-play if enabled
        if (autoPlay) {
            audio.play().catch(handlePlayError);
        }

        // Cleanup
        return () => {
            audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
            audio.removeEventListener('timeupdate', handleTimeUpdate);
            audio.removeEventListener('playing', handlePlaying);
            audio.removeEventListener('pause', handlePause);
            audio.removeEventListener('ended', handleEnded);
            audio.removeEventListener('error', handleError);
            audio.pause();
            audio.src = '';
        };
    }, [audioData, autoPlay, playbackRate]);

    const handleLoadedMetadata = () => {
        if (audioRef.current) {
            setDuration(audioRef.current.duration);
        }
    };

    const handleTimeUpdate = () => {
        if (audioRef.current) {
            const current = audioRef.current.currentTime;
            const total = audioRef.current.duration;
            setCurrentTime(current);
            setProgress(total > 0 ? (current / total) * 100 : 0);
        }
    };

    const handlePlaying = () => {
        setPlayerState('playing');
        onPlaybackStart?.();
    };

    const handlePause = () => {
        setPlayerState('paused');
    };

    const handleEnded = () => {
        setPlayerState('ended');
        onPlaybackEnd?.();
    };

    const handleError = (event: Event) => {
        const error = new Error('Audio playback failed');
        setPlayerState('error');
        onPlaybackError?.(error);
        console.error('Audio playback error:', event);
    };

    const handlePlayError = (error: unknown) => {
        const playbackError = error instanceof Error 
            ? error 
            : new Error('Failed to start audio playback');
        setPlayerState('error');
        onPlaybackError?.(playbackError);
        console.error('Failed to play audio:', error);
    };

    // Format time as MM:SS
    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    if (!audioData) {
        return null;
    }

    return (
        <div className="audio-player">
            <div className="audio-player-header">
                <div className="speaker-icon">
                    {playerState === 'playing' ? '🔊' : '🔇'}
                </div>
                <div className="speaker-label">
                    {playerState === 'playing' && 'AI Assistant is speaking...'}
                    {playerState === 'loading' && 'Loading audio...'}
                    {playerState === 'ended' && 'Playback complete'}
                    {playerState === 'error' && 'Audio error'}
                </div>
            </div>

            {/* Progress bar */}
            <div className="audio-progress-container">
                <div className="audio-progress-bar">
                    <div 
                        className="audio-progress-fill"
                        style={{ width: `${progress}%` }}
                    />
                </div>
                <div className="audio-time-display">
                    <span className="current-time">{formatTime(currentTime)}</span>
                    <span className="duration-time">{formatTime(duration)}</span>
                </div>
            </div>

            {/* Playback info */}
            {playerState === 'playing' && (
                <div className="audio-info">
                    <span className="playback-rate">▶ {playbackRate}x speed</span>
                </div>
            )}
        </div>
    );
};
