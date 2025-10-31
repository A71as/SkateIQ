import { BaseAgent } from './BaseAgent.js';
import { logger } from '../utils/logger.js';
import moment from 'moment';

/**
 * Fantasy Hockey Agent - Persistent agent for managing fantasy teams and providing recommendations
 */
export class FantasyAgent extends BaseAgent {
    constructor(services) {
        super(services, 'fantasy-hockey-agent', {
            memorySize: 2000,
            persistenceInterval: 30000,
            autoSave: true
        });
        
        this.userTeams = new Map();
        this.playerDatabase = new Map();
        this.lastRecommendationUpdate = null;
        this.currentRecommendations = null;
    }

    async initialize() {
        await super.initialize();
        
        // Load user teams
        await this.loadUserTeams();
        
        // Load player database
        await this.loadPlayerDatabase();
        
        // Set up periodic updates
        this.setupPeriodicUpdates();
        
        logger.info('FantasyAgent initialized with team and player data');
    }

    async loadUserTeams() {
        try {
            const teams = await this.services.database.getAllUserTeams();
            teams.forEach(team => {
                this.userTeams.set(team.userId, team);
            });
            
            this.setState('userTeamsCount', this.userTeams.size);
            await this.addMemory('system', {
                action: 'loadUserTeams',
                teamsLoaded: this.userTeams.size
            });
            
            logger.info(`Loaded ${this.userTeams.size} user teams`);
        } catch (error) {
            logger.error('Failed to load user teams:', error);
        }
    }

    async loadPlayerDatabase() {
        try {
            const players = await this.services.database.getAllPlayers();
            players.forEach(player => {
                this.playerDatabase.set(player.playerId, player);
            });
            
            this.setState('playerDatabaseSize', this.playerDatabase.size);
            await this.addMemory('system', {
                action: 'loadPlayerDatabase',
                playersLoaded: this.playerDatabase.size
            });
            
            logger.info(`Loaded ${this.playerDatabase.size} players into database`);
        } catch (error) {
            logger.error('Failed to load player database:', error);
        }
    }

    setupPeriodicUpdates() {
        // Update player stats every hour
        this.statsUpdateInterval = setInterval(async () => {
            await this.updatePlayerStats();
        }, 60 * 60 * 1000);

        // Generate recommendations every 4 hours
        this.recommendationInterval = setInterval(async () => {
            await this.generateAllRecommendations();
        }, 4 * 60 * 60 * 1000);
    }

    async processInput(input) {
        const { type, data, userId } = input;
        
        try {
            switch (type) {
                case 'addPlayer':
                    return await this.addPlayerToTeam(userId, data.playerId, data.position);
                
                case 'removePlayer':
                    return await this.removePlayerFromTeam(userId, data.playerId);
                
                case 'setLineup':
                    return await this.setUserLineup(userId, data.lineup);
                
                case 'getRecommendations':
                    return await this.getUserRecommendations(userId, data.options);
                
                case 'updatePreferences':
                    return await this.updateUserPreferences(userId, data.preferences);
                
                case 'getPlayerAnalysis':
                    return await this.getPlayerAnalysis(data.playerId, data.days);
                
                default:
                    throw new Error(`Unknown input type: ${type}`);
            }
        } catch (error) {
            logger.error(`Error processing input for user ${userId}:`, error);
            await this.addMemory('error', {
                type,
                userId,
                error: error.message,
                data
            });
            throw error;
        }
    }

    async addPlayerToTeam(userId, playerId, position) {
        let userTeam = this.userTeams.get(userId);
        
        if (!userTeam) {
            userTeam = {
                userId,
                players: [],
                lineup: {},
                preferences: {},
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            };
            this.userTeams.set(userId, userTeam);
        }

        // Check if player already exists
        const existingPlayer = userTeam.players.find(p => p.playerId === playerId);
        if (existingPlayer) {
            throw new Error('Player already on team');
        }

        // Get player info
        const playerInfo = await this.getPlayerInfo(playerId);
        
        const teamPlayer = {
            playerId,
            position,
            addedAt: new Date().toISOString(),
            playerInfo
        };

        userTeam.players.push(teamPlayer);
        userTeam.updatedAt = new Date().toISOString();

        // Save to database
        await this.services.database.saveUserTeam(userTeam);

        // Add to memory
        await this.addMemory('teamChange', {
            userId,
            action: 'addPlayer',
            playerId,
            position,
            playerName: playerInfo.fullName
        });

        logger.info(`Added player ${playerInfo.fullName} to user ${userId}'s team`);
        return { success: true, player: teamPlayer };
    }

    async removePlayerFromTeam(userId, playerId) {
        const userTeam = this.userTeams.get(userId);
        if (!userTeam) {
            throw new Error('User team not found');
        }

        const playerIndex = userTeam.players.findIndex(p => p.playerId === playerId);
        if (playerIndex === -1) {
            throw new Error('Player not found on team');
        }

        const removedPlayer = userTeam.players.splice(playerIndex, 1)[0];
        userTeam.updatedAt = new Date().toISOString();

        // Remove from lineup if present
        Object.keys(userTeam.lineup).forEach(position => {
            if (userTeam.lineup[position] === playerId) {
                delete userTeam.lineup[position];
            }
        });

        // Save to database
        await this.services.database.saveUserTeam(userTeam);

        // Add to memory
        await this.addMemory('teamChange', {
            userId,
            action: 'removePlayer',
            playerId,
            playerName: removedPlayer.playerInfo?.fullName
        });

        logger.info(`Removed player ${removedPlayer.playerInfo?.fullName} from user ${userId}'s team`);
        return { success: true, removedPlayer };
    }

    async setUserLineup(userId, lineup) {
        const userTeam = this.userTeams.get(userId);
        if (!userTeam) {
            throw new Error('User team not found');
        }

        // Validate lineup
        const validationResult = await this.validateLineup(userTeam.players, lineup);
        if (!validationResult.valid) {
            throw new Error(`Invalid lineup: ${validationResult.errors.join(', ')}`);
        }

        userTeam.lineup = lineup;
        userTeam.updatedAt = new Date().toISOString();

        // Save to database
        await this.services.database.saveUserTeam(userTeam);

        // Add to memory
        await this.addMemory('teamChange', {
            userId,
            action: 'setLineup',
            lineup
        });

        logger.info(`Updated lineup for user ${userId}`);
        return { success: true, lineup };
    }

    async getUserRecommendations(userId, options = {}) {
        const userTeam = this.userTeams.get(userId);
        if (!userTeam) {
            throw new Error('User team not found');
        }

        const recommendations = await this.services.recommendations.generateUserRecommendations(
            userTeam,
            options
        );

        // Add to memory
        await this.addMemory('recommendation', {
            userId,
            recommendationsCount: recommendations.length,
            options
        });

        return recommendations;
    }

    async updateUserPreferences(userId, preferences) {
        let userTeam = this.userTeams.get(userId);
        if (!userTeam) {
            userTeam = {
                userId,
                players: [],
                lineup: {},
                preferences: {},
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            };
            this.userTeams.set(userId, userTeam);
        }

        userTeam.preferences = { ...userTeam.preferences, ...preferences };
        userTeam.updatedAt = new Date().toISOString();

        // Save to database
        await this.services.database.saveUserTeam(userTeam);

        // Add to memory
        await this.addMemory('teamChange', {
            userId,
            action: 'updatePreferences',
            preferences
        });

        return { success: true, preferences: userTeam.preferences };
    }

    async getPlayerInfo(playerId) {
        // First check local database
        let playerInfo = this.playerDatabase.get(playerId);
        
        if (!playerInfo) {
            // Fetch from NHL API
            try {
                playerInfo = await this.services.nhlApi.getPlayer(playerId);
                this.playerDatabase.set(playerId, playerInfo);
                
                // Save to database
                await this.services.database.savePlayer(playerInfo);
            } catch (error) {
                logger.error(`Failed to fetch player info for ${playerId}:`, error);
                throw new Error('Player not found');
            }
        }

        return playerInfo;
    }

    async getPlayerAnalysis(playerId, days = 30) {
        const playerInfo = await this.getPlayerInfo(playerId);
        const stats = await this.services.nhlApi.getPlayerStats(playerId, days);
        const upcomingGames = await this.services.nhlApi.getPlayerUpcomingGames(playerId, 7);
        
        const analysis = await this.services.recommendations.analyzePlayer(
            playerInfo,
            stats,
            upcomingGames
        );

        await this.addMemory('playerAnalysis', {
            playerId,
            playerName: playerInfo.fullName,
            days,
            analysis
        });

        return analysis;
    }

    async validateLineup(teamPlayers, lineup) {
        const errors = [];
        const playerIds = teamPlayers.map(p => p.playerId);
        
        // Check if all lineup players are on the team
        Object.values(lineup).forEach(playerId => {
            if (playerId && !playerIds.includes(playerId)) {
                errors.push(`Player ${playerId} not found on team`);
            }
        });

        // Add position-specific validations here
        // This would depend on your fantasy league rules

        return {
            valid: errors.length === 0,
            errors
        };
    }

    async updatePlayerStats() {
        logger.info('Updating player statistics...');
        
        try {
            const playerIds = Array.from(this.playerDatabase.keys());
            const chunkSize = 10;
            
            for (let i = 0; i < playerIds.length; i += chunkSize) {
                const chunk = playerIds.slice(i, i + chunkSize);
                
                await Promise.all(chunk.map(async (playerId) => {
                    try {
                        const stats = await this.services.nhlApi.getPlayerStats(playerId, 7);
                        await this.services.database.updatePlayerStats(playerId, stats);
                    } catch (error) {
                        logger.error(`Failed to update stats for player ${playerId}:`, error);
                    }
                }));
                
                // Small delay to avoid rate limiting
                await new Promise(resolve => setTimeout(resolve, 100));
            }
            
            this.setState('lastStatsUpdate', new Date().toISOString());
            logger.info('Player statistics update completed');
        } catch (error) {
            logger.error('Failed to update player statistics:', error);
        }
    }

    async generateAllRecommendations() {
        logger.info('Generating recommendations for all users...');
        
        try {
            for (const [userId, userTeam] of this.userTeams) {
                try {
                    const recommendations = await this.services.recommendations.generateUserRecommendations(userTeam);
                    await this.services.database.saveUserRecommendations(userId, recommendations);
                } catch (error) {
                    logger.error(`Failed to generate recommendations for user ${userId}:`, error);
                }
            }
            
            this.setState('lastRecommendationUpdate', new Date().toISOString());
            logger.info('Recommendation generation completed');
        } catch (error) {
            logger.error('Failed to generate recommendations:', error);
        }
    }

    async generateRecommendations() {
        // Generate recommendations for all users
        await this.generateAllRecommendations();
        return this.getState('lastRecommendationUpdate');
    }

    async shutdown() {
        if (this.statsUpdateInterval) {
            clearInterval(this.statsUpdateInterval);
        }
        
        if (this.recommendationInterval) {
            clearInterval(this.recommendationInterval);
        }
        
        await super.shutdown();
    }

    // Helper method to get agent status
    getStatus() {
        return {
            agentId: this.agentId,
            isInitialized: this.isInitialized,
            userTeamsCount: this.userTeams.size,
            playerDatabaseSize: this.playerDatabase.size,
            lastStatsUpdate: this.getState('lastStatsUpdate'),
            lastRecommendationUpdate: this.getState('lastRecommendationUpdate'),
            memoryEntries: this.memory.length
        };
    }
}