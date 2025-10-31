import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

import { DatabaseManager } from './database/DatabaseManager.js';
import { FantasyAgent } from './agents/FantasyAgent.js';
import { NHLApiService } from './api/NHLApiService.js';
import { RecommendationEngine } from './recommendations/RecommendationEngine.js';
import { NotificationService } from './services/NotificationService.js';
import { setupRoutes } from './routes/index.js';
import { logger } from './utils/logger.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables
dotenv.config();

class FantasyHockeyAssistant {
    constructor() {
        this.app = express();
        this.port = process.env.PORT || 3000;
        this.services = {};
        this.agent = null;
    }

    async initialize() {
        try {
            logger.info('🏒 Initializing NHL Fantasy Hockey Assistant...');

            // Initialize core services
            await this.initializeServices();
            
            // Setup middleware
            this.setupMiddleware();
            
            // Setup routes
            this.setupRoutes();
            
            // Initialize the persistent agent
            await this.initializeAgent();
            
            // Start notification service
            this.startNotificationService();
            
            logger.info('✅ NHL Fantasy Hockey Assistant initialized successfully');
        } catch (error) {
            logger.error('❌ Failed to initialize Fantasy Hockey Assistant:', error);
            throw error;
        }
    }

    async initializeServices() {
        // Initialize database
        this.services.database = new DatabaseManager();
        await this.services.database.initialize();

        // Initialize NHL API service
        this.services.nhlApi = new NHLApiService();

        // Initialize recommendation engine
        this.services.recommendations = new RecommendationEngine(
            this.services.database,
            this.services.nhlApi
        );

        // Initialize notification service
        this.services.notifications = new NotificationService(
            this.services.database,
            this.services.recommendations
        );

        logger.info('✅ Core services initialized');
    }

    setupMiddleware() {
        // Security middleware
        this.app.use(helmet());
        
        // CORS configuration
        this.app.use(cors({
            origin: process.env.NODE_ENV === 'production' 
                ? process.env.ALLOWED_ORIGINS?.split(',') 
                : true,
            credentials: true
        }));

        // Rate limiting
        const limiter = rateLimit({
            windowMs: 15 * 60 * 1000, // 15 minutes
            max: process.env.API_RATE_LIMIT || 100
        });
        this.app.use('/api/', limiter);

        // Body parsing
        this.app.use(express.json());
        this.app.use(express.urlencoded({ extended: true }));

        // Static files
        this.app.use(express.static(path.join(__dirname, 'web/public')));

        logger.info('✅ Middleware configured');
    }

    setupRoutes() {
        setupRoutes(this.app, this.services);
        logger.info('✅ Routes configured');
    }

    async initializeAgent() {
        this.agent = new FantasyAgent(this.services);
        await this.agent.initialize();
        
        // Make agent available to routes
        this.app.locals.agent = this.agent;
        
        logger.info('✅ Persistent Fantasy Agent initialized');
    }

    startNotificationService() {
        if (process.env.ENABLE_NOTIFICATIONS === 'true') {
            this.services.notifications.start();
            logger.info('✅ Notification service started');
        }
    }

    async start() {
        await this.initialize();
        
        this.app.listen(this.port, () => {
            logger.info(`🚀 NHL Fantasy Hockey Assistant running on port ${this.port}`);
            logger.info(`📱 Web interface: http://localhost:${this.port}`);
            logger.info(`🔌 API endpoint: http://localhost:${this.port}/api`);
        });
    }

    async shutdown() {
        logger.info('🛑 Shutting down NHL Fantasy Hockey Assistant...');
        
        if (this.services.notifications) {
            this.services.notifications.stop();
        }
        
        if (this.services.database) {
            await this.services.database.close();
        }
        
        logger.info('✅ Shutdown complete');
        process.exit(0);
    }
}

// Handle graceful shutdown
process.on('SIGINT', async () => {
    if (global.fantasyAssistant) {
        await global.fantasyAssistant.shutdown();
    }
});

process.on('SIGTERM', async () => {
    if (global.fantasyAssistant) {
        await global.fantasyAssistant.shutdown();
    }
});

// Start the application
async function main() {
    try {
        const assistant = new FantasyHockeyAssistant();
        global.fantasyAssistant = assistant;
        await assistant.start();
    } catch (error) {
        logger.error('💥 Failed to start Fantasy Hockey Assistant:', error);
        process.exit(1);
    }
}

// Run if this is the main module
if (import.meta.url === `file://${process.argv[1]}`) {
    main();
}

export { FantasyHockeyAssistant };