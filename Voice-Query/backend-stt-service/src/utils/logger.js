/**
 * Simple logging utility with timestamp and log levels
 * Output goes to stdout/stderr (captured by CloudWatch Logs)
 */

const LOG_LEVELS = {
    ERROR: 'ERROR',
    WARN: 'WARN',
    INFO: 'INFO',
    DEBUG: 'DEBUG'
};

const LOG_LEVEL = process.env.LOG_LEVEL?.toUpperCase() || 'INFO';

// Determine which levels should be logged based on LOG_LEVEL setting
const shouldLog = (level) => {
    const levels = ['ERROR', 'WARN', 'INFO', 'DEBUG'];
    const currentIndex = levels.indexOf(LOG_LEVEL);
    const requestedIndex = levels.indexOf(level);
    return requestedIndex <= currentIndex;
};

/**
 * Format log message with timestamp and level
 */
const formatMessage = (level, sessionId, message, data = null) => {
    const timestamp = new Date().toISOString();
    const sessionPrefix = sessionId ? `[${sessionId}]` : '';
    const baseMessage = `${timestamp} ${level} ${sessionPrefix} ${message}`;

    if (data) {
        return `${baseMessage} ${JSON.stringify(data)}`;
    }
    return baseMessage;
};

/**
 * Logger class with session context
 */
class Logger {
    constructor(sessionId = null) {
        this.sessionId = sessionId;
    }

    error(message, data = null) {
        if (shouldLog(LOG_LEVELS.ERROR)) {
            console.error(formatMessage(LOG_LEVELS.ERROR, this.sessionId, message, data));
        }
    }

    warn(message, data = null) {
        if (shouldLog(LOG_LEVELS.WARN)) {
            console.warn(formatMessage(LOG_LEVELS.WARN, this.sessionId, message, data));
        }
    }

    info(message, data = null) {
        if (shouldLog(LOG_LEVELS.INFO)) {
            console.log(formatMessage(LOG_LEVELS.INFO, this.sessionId, message, data));
        }
    }

    debug(message, data = null) {
        if (shouldLog(LOG_LEVELS.DEBUG)) {
            console.log(formatMessage(LOG_LEVELS.DEBUG, this.sessionId, message, data));
        }
    }
}

/**
 * Create logger instance with optional session ID
 */
const createLogger = (sessionId = null) => {
    return new Logger(sessionId);
};

// Export default logger (no session context)
const logger = new Logger();

module.exports = {
    logger,
    createLogger,
    LOG_LEVELS
};