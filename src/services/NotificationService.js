import cron from 'node-cron';
import { logger } from '../utils/logger.js';

/**
 * Notification Service - Handles scheduled notifications and alerts
 */
export class NotificationService {
    constructor(database, recommendationEngine) {
        this.database = database;
        this.recommendationEngine = recommendationEngine;
        this.cronJobs = [];
        this.isRunning = false;
    }

    start() {
        if (this.isRunning) {
            logger.warn('Notification service is already running');
            return;
        }

        // Daily recommendations at 8 AM
        const schedule = process.env.NOTIFICATION_SCHEDULE || '0 8 * * *';
        
        const dailyJob = cron.schedule(schedule, async () => {
            await this.sendDailyRecommendations();
        });

        this.cronJobs.push(dailyJob);
        this.isRunning = true;

        logger.info(`Notification service started with schedule: ${schedule}`);
    }

    async sendDailyRecommendations() {
        logger.info('Generating daily recommendations...');
        
        try {
            const userTeams = await this.database.getAllUserTeams();
            
            for (const userTeam of userTeams) {
                try {
                    const recommendations = await this.recommendationEngine.generateUserRecommendations(
                        userTeam,
                        { includeStartSit: true, includeWaiverTargets: true }
                    );

                    // Save recommendations
                    await this.database.saveUserRecommendations(userTeam.userId, recommendations);

                    // Here you would send the actual notification (email, push, etc.)
                    await this.notifyUser(userTeam.userId, recommendations);

                    logger.info(`Sent daily recommendations to user ${userTeam.userId}`);
                } catch (error) {
                    logger.error(`Failed to send recommendations to user ${userTeam.userId}:`, error);
                }
            }

            logger.info('Daily recommendations completed');
        } catch (error) {
            logger.error('Failed to send daily recommendations:', error);
        }
    }

    async notifyUser(userId, recommendations) {
        // This is a placeholder for actual notification logic
        // You would implement email, push notifications, webhooks, etc.
        
        logger.debug(`Notification for user ${userId}:`, {
            startSitCount: recommendations.startSitRecommendations?.length || 0,
            alertsCount: recommendations.playerAlerts?.length || 0,
            waiverTargetsCount: recommendations.waiverTargets?.length || 0
        });

        // Example: You could emit an event for WebSocket notifications
        // this.emit('notification', { userId, recommendations });
    }

    stop() {
        this.cronJobs.forEach(job => job.stop());
        this.cronJobs = [];
        this.isRunning = false;
        logger.info('Notification service stopped');
    }
}