/**
 * Logger utility for the Fantasy Hockey Assistant
 */

const LOG_LEVELS = {
    debug: 0,
    info: 1,
    warn: 2,
    error: 3
};

class Logger {
    constructor() {
        this.level = LOG_LEVELS[process.env.LOG_LEVEL?.toLowerCase()] || LOG_LEVELS.info;
    }

    formatMessage(level, ...args) {
        const timestamp = new Date().toISOString();
        const levelStr = level.toUpperCase().padEnd(5);
        return `[${timestamp}] ${levelStr} ${args.map(arg => 
            typeof arg === 'object' ? JSON.stringify(arg, null, 2) : arg
        ).join(' ')}`;
    }

    debug(...args) {
        if (this.level <= LOG_LEVELS.debug) {
            console.log(this.formatMessage('debug', ...args));
        }
    }

    info(...args) {
        if (this.level <= LOG_LEVELS.info) {
            console.log(this.formatMessage('info', ...args));
        }
    }

    warn(...args) {
        if (this.level <= LOG_LEVELS.warn) {
            console.warn(this.formatMessage('warn', ...args));
        }
    }

    error(...args) {
        if (this.level <= LOG_LEVELS.error) {
            console.error(this.formatMessage('error', ...args));
        }
    }
}

export const logger = new Logger();