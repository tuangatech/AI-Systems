/**
 * AWS Polly Text-to-Speech Service
 * Synthesizes text into natural-sounding speech using AWS Polly Neural voices
 */

const {
    PollyClient,
    SynthesizeSpeechCommand
} = require('@aws-sdk/client-polly');
const { createLogger } = require('../utils/logger');

const logger = createLogger('polly-service');

// Polly configuration
const POLLY_CONFIG = {
    region: process.env.AWS_REGION || 'us-east-1',
    voiceId: process.env.POLLY_VOICE_ID || 'Matthew',
    engine: 'neural', // Neural engine for most natural sound
    outputFormat: 'mp3',
    sampleRate: '24000', // High quality audio
    textType: 'text', // Can be 'text' or 'ssml' for advanced control
    languageCode: 'en-US'
};

// Max text length for Polly (AWS limit is 3000 characters for neural voices)
const MAX_TEXT_LENGTH = 3000;

/**
 * Create Polly client instance
 */
const createPollyClient = () => {
    return new PollyClient({
        region: POLLY_CONFIG.region
    });
};

/**
 * Synthesize speech from text using AWS Polly
 * 
 * @param {string} text - Text to synthesize
 * @param {Object} options - Optional synthesis parameters
 * @param {string} options.voiceId - Voice ID (default: Matthew)
 * @param {number} options.playbackRate - Speed multiplier (not used in synthesis, handled client-side)
 * @returns {Promise<Object>} - { audioData: string (base64), duration: number, format: string }
 */
const synthesizeSpeech = async (text, options = {}) => {
    const startTime = Date.now();

    try {
        // Validate input
        if (!text || typeof text !== 'string') {
            throw new Error('Text must be a non-empty string');
        }

        // Truncate if too long
        const truncatedText = text.length > MAX_TEXT_LENGTH 
            ? text.substring(0, MAX_TEXT_LENGTH) + '...'
            : text;

        if (text.length > MAX_TEXT_LENGTH) {
            logger.warn('Text truncated for Polly synthesis', {
                originalLength: text.length,
                truncatedLength: truncatedText.length
            });
        }

        logger.info('Starting speech synthesis', {
            textLength: truncatedText.length,
            voiceId: options.voiceId || POLLY_CONFIG.voiceId,
            engine: POLLY_CONFIG.engine
        });

        // Create Polly client
        const client = createPollyClient();

        // Prepare synthesis command
        const command = new SynthesizeSpeechCommand({
            Text: truncatedText,
            VoiceId: options.voiceId || POLLY_CONFIG.voiceId,
            Engine: POLLY_CONFIG.engine,
            OutputFormat: POLLY_CONFIG.outputFormat,
            SampleRate: POLLY_CONFIG.sampleRate,
            TextType: POLLY_CONFIG.textType,
            LanguageCode: POLLY_CONFIG.languageCode
        });

        // Execute synthesis
        const response = await client.send(command);

        if (!response.AudioStream) {
            throw new Error('No audio stream returned from Polly');
        }

        // Convert audio stream to buffer
        const audioBuffer = await streamToBuffer(response.AudioStream);

        // Convert buffer to base64
        const base64Audio = audioBuffer.toString('base64');

        // Estimate duration (approximate: MP3 bitrate ~32kbps for speech)
        // More accurate: parse MP3 headers, but this is good enough for POC
        const estimatedDuration = estimateMp3Duration(audioBuffer.length);

        const synthesisTime = Date.now() - startTime;

        logger.info('Speech synthesis completed', {
            audioSize: audioBuffer.length,
            base64Size: base64Audio.length,
            estimatedDuration,
            synthesisTime,
            voiceId: options.voiceId || POLLY_CONFIG.voiceId
        });

        return {
            audioData: `data:audio/mp3;base64,${base64Audio}`,
            duration: estimatedDuration,
            format: 'mp3',
            voiceId: options.voiceId || POLLY_CONFIG.voiceId,
            synthesisTime
        };

    } catch (error) {
        logger.error('Speech synthesis failed', {
            error: error.message,
            stack: error.stack,
            textLength: text ? text.length : 0
        });

        throw new Error(`Failed to synthesize speech: ${error.message}`);
    }
};

/**
 * Convert ReadableStream to Buffer
 * @param {ReadableStream} stream 
 * @returns {Promise<Buffer>}
 */
const streamToBuffer = async (stream) => {
    const chunks = [];
    
    for await (const chunk of stream) {
        chunks.push(chunk);
    }
    
    return Buffer.concat(chunks);
};

/**
 * Estimate MP3 audio duration based on file size
 * Formula: duration (seconds) ≈ fileSize (bytes) / (bitrate / 8)
 * For Polly neural voices at 24kHz: ~32kbps average bitrate
 * 
 * @param {number} fileSizeBytes 
 * @returns {number} - Duration in seconds
 */
const estimateMp3Duration = (fileSizeBytes) => {
    const bitrateKbps = 32; // Average bitrate for Polly neural voices
    const bytesPerSecond = (bitrateKbps * 1000) / 8;
    const durationSeconds = fileSizeBytes / bytesPerSecond;
    
    // Round to 1 decimal place
    return Math.round(durationSeconds * 10) / 10;
};

/**
 * Test Polly connection and configuration
 * @returns {Promise<boolean>}
 */
const testPollyConnection = async () => {
    try {
        logger.info('Testing Polly connection...');
        
        const result = await synthesizeSpeech('Testing connection to AWS Polly.');
        
        logger.info('Polly connection test successful', {
            audioSize: result.audioData.length,
            duration: result.duration
        });
        
        return true;
    } catch (error) {
        logger.error('Polly connection test failed', {
            error: error.message
        });
        
        return false;
    }
};

/**
 * Get available voice information
 * @returns {Object} - Voice configuration details
 */
const getVoiceInfo = () => {
    return {
        voiceId: POLLY_CONFIG.voiceId,
        engine: POLLY_CONFIG.engine,
        languageCode: POLLY_CONFIG.languageCode,
        description: 'Matthew - US English Male, Neural engine for natural speech',
        features: [
            'Neural TTS for natural prosody',
            'High-quality 24kHz audio',
            'Optimized for conversational AI',
            'Supports SSML for advanced control'
        ]
    };
};

module.exports = {
    synthesizeSpeech,
    testPollyConnection,
    getVoiceInfo,
    POLLY_CONFIG
};
