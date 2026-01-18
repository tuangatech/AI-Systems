/**
 * HTTP Routes for Query API
 * Handles POST /query endpoint for text + audio responses
 */

const { processQuery, validateQueryRequest } = require('./query-handler');
const { testPollyConnection, getVoiceInfo } = require('../services/polly-service');
const { createLogger } = require('../utils/logger');

const logger = createLogger('query-routes');

/**
 * Handle POST /query request
 * 
 * Request body: { text: string }
 * Response: { success, text, audio, duration, metadata }
 */
const handleQueryRequest = async (req, res) => {
    logger.info('Received query request', {
        method: req.method,
        url: req.url,
        contentType: req.headers['content-type']
    });

    try {
        // Parse request body
        let body;
        try {
            body = await parseRequestBody(req);
        } catch (error) {
            logger.error('Failed to parse request body', { error: error.message });
            return sendJsonResponse(res, 400, {
                success: false,
                error: 'Invalid JSON in request body'
            });
        }

        // Validate request
        const validation = validateQueryRequest(body);
        if (!validation.valid) {
            logger.warn('Invalid query request', { error: validation.error });
            return sendJsonResponse(res, 400, {
                success: false,
                error: validation.error
            });
        }

        // Process query
        const result = await processQuery(body.text);

        if (!result.success) {
            return sendJsonResponse(res, 500, result);
        }

        // Return successful response
        return sendJsonResponse(res, 200, result);

    } catch (error) {
        logger.error('Unexpected error in query handler', {
            error: error.message,
            stack: error.stack
        });

        return sendJsonResponse(res, 500, {
            success: false,
            error: 'Internal server error',
            message: error.message
        });
    }
};

/**
 * Handle GET /query/test - Test Polly connection
 */
const handleTestRequest = async (req, res) => {
    logger.info('Testing Polly connection');

    try {
        const isConnected = await testPollyConnection();

        return sendJsonResponse(res, 200, {
            success: true,
            pollyConnected: isConnected,
            voiceInfo: getVoiceInfo(),
            timestamp: new Date().toISOString()
        });

    } catch (error) {
        logger.error('Test endpoint error', { error: error.message });

        return sendJsonResponse(res, 500, {
            success: false,
            error: 'Failed to test Polly connection',
            message: error.message
        });
    }
};

/**
 * Handle GET /query/voice-info - Get voice configuration
 */
const handleVoiceInfoRequest = (req, res) => {
    logger.info('Voice info requested');

    return sendJsonResponse(res, 200, {
        success: true,
        voice: getVoiceInfo()
    });
};

/**
 * Parse JSON request body
 * @param {http.IncomingMessage} req 
 * @returns {Promise<Object>}
 */
const parseRequestBody = (req) => {
    return new Promise((resolve, reject) => {
        let body = '';

        req.on('data', chunk => {
            body += chunk.toString();
        });

        req.on('end', () => {
            try {
                const parsed = JSON.parse(body);
                resolve(parsed);
            } catch (error) {
                reject(new Error('Invalid JSON'));
            }
        });

        req.on('error', error => {
            reject(error);
        });
    });
};

/**
 * Send JSON response with proper headers
 * @param {http.ServerResponse} res 
 * @param {number} statusCode 
 * @param {Object} data 
 */
const sendJsonResponse = (res, statusCode, data) => {
    res.writeHead(statusCode, {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*', // Configure properly in production
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type'
    });
    res.end(JSON.stringify(data));
};

/**
 * Handle OPTIONS preflight request (CORS)
 */
const handleOptionsRequest = (req, res) => {
    res.writeHead(204, {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '86400'
    });
    res.end();
};

module.exports = {
    handleQueryRequest,
    handleTestRequest,
    handleVoiceInfoRequest,
    handleOptionsRequest
};
