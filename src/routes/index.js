import express from 'express';
import { logger } from '../utils/logger.js';

/**
 * Setup all API routes
 */
export function setupRoutes(app, services) {
    const router = express.Router();

    // Health check
    router.get('/health', (req, res) => {
        res.json({ status: 'ok', timestamp: new Date().toISOString() });
    });

    // Agent status
    router.get('/agent/status', (req, res) => {
        try {
            const agent = req.app.locals.agent;
            if (!agent) {
                return res.status(503).json({ error: 'Agent not initialized' });
            }
            
            res.json(agent.getStatus());
        } catch (error) {
            logger.error('Error getting agent status:', error);
            res.status(500).json({ error: 'Failed to get agent status' });
        }
    });

    // Get user team
    router.get('/team/:userId', async (req, res) => {
        try {
            const { userId } = req.params;
            const team = await services.database.getUserTeam(userId);
            
            if (!team) {
                return res.status(404).json({ error: 'Team not found' });
            }
            
            res.json(team);
        } catch (error) {
            logger.error('Error getting user team:', error);
            res.status(500).json({ error: 'Failed to get team' });
        }
    });

    // Add player to team
    router.post('/team/:userId/players', async (req, res) => {
        try {
            const { userId } = req.params;
            const { playerId, position } = req.body;
            
            if (!playerId || !position) {
                return res.status(400).json({ error: 'playerId and position are required' });
            }

            const agent = req.app.locals.agent;
            const result = await agent.processInput({
                type: 'addPlayer',
                userId,
                data: { playerId, position }
            });

            res.json(result);
        } catch (error) {
            logger.error('Error adding player:', error);
            res.status(500).json({ error: error.message });
        }
    });

    // Remove player from team
    router.delete('/team/:userId/players/:playerId', async (req, res) => {
        try {
            const { userId, playerId } = req.params;

            const agent = req.app.locals.agent;
            const result = await agent.processInput({
                type: 'removePlayer',
                userId,
                data: { playerId: parseInt(playerId) }
            });

            res.json(result);
        } catch (error) {
            logger.error('Error removing player:', error);
            res.status(500).json({ error: error.message });
        }
    });

    // Set lineup
    router.put('/team/:userId/lineup', async (req, res) => {
        try {
            const { userId } = req.params;
            const { lineup } = req.body;

            if (!lineup) {
                return res.status(400).json({ error: 'lineup is required' });
            }

            const agent = req.app.locals.agent;
            const result = await agent.processInput({
                type: 'setLineup',
                userId,
                data: { lineup }
            });

            res.json(result);
        } catch (error) {
            logger.error('Error setting lineup:', error);
            res.status(500).json({ error: error.message });
        }
    });

    // Get recommendations
    router.get('/recommendations/:userId', async (req, res) => {
        try {
            const { userId } = req.params;
            const options = {
                includeStartSit: req.query.includeStartSit !== 'false',
                includeWaiverTargets: req.query.includeWaiverTargets !== 'false',
                daysAhead: parseInt(req.query.daysAhead) || 7
            };

            const agent = req.app.locals.agent;
            const recommendations = await agent.processInput({
                type: 'getRecommendations',
                userId,
                data: { options }
            });

            res.json(recommendations);
        } catch (error) {
            logger.error('Error getting recommendations:', error);
            res.status(500).json({ error: error.message });
        }
    });

    // Get player info
    router.get('/players/:playerId', async (req, res) => {
        try {
            const { playerId } = req.params;
            const player = await services.nhlApi.getPlayer(playerId);
            res.json(player);
        } catch (error) {
            logger.error('Error getting player:', error);
            res.status(500).json({ error: 'Failed to get player' });
        }
    });

    // Get player stats
    router.get('/players/:playerId/stats', async (req, res) => {
        try {
            const { playerId } = req.params;
            const days = parseInt(req.query.days) || 30;
            const stats = await services.nhlApi.getPlayerStats(playerId, days);
            res.json(stats);
        } catch (error) {
            logger.error('Error getting player stats:', error);
            res.status(500).json({ error: 'Failed to get player stats' });
        }
    });

    // Get player analysis
    router.get('/players/:playerId/analysis', async (req, res) => {
        try {
            const { playerId } = req.params;
            const days = parseInt(req.query.days) || 30;

            const agent = req.app.locals.agent;
            const analysis = await agent.processInput({
                type: 'getPlayerAnalysis',
                userId: 'system',
                data: { playerId: parseInt(playerId), days }
            });

            res.json(analysis);
        } catch (error) {
            logger.error('Error getting player analysis:', error);
            res.status(500).json({ error: error.message });
        }
    });

    // Search players
    router.get('/players/search/:searchTerm', async (req, res) => {
        try {
            const { searchTerm } = req.params;
            const players = await services.nhlApi.searchPlayers(searchTerm);
            res.json(players);
        } catch (error) {
            logger.error('Error searching players:', error);
            res.status(500).json({ error: 'Failed to search players' });
        }
    });

    // Get schedule
    router.get('/schedule', async (req, res) => {
        try {
            const teamId = req.query.teamId;
            const days = parseInt(req.query.days) || 7;
            
            if (!teamId) {
                return res.status(400).json({ error: 'teamId is required' });
            }

            const schedule = await services.nhlApi.getTeamUpcomingGames(teamId, days);
            res.json(schedule);
        } catch (error) {
            logger.error('Error getting schedule:', error);
            res.status(500).json({ error: 'Failed to get schedule' });
        }
    });

    // Get all teams
    router.get('/teams', async (req, res) => {
        try {
            const teams = await services.nhlApi.getAllTeams();
            res.json(teams);
        } catch (error) {
            logger.error('Error getting teams:', error);
            res.status(500).json({ error: 'Failed to get teams' });
        }
    });

    // Update user preferences
    router.put('/team/:userId/preferences', async (req, res) => {
        try {
            const { userId } = req.params;
            const { preferences } = req.body;

            if (!preferences) {
                return res.status(400).json({ error: 'preferences are required' });
            }

            const agent = req.app.locals.agent;
            const result = await agent.processInput({
                type: 'updatePreferences',
                userId,
                data: { preferences }
            });

            res.json(result);
        } catch (error) {
            logger.error('Error updating preferences:', error);
            res.status(500).json({ error: error.message });
        }
    });

    // Mount router
    app.use('/api', router);

    // Serve web interface
    app.get('/', (req, res) => {
        res.send(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>NHL Fantasy Hockey Assistant</title>
                <style>
                    body { 
                        font-family: Arial, sans-serif; 
                        max-width: 1200px; 
                        margin: 50px auto; 
                        padding: 20px;
                        background: #f5f5f5;
                    }
                    .container {
                        background: white;
                        padding: 40px;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }
                    h1 { color: #003087; }
                    .api-link { 
                        background: #003087; 
                        color: white; 
                        padding: 10px 20px; 
                        text-decoration: none; 
                        border-radius: 5px;
                        display: inline-block;
                        margin: 10px 5px;
                    }
                    .section { margin: 30px 0; }
                    code { 
                        background: #f4f4f4; 
                        padding: 2px 6px; 
                        border-radius: 3px; 
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🏒 NHL Fantasy Hockey Assistant</h1>
                    <p>Welcome to your intelligent fantasy hockey companion!</p>
                    
                    <div class="section">
                        <h2>API Endpoints</h2>
                        <a href="/api/health" class="api-link">Health Check</a>
                        <a href="/api/agent/status" class="api-link">Agent Status</a>
                        <a href="/api/teams" class="api-link">NHL Teams</a>
                    </div>
                    
                    <div class="section">
                        <h2>Getting Started</h2>
                        <ol>
                            <li>Create your team: <code>POST /api/team/:userId/players</code></li>
                            <li>Set your lineup: <code>PUT /api/team/:userId/lineup</code></li>
                            <li>Get recommendations: <code>GET /api/recommendations/:userId</code></li>
                        </ol>
                    </div>
                    
                    <div class="section">
                        <h2>Features</h2>
                        <ul>
                            <li>✅ Persistent team memory</li>
                            <li>✅ Daily roster recommendations</li>
                            <li>✅ Player performance analysis</li>
                            <li>✅ Matchup analysis</li>
                            <li>✅ Real-time NHL data</li>
                        </ul>
                    </div>
                </div>
            </body>
            </html>
        `);
    });

    logger.info('Routes configured successfully');
}

export default setupRoutes;