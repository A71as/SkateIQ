import _ from 'lodash';
import moment from 'moment';
import { logger } from '../utils/logger.js';

/**
 * Recommendation Engine - Analyzes player performance and generates roster recommendations
 */
export class RecommendationEngine {
    constructor(database, nhlApi) {
        this.database = database;
        this.nhlApi = nhlApi;
        
        // Scoring weights for different stat categories
        this.scoringWeights = {
            goals: 3.0,
            assists: 2.0,
            powerPlayGoals: 1.5,
            powerPlayPoints: 1.0,
            shortHandedGoals: 2.0,
            shots: 0.3,
            hits: 0.2,
            blocked: 0.2,
            plusMinus: 0.5,
            faceOffPct: 0.1
        };

        // Trend analysis weights
        this.trendWeights = {
            last3Games: 0.4,
            last7Games: 0.3,
            last14Games: 0.2,
            seasonAverage: 0.1
        };
    }

    /**
     * Generate comprehensive recommendations for a user's team
     */
    async generateUserRecommendations(userTeam, options = {}) {
        const {
            includeStartSit = true,
            includeWaiverTargets = true,
            includeTradeTargets = false,
            daysAhead = 7
        } = options;

        const recommendations = {
            userId: userTeam.userId,
            generatedAt: new Date().toISOString(),
            startSitRecommendations: [],
            waiverTargets: [],
            tradeTargets: [],
            playerAlerts: [],
            lineupOptimization: null
        };

        try {
            // Generate start/sit recommendations
            if (includeStartSit && userTeam.players.length > 0) {
                recommendations.startSitRecommendations = await this.generateStartSitRecommendations(
                    userTeam,
                    daysAhead
                );
            }

            // Find waiver wire targets
            if (includeWaiverTargets) {
                recommendations.waiverTargets = await this.findWaiverTargets(userTeam);
            }

            // Generate lineup optimization
            recommendations.lineupOptimization = await this.optimizeLineup(userTeam, daysAhead);

            // Check for player alerts (injuries, cold streaks, etc.)
            recommendations.playerAlerts = await this.generatePlayerAlerts(userTeam);

            logger.info(`Generated recommendations for user ${userTeam.userId}`);
            return recommendations;
        } catch (error) {
            logger.error(`Failed to generate recommendations for user ${userTeam.userId}:`, error);
            throw error;
        }
    }

    /**
     * Generate start/sit recommendations based on upcoming matchups
     */
    async generateStartSitRecommendations(userTeam, daysAhead = 7) {
        const recommendations = [];

        for (const teamPlayer of userTeam.players) {
            try {
                const analysis = await this.analyzePlayerForPeriod(
                    teamPlayer.playerId,
                    daysAhead
                );

                const recommendation = {
                    playerId: teamPlayer.playerId,
                    playerName: teamPlayer.playerInfo?.fullName,
                    position: teamPlayer.position,
                    recommendation: this.determineStartSit(analysis),
                    confidence: analysis.confidence,
                    reasoning: this.generateReasoning(analysis),
                    projectedPoints: analysis.projectedPoints,
                    upcomingGames: analysis.upcomingGames.length,
                    analysis
                };

                recommendations.push(recommendation);
            } catch (error) {
                logger.error(`Failed to analyze player ${teamPlayer.playerId}:`, error);
            }
        }

        // Sort by projected points (descending)
        return _.orderBy(recommendations, ['projectedPoints'], ['desc']);
    }

    /**
     * Analyze a player for a specific time period
     */
    async analyzePlayerForPeriod(playerId, daysAhead = 7) {
        const [playerInfo, stats, gameLog, upcomingGames] = await Promise.all([
            this.nhlApi.getPlayer(playerId),
            this.nhlApi.getPlayerStats(playerId, 30),
            this.nhlApi.getPlayerGameLog(playerId, 14),
            this.nhlApi.getPlayerUpcomingGames(playerId, daysAhead)
        ]);

        // Calculate recent performance trends
        const recentTrend = this.calculateRecentTrend(gameLog);
        
        // Analyze upcoming matchups
        const matchupAnalysis = await this.analyzeMatchups(upcomingGames, playerInfo);
        
        // Calculate projected performance
        const projectedPoints = this.projectPerformance(
            stats,
            recentTrend,
            matchupAnalysis,
            upcomingGames.length
        );

        // Calculate confidence score
        const confidence = this.calculateConfidence(stats, gameLog, upcomingGames);

        return {
            playerId,
            playerInfo,
            stats,
            gameLog,
            upcomingGames,
            recentTrend,
            matchupAnalysis,
            projectedPoints,
            confidence,
            analysis: {
                form: this.analyzeForm(gameLog),
                schedule: this.analyzeSchedule(upcomingGames),
                matchupQuality: matchupAnalysis.averageQuality
            }
        };
    }

    /**
     * Calculate recent performance trend
     */
    calculateRecentTrend(gameLog) {
        if (gameLog.length === 0) {
            return { trend: 'unknown', score: 0, games: 0 };
        }

        const last3 = gameLog.slice(0, 3);
        const last7 = gameLog.slice(0, 7);

        const avgLast3 = this.calculateAveragePoints(last3);
        const avgLast7 = this.calculateAveragePoints(last7);
        const avgAll = this.calculateAveragePoints(gameLog);

        let trend = 'stable';
        let score = avgLast3;

        if (avgLast3 > avgLast7 * 1.2) {
            trend = 'hot';
            score *= 1.2;
        } else if (avgLast3 < avgLast7 * 0.8) {
            trend = 'cold';
            score *= 0.8;
        }

        return {
            trend,
            score,
            last3Avg: avgLast3,
            last7Avg: avgLast7,
            seasonAvg: avgAll,
            games: gameLog.length
        };
    }

    /**
     * Calculate average fantasy points from game log
     */
    calculateAveragePoints(games) {
        if (games.length === 0) return 0;

        const totalPoints = games.reduce((sum, game) => {
            return sum + this.calculateFantasyPoints(game);
        }, 0);

        return totalPoints / games.length;
    }

    /**
     * Calculate fantasy points for a game
     */
    calculateFantasyPoints(game) {
        return (
            (game.goals || 0) * this.scoringWeights.goals +
            (game.assists || 0) * this.scoringWeights.assists +
            (game.shots || 0) * this.scoringWeights.shots +
            (game.hits || 0) * this.scoringWeights.hits +
            (game.blocked || 0) * this.scoringWeights.blocked +
            (game.plusMinus || 0) * this.scoringWeights.plusMinus
        );
    }

    /**
     * Analyze upcoming matchups
     */
    async analyzeMatchups(upcomingGames, playerInfo) {
        const matchupRatings = [];

        for (const game of upcomingGames) {
            const opponent = game.isHome ? game.awayTeam : game.homeTeam;
            const rating = await this.rateOpponent(opponent, playerInfo);
            
            matchupRatings.push({
                gameDate: game.date,
                opponent: opponent.name,
                isHome: game.isHome,
                rating,
                quality: this.categorizeMatchupQuality(rating)
            });
        }

        const averageRating = matchupRatings.length > 0
            ? _.meanBy(matchupRatings, 'rating')
            : 50;

        return {
            matchups: matchupRatings,
            averageQuality: averageRating,
            favorableCount: matchupRatings.filter(m => m.rating > 60).length,
            difficultCount: matchupRatings.filter(m => m.rating < 40).length
        };
    }

    /**
     * Rate an opponent for matchup analysis
     */
    async rateOpponent(opponent, playerInfo) {
        // This is a simplified rating system
        // In production, you'd want to analyze opponent's defensive stats,
        // goals against average, penalty kill %, etc.
        
        // For now, return a baseline rating with some variance
        return 50 + Math.random() * 20;
    }

    /**
     * Categorize matchup quality
     */
    categorizeMatchupQuality(rating) {
        if (rating >= 70) return 'excellent';
        if (rating >= 60) return 'good';
        if (rating >= 40) return 'average';
        if (rating >= 30) return 'difficult';
        return 'very-difficult';
    }

    /**
     * Project player performance
     */
    projectPerformance(stats, recentTrend, matchupAnalysis, gamesCount) {
        if (gamesCount === 0) return 0;

        // Base projection on season stats
        const seasonPointsPerGame = stats.games > 0 ? stats.points / stats.games : 0;
        const baseProjection = seasonPointsPerGame * gamesCount;

        // Adjust for recent trend
        const trendMultiplier = recentTrend.trend === 'hot' ? 1.15 : 
                               recentTrend.trend === 'cold' ? 0.85 : 1.0;

        // Adjust for matchup quality
        const matchupMultiplier = 0.8 + (matchupAnalysis.averageQuality / 100);

        return baseProjection * trendMultiplier * matchupMultiplier;
    }

    /**
     * Calculate confidence score
     */
    calculateConfidence(stats, gameLog, upcomingGames) {
        let confidence = 50;

        // More games played = higher confidence
        if (stats.games > 40) confidence += 20;
        else if (stats.games > 20) confidence += 10;
        else if (stats.games < 5) confidence -= 20;

        // Recent game log data increases confidence
        if (gameLog.length >= 10) confidence += 15;
        else if (gameLog.length < 3) confidence -= 15;

        // Having upcoming games increases confidence
        if (upcomingGames.length >= 3) confidence += 15;
        else if (upcomingGames.length === 0) confidence -= 30;

        return Math.max(0, Math.min(100, confidence));
    }

    /**
     * Determine start or sit recommendation
     */
    determineStartSit(analysis) {
        const { projectedPoints, confidence, upcomingGames } = analysis;

        if (upcomingGames.length === 0) {
            return 'sit';
        }

        if (projectedPoints > 3 && confidence > 60) {
            return 'start';
        } else if (projectedPoints < 1.5 || confidence < 40) {
            return 'sit';
        } else {
            return 'consider';
        }
    }

    /**
     * Generate reasoning for recommendation
     */
    generateReasoning(analysis) {
        const reasons = [];

        // Trend-based reasoning
        if (analysis.recentTrend.trend === 'hot') {
            reasons.push(`Player is on a hot streak (${analysis.recentTrend.last3Avg.toFixed(1)} pts/game in last 3)`);
        } else if (analysis.recentTrend.trend === 'cold') {
            reasons.push(`Player is in a cold stretch (${analysis.recentTrend.last3Avg.toFixed(1)} pts/game in last 3)`);
        }

        // Schedule-based reasoning
        if (analysis.upcomingGames.length >= 4) {
            reasons.push(`${analysis.upcomingGames.length} games in next week`);
        } else if (analysis.upcomingGames.length === 0) {
            reasons.push('No games scheduled');
        }

        // Matchup-based reasoning
        if (analysis.matchupAnalysis.favorableCount > 0) {
            reasons.push(`${analysis.matchupAnalysis.favorableCount} favorable matchup(s)`);
        } else if (analysis.matchupAnalysis.difficultCount > 2) {
            reasons.push(`${analysis.matchupAnalysis.difficultCount} difficult matchup(s)`);
        }

        return reasons.join('; ');
    }

    /**
     * Analyze player form
     */
    analyzeForm(gameLog) {
        const recent = gameLog.slice(0, 5);
        const points = recent.map(g => (g.goals || 0) + (g.assists || 0));
        const avgPoints = points.length > 0 ? _.mean(points) : 0;

        return {
            recent: avgPoints,
            consistency: points.length > 0 ? 1 - (_.stdDeviation(points) / (avgPoints + 1)) : 0,
            gamesAnalyzed: recent.length
        };
    }

    /**
     * Analyze schedule difficulty
     */
    analyzeSchedule(upcomingGames) {
        return {
            gamesCount: upcomingGames.length,
            homeGames: upcomingGames.filter(g => g.isHome).length,
            awayGames: upcomingGames.filter(g => !g.isHome).length,
            backToBack: this.identifyBackToBack(upcomingGames)
        };
    }

    /**
     * Identify back-to-back games
     */
    identifyBackToBack(games) {
        let backToBackCount = 0;
        for (let i = 1; i < games.length; i++) {
            const prevDate = moment(games[i - 1].date);
            const currDate = moment(games[i].date);
            if (currDate.diff(prevDate, 'days') === 1) {
                backToBackCount++;
            }
        }
        return backToBackCount;
    }

    /**
     * Find potential waiver wire targets
     */
    async findWaiverTargets(userTeam, limit = 10) {
        // This would typically query available players not on any user's team
        // For now, return empty array as placeholder
        return [];
    }

    /**
     * Optimize lineup based on upcoming schedule
     */
    async optimizeLineup(userTeam, daysAhead = 7) {
        if (userTeam.players.length === 0) {
            return null;
        }

        const playerAnalyses = [];
        
        for (const player of userTeam.players) {
            const analysis = await this.analyzePlayerForPeriod(player.playerId, daysAhead);
            playerAnalyses.push({
                playerId: player.playerId,
                position: player.position,
                projectedPoints: analysis.projectedPoints,
                analysis
            });
        }

        // Sort by projected points
        const sorted = _.orderBy(playerAnalyses, ['projectedPoints'], ['desc']);

        return {
            suggestedStarters: sorted.slice(0, Math.min(9, sorted.length)),
            suggestedBench: sorted.slice(9),
            totalProjectedPoints: _.sumBy(sorted.slice(0, 9), 'projectedPoints')
        };
    }

    /**
     * Generate player alerts
     */
    async generatePlayerAlerts(userTeam) {
        const alerts = [];

        for (const player of userTeam.players) {
            try {
                const gameLog = await this.nhlApi.getPlayerGameLog(player.playerId, 5);
                const upcomingGames = await this.nhlApi.getPlayerUpcomingGames(player.playerId, 7);

                // Check for cold streak
                const recentPoints = gameLog.slice(0, 5).reduce((sum, g) => 
                    sum + (g.goals || 0) + (g.assists || 0), 0
                );
                
                if (recentPoints === 0 && gameLog.length >= 3) {
                    alerts.push({
                        playerId: player.playerId,
                        playerName: player.playerInfo?.fullName,
                        type: 'cold-streak',
                        severity: 'warning',
                        message: `${player.playerInfo?.fullName} has no points in last ${gameLog.length} games`
                    });
                }

                // Check for no upcoming games
                if (upcomingGames.length === 0) {
                    alerts.push({
                        playerId: player.playerId,
                        playerName: player.playerInfo?.fullName,
                        type: 'no-games',
                        severity: 'info',
                        message: `${player.playerInfo?.fullName} has no games in the next 7 days`
                    });
                }

                // Check for heavy schedule (4+ games)
                if (upcomingGames.length >= 4) {
                    alerts.push({
                        playerId: player.playerId,
                        playerName: player.playerInfo?.fullName,
                        type: 'heavy-schedule',
                        severity: 'info',
                        message: `${player.playerInfo?.fullName} has ${upcomingGames.length} games this week`
                    });
                }
            } catch (error) {
                logger.error(`Failed to generate alerts for player ${player.playerId}:`, error);
            }
        }

        return alerts;
    }

    /**
     * Analyze a single player
     */
    async analyzePlayer(playerInfo, stats, upcomingGames) {
        const gameLog = await this.nhlApi.getPlayerGameLog(playerInfo.playerId, 14);
        
        return {
            playerInfo,
            stats,
            upcomingGames,
            recentTrend: this.calculateRecentTrend(gameLog),
            form: this.analyzeForm(gameLog),
            schedule: this.analyzeSchedule(upcomingGames),
            projectedPoints: this.projectPerformance(
                stats,
                this.calculateRecentTrend(gameLog),
                await this.analyzeMatchups(upcomingGames, playerInfo),
                upcomingGames.length
            )
        };
    }
}