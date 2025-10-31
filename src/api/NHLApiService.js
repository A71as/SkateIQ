import axios from 'axios';
import NodeCache from 'node-cache';
import { logger } from '../utils/logger.js';

/**
 * NHL API Service - Handles all interactions with NHL stats API
 */
export class NHLApiService {
    constructor() {
        this.baseUrl = process.env.NHL_API_BASE_URL || 'https://statsapi.web.nhl.com/api/v1';
        this.cache = new NodeCache({ 
            stdTTL: parseInt(process.env.CACHE_TTL) || 300,
            checkperiod: 60 
        });
        
        this.axiosInstance = axios.create({
            baseURL: this.baseUrl,
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json'
            }
        });

        // Add request interceptor for logging
        this.axiosInstance.interceptors.request.use(
            config => {
                logger.debug(`NHL API Request: ${config.method?.toUpperCase()} ${config.url}`);
                return config;
            },
            error => Promise.reject(error)
        );
    }

    /**
     * Get player information by ID
     */
    async getPlayer(playerId) {
        const cacheKey = `player:${playerId}`;
        const cached = this.cache.get(cacheKey);
        
        if (cached) {
            logger.debug(`Cache hit for player ${playerId}`);
            return cached;
        }

        try {
            const response = await this.axiosInstance.get(`/people/${playerId}`);
            const playerData = response.data.people[0];
            
            const player = {
                playerId: playerData.id,
                fullName: playerData.fullName,
                firstName: playerData.firstName,
                lastName: playerData.lastName,
                primaryNumber: playerData.primaryNumber,
                birthDate: playerData.birthDate,
                currentAge: playerData.currentAge,
                birthCity: playerData.birthCity,
                birthCountry: playerData.birthCountry,
                nationality: playerData.nationality,
                height: playerData.height,
                weight: playerData.weight,
                active: playerData.active,
                rookie: playerData.rookie,
                shootsCatches: playerData.shootsCatches,
                rosterStatus: playerData.rosterStatus,
                currentTeam: playerData.currentTeam,
                primaryPosition: playerData.primaryPosition,
                lastUpdated: new Date().toISOString()
            };

            this.cache.set(cacheKey, player);
            return player;
        } catch (error) {
            logger.error(`Failed to fetch player ${playerId}:`, error.message);
            throw new Error(`Failed to fetch player data: ${error.message}`);
        }
    }

    /**
     * Get player statistics for a specific season or date range
     */
    async getPlayerStats(playerId, days = 30) {
        const cacheKey = `stats:${playerId}:${days}`;
        const cached = this.cache.get(cacheKey);
        
        if (cached) {
            return cached;
        }

        try {
            // Get current season
            const season = await this.getCurrentSeason();
            
            const response = await this.axiosInstance.get(
                `/people/${playerId}/stats?stats=statsSingleSeason&season=${season}`
            );

            const stats = response.data.stats[0]?.splits[0]?.stat || {};
            
            const playerStats = {
                playerId,
                season,
                games: stats.games || 0,
                goals: stats.goals || 0,
                assists: stats.assists || 0,
                points: stats.points || 0,
                plusMinus: stats.plusMinus || 0,
                pim: stats.pim || 0,
                shots: stats.shots || 0,
                shotPct: stats.shotPct || 0,
                gameWinningGoals: stats.gameWinningGoals || 0,
                overTimeGoals: stats.overTimeGoals || 0,
                powerPlayGoals: stats.powerPlayGoals || 0,
                powerPlayPoints: stats.powerPlayPoints || 0,
                shortHandedGoals: stats.shortHandedGoals || 0,
                shortHandedPoints: stats.shortHandedPoints || 0,
                blocked: stats.blocked || 0,
                hits: stats.hits || 0,
                faceOffPct: stats.faceOffPct || 0,
                timeOnIce: stats.timeOnIce || '0:00',
                lastUpdated: new Date().toISOString()
            };

            this.cache.set(cacheKey, playerStats);
            return playerStats;
        } catch (error) {
            logger.error(`Failed to fetch stats for player ${playerId}:`, error.message);
            return this.getEmptyStats(playerId);
        }
    }

    /**
     * Get recent game logs for a player
     */
    async getPlayerGameLog(playerId, limit = 10) {
        const cacheKey = `gamelog:${playerId}:${limit}`;
        const cached = this.cache.get(cacheKey);
        
        if (cached) {
            return cached;
        }

        try {
            const season = await this.getCurrentSeason();
            const response = await this.axiosInstance.get(
                `/people/${playerId}/stats?stats=gameLog&season=${season}`
            );

            const games = response.data.stats[0]?.splits || [];
            const gameLog = games.slice(0, limit).map(game => ({
                date: game.date,
                isHome: game.isHome,
                isWin: game.isWin,
                opponent: game.opponent,
                goals: game.stat.goals,
                assists: game.stat.assists,
                points: game.stat.points,
                plusMinus: game.stat.plusMinus,
                pim: game.stat.pim,
                shots: game.stat.shots,
                hits: game.stat.hits,
                blocked: game.stat.blocked,
                timeOnIce: game.stat.timeOnIce
            }));

            this.cache.set(cacheKey, gameLog);
            return gameLog;
        } catch (error) {
            logger.error(`Failed to fetch game log for player ${playerId}:`, error.message);
            return [];
        }
    }

    /**
     * Get upcoming games for a player's team
     */
    async getPlayerUpcomingGames(playerId, days = 7) {
        try {
            const player = await this.getPlayer(playerId);
            if (!player.currentTeam) {
                return [];
            }

            const teamId = player.currentTeam.id;
            return await this.getTeamUpcomingGames(teamId, days);
        } catch (error) {
            logger.error(`Failed to fetch upcoming games for player ${playerId}:`, error.message);
            return [];
        }
    }

    /**
     * Get upcoming games for a team
     */
    async getTeamUpcomingGames(teamId, days = 7) {
        const cacheKey = `upcoming:${teamId}:${days}`;
        const cached = this.cache.get(cacheKey);
        
        if (cached) {
            return cached;
        }

        try {
            const startDate = new Date().toISOString().split('T')[0];
            const endDate = new Date(Date.now() + days * 24 * 60 * 60 * 1000)
                .toISOString().split('T')[0];

            const response = await this.axiosInstance.get(
                `/schedule?teamId=${teamId}&startDate=${startDate}&endDate=${endDate}`
            );

            const games = [];
            response.data.dates?.forEach(date => {
                date.games.forEach(game => {
                    games.push({
                        gameId: game.gamePk,
                        date: game.gameDate,
                        gameType: game.gameType,
                        season: game.season,
                        homeTeam: game.teams.home.team,
                        awayTeam: game.teams.away.team,
                        venue: game.venue,
                        isHome: game.teams.home.team.id === teamId
                    });
                });
            });

            this.cache.set(cacheKey, games);
            return games;
        } catch (error) {
            logger.error(`Failed to fetch upcoming games for team ${teamId}:`, error.message);
            return [];
        }
    }

    /**
     * Get current NHL season
     */
    async getCurrentSeason() {
        const cacheKey = 'current:season';
        const cached = this.cache.get(cacheKey);
        
        if (cached) {
            return cached;
        }

        try {
            const response = await this.axiosInstance.get('/seasons/current');
            const season = response.data.seasons[0].seasonId;
            this.cache.set(cacheKey, season, 3600); // Cache for 1 hour
            return season;
        } catch (error) {
            logger.error('Failed to fetch current season:', error.message);
            // Fallback to calculated season
            return this.calculateCurrentSeason();
        }
    }

    /**
     * Calculate current season based on date
     */
    calculateCurrentSeason() {
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth() + 1;
        
        // NHL season typically starts in October
        if (month >= 10) {
            return `${year}${year + 1}`;
        } else {
            return `${year - 1}${year}`;
        }
    }

    /**
     * Get all NHL teams
     */
    async getAllTeams() {
        const cacheKey = 'all:teams';
        const cached = this.cache.get(cacheKey);
        
        if (cached) {
            return cached;
        }

        try {
            const response = await this.axiosInstance.get('/teams');
            const teams = response.data.teams.map(team => ({
                id: team.id,
                name: team.name,
                abbreviation: team.abbreviation,
                teamName: team.teamName,
                locationName: team.locationName,
                division: team.division,
                conference: team.conference,
                venue: team.venue
            }));

            this.cache.set(cacheKey, teams, 86400); // Cache for 24 hours
            return teams;
        } catch (error) {
            logger.error('Failed to fetch teams:', error.message);
            return [];
        }
    }

    /**
     * Get team roster
     */
    async getTeamRoster(teamId) {
        const cacheKey = `roster:${teamId}`;
        const cached = this.cache.get(cacheKey);
        
        if (cached) {
            return cached;
        }

        try {
            const response = await this.axiosInstance.get(`/teams/${teamId}/roster`);
            const roster = response.data.roster.map(player => ({
                playerId: player.person.id,
                fullName: player.person.fullName,
                jerseyNumber: player.jerseyNumber,
                position: player.position
            }));

            this.cache.set(cacheKey, roster, 3600); // Cache for 1 hour
            return roster;
        } catch (error) {
            logger.error(`Failed to fetch roster for team ${teamId}:`, error.message);
            return [];
        }
    }

    /**
     * Search players by name
     */
    async searchPlayers(searchTerm) {
        try {
            const teams = await this.getAllTeams();
            const allPlayers = [];

            for (const team of teams) {
                const roster = await this.getTeamRoster(team.id);
                allPlayers.push(...roster);
            }

            const searchLower = searchTerm.toLowerCase();
            return allPlayers.filter(player => 
                player.fullName.toLowerCase().includes(searchLower)
            );
        } catch (error) {
            logger.error(`Failed to search players with term "${searchTerm}":`, error.message);
            return [];
        }
    }

    /**
     * Get standings
     */
    async getStandings() {
        const cacheKey = 'standings';
        const cached = this.cache.get(cacheKey);
        
        if (cached) {
            return cached;
        }

        try {
            const response = await this.axiosInstance.get('/standings');
            const standings = response.data.records;
            this.cache.set(cacheKey, standings, 3600); // Cache for 1 hour
            return standings;
        } catch (error) {
            logger.error('Failed to fetch standings:', error.message);
            return [];
        }
    }

    /**
     * Helper method to get empty stats object
     */
    getEmptyStats(playerId) {
        return {
            playerId,
            season: this.calculateCurrentSeason(),
            games: 0,
            goals: 0,
            assists: 0,
            points: 0,
            plusMinus: 0,
            pim: 0,
            shots: 0,
            shotPct: 0,
            gameWinningGoals: 0,
            overTimeGoals: 0,
            powerPlayGoals: 0,
            powerPlayPoints: 0,
            shortHandedGoals: 0,
            shortHandedPoints: 0,
            blocked: 0,
            hits: 0,
            faceOffPct: 0,
            timeOnIce: '0:00',
            lastUpdated: new Date().toISOString()
        };
    }

    /**
     * Clear cache
     */
    clearCache(pattern = null) {
        if (pattern) {
            const keys = this.cache.keys();
            keys.forEach(key => {
                if (key.includes(pattern)) {
                    this.cache.del(key);
                }
            });
        } else {
            this.cache.flushAll();
        }
        logger.info(`Cache cleared${pattern ? ` for pattern: ${pattern}` : ''}`);
    }
}