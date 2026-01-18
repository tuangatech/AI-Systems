/**
 * Query Handler for Voice-to-Voice Conversation
 * Processes user queries and returns text + audio responses
 */

const { synthesizeSpeech } = require('../services/polly-service');
const { createLogger } = require('../utils/logger');

const logger = createLogger('query-handler');

/**
 * Mock response generator
 * In production, this would call your RAG service
 * 
 * @param {string} query - User's query text
 * @returns {string} - Response text
 */
const generateMockResponse = (query) => {
    // Simple keyword-based variations for demo purposes
    const lowerQuery = query.toLowerCase();
    
    if (lowerQuery.includes('hello') || lowerQuery.includes('hi')) {
        return `Hello! I'm Matthew, your AI assistant. In a production system, I would search our knowledge base to help answer your question: "${query}"`;
    }
    
    // Default response for "The pump is leaking. What are the maximum operating pressure and flow rate of the Power Team PE 462?"
    return `The pump reaches a maximum pressure of 10,000 PSI. As a two-speed pump, it provides high oil volume at low pressure for rapid cylinder advance (500 cu. in./min at 0 PSI), then automatically shifts to high pressure stage (46 cu. in./min at 10,000 PSI) once a load is encountered`;
};

/**
 * Process user query and return response with audio
 * 
 * @param {string} queryText - User's query text
 * @returns {Promise<Object>} - { text, audio, audioData, duration, success, error }
 */
const processQuery = async (queryText) => {
    const startTime = Date.now();
    const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    logger.info('Processing query', {
        requestId,
        queryLength: queryText ? queryText.length : 0,
        preview: queryText ? queryText.substring(0, 50) : ''
    });

    try {
        // Validate input
        if (!queryText || typeof queryText !== 'string' || queryText.trim().length === 0) {
            throw new Error('Query text is required');
        }

        const trimmedQuery = queryText.trim();

        // Generate text response (mock)
        const responseText = generateMockResponse(trimmedQuery);
        
        logger.info('Generated text response', {
            requestId,
            responseLength: responseText.length
        });

        // Synthesize speech
        let audioResult = null;
        let synthesisError = null;

        try {
            audioResult = await synthesizeSpeech(responseText);
            
            logger.info('Audio synthesis successful', {
                requestId,
                duration: audioResult.duration,
                audioSize: audioResult.audioData.length
            });
        } catch (error) {
            synthesisError = error.message;
            
            logger.error('Audio synthesis failed, returning text-only response', {
                requestId,
                error: error.message
            });
        }

        const processingTime = Date.now() - startTime;

        const response = {
            success: true,
            text: responseText,
            audio: audioResult ? audioResult.audioData : null,
            duration: audioResult ? audioResult.duration : null,
            format: audioResult ? audioResult.format : null,
            voiceId: audioResult ? audioResult.voiceId : null,
            metadata: {
                requestId,
                processingTime,
                synthesisTime: audioResult ? audioResult.synthesisTime : null,
                queryLength: trimmedQuery.length,
                responseLength: responseText.length,
                hasAudio: !!audioResult,
                synthesisError: synthesisError
            }
        };

        logger.info('Query processed successfully', {
            requestId,
            processingTime,
            hasAudio: !!audioResult
        });

        return response;

    } catch (error) {
        const processingTime = Date.now() - startTime;
        
        logger.error('Query processing failed', {
            requestId,
            error: error.message,
            stack: error.stack,
            processingTime
        });

        return {
            success: false,
            text: null,
            audio: null,
            error: error.message,
            metadata: {
                requestId,
                processingTime
            }
        };
    }
};

/**
 * Validate query request body
 * @param {Object} body 
 * @returns {{ valid: boolean, error?: string }}
 */
const validateQueryRequest = (body) => {
    if (!body) {
        return { valid: false, error: 'Request body is required' };
    }

    if (!body.text || typeof body.text !== 'string') {
        return { valid: false, error: 'Text field is required and must be a string' };
    }

    if (body.text.trim().length === 0) {
        return { valid: false, error: 'Text field cannot be empty' };
    }

    if (body.text.length > 5000) {
        return { valid: false, error: 'Text field exceeds maximum length of 5000 characters' };
    }

    return { valid: true };
};

module.exports = {
    processQuery,
    validateQueryRequest,
    generateMockResponse
};
