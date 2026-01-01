/**
 * Main Server Entry Point
 * HTTP server with WebSocket upgrade support for STT streaming
 */

const http = require('http');
const { WebSocketServer } = require('ws');
const { handleConnection } = require('./websocket-handler');
const { logger } = require('./utils/logger');

// Server configuration
const PORT = parseInt(process.env.PORT || '8080', 10);
const AWS_REGION = process.env.AWS_REGION || 'us-east-1';

/**
 * Create HTTP server with health check endpoint
 */
const server = http.createServer((req, res) => {
    // Health check endpoint for ALB target group
    if (req.url === '/health' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            status: 'healthy',
            timestamp: new Date().toISOString(),
            region: AWS_REGION,
            uptime: process.uptime()
        }));
        return;
    }

    // Root endpoint - basic info
    if (req.url === '/' && req.method === 'GET') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
            service: 'STT WebSocket Service',
            version: '1.0.0',
            status: 'running',
            endpoints: {
                health: '/health',
                websocket: 'ws://<host>:<port>/'
            }
        }));
        return;
    }

    // 404 for all other routes
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Not found' }));
});

/**
 * Create WebSocket server attached to HTTP server
 */
const wss = new WebSocketServer({
    server,
    // Only handle WebSocket upgrade requests (not all HTTP requests)
    path: '/'
});

/**
 * Handle WebSocket connections
 */
wss.on('connection', (ws, request) => {
    handleConnection(ws, request);
});

/**
 * Handle WebSocket server errors
 */
wss.on('error', (error) => {
    logger.error('WebSocket server error', { error: error.message });
});

/**
 * Start server
 */
server.listen(PORT, () => {
    logger.info(`STT WebSocket service started`, {
        port: PORT,
        region: AWS_REGION,
        nodeVersion: process.version,
        pid: process.pid
    });
});

/**
 * Graceful shutdown handling
 */
const shutdown = (signal) => {
    logger.info(`Received ${signal}, shutting down gracefully...`);

    // Stop accepting new connections
    wss.close(() => {
        logger.info('WebSocket server closed');
    });

    server.close(() => {
        logger.info('HTTP server closed');
        process.exit(0);
    });

    // Force shutdown after 10 seconds
    setTimeout(() => {
        logger.error('Forced shutdown after timeout');
        process.exit(1);
    }, 10000);
};

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

/**
 * Handle uncaught errors
 */
process.on('uncaughtException', (error) => {
    logger.error('Uncaught exception', { error: error.message, stack: error.stack });
    process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
    logger.error('Unhandled rejection', { reason, promise });
    process.exit(1);
});