import sqlite3 from 'sqlite3';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs';
import { logger } from '../utils/logger.js';

/**
 * Database Manager - Handles all database operations for the Fantasy Hockey Assistant
 */
export class DatabaseManager {
    constructor() {
        const dbPath = process.env.DATABASE_PATH || './data/fantasy_hockey.db';
        this.dbPath = path.resolve(dbPath);
        this.db = null;
    }

    async initialize() {
        try {
            // Ensure data directory exists
            const dataDir = path.dirname(this.dbPath);
            if (!fs.existsSync(dataDir)) {
                fs.mkdirSync(dataDir, { recursive: true });
            }

            // Open database connection
            this.db = new sqlite3.Database(this.dbPath, (err) => {
                if (err) {
                    logger.error('Failed to open database:', err);
                    throw err;
                }
            });

            // Promisify database methods
            this.run = promisify(this.db.run.bind(this.db));
            this.get = promisify(this.db.get.bind(this.db));
            this.all = promisify(this.db.all.bind(this.db));

            // Create tables
            await this.createTables();

            logger.info(`Database initialized at ${this.dbPath}`);
        } catch (error) {
            logger.error('Failed to initialize database:', error);
            throw error;
        }
    }

    async createTables() {
        const tables = [
            // Agent state table
            `CREATE TABLE IF NOT EXISTS agent_state (
                agent_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )`,
            
            // Agent memory table
            `CREATE TABLE IF NOT EXISTS agent_memory (
                id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                type TEXT NOT NULL,
                data TEXT NOT NULL,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )`,
            
            // User teams table
            `CREATE TABLE IF NOT EXISTS user_teams (
                user_id TEXT PRIMARY KEY,
                players TEXT NOT NULL,
                lineup TEXT,
                preferences TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )`,
            
            // Players table
            `CREATE TABLE IF NOT EXISTS players (
                player_id INTEGER PRIMARY KEY,
                full_name TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                position TEXT,
                team_id INTEGER,
                data TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )`,
            
            // Player stats table
            `CREATE TABLE IF NOT EXISTS player_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
                season TEXT NOT NULL,
                games INTEGER DEFAULT 0,
                goals INTEGER DEFAULT 0,
                assists INTEGER DEFAULT 0,
                points INTEGER DEFAULT 0,
                data TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(player_id, season)
            )`,
            
            // Recommendations table
            `CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                recommendations TEXT NOT NULL,
                generated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )`
        ];

        for (const table of tables) {
            await this.run(table);
        }

        // Create indices
        await this.run('CREATE INDEX IF NOT EXISTS idx_agent_memory_agent_id ON agent_memory(agent_id)');
        await this.run('CREATE INDEX IF NOT EXISTS idx_agent_memory_type ON agent_memory(type)');
        await this.run('CREATE INDEX IF NOT EXISTS idx_player_stats_player_id ON player_stats(player_id)');
        await this.run('CREATE INDEX IF NOT EXISTS idx_recommendations_user_id ON recommendations(user_id)');

        logger.debug('Database tables created successfully');
    }

    // Agent state methods
    async getAgentState(agentId) {
        const row = await this.get('SELECT * FROM agent_state WHERE agent_id = ?', [agentId]);
        if (row) {
            return {
                agentId: row.agent_id,
                data: JSON.parse(row.data),
                updatedAt: row.updated_at
            };
        }
        return null;
    }

    async saveAgentState(agentId, data) {
        await this.run(
            `INSERT OR REPLACE INTO agent_state (agent_id, data, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)`,
            [agentId, JSON.stringify(data)]
        );
    }

    // Agent memory methods
    async getAgentMemory(agentId, limit = 100) {
        const rows = await this.all(
            'SELECT * FROM agent_memory WHERE agent_id = ? ORDER BY timestamp DESC LIMIT ?',
            [agentId, limit]
        );
        
        return rows.map(row => ({
            id: row.id,
            agentId: row.agent_id,
            timestamp: row.timestamp,
            type: row.type,
            data: JSON.parse(row.data),
            metadata: row.metadata ? JSON.parse(row.metadata) : {}
        }));
    }

    async addAgentMemory(memoryEntry) {
        await this.run(
            `INSERT INTO agent_memory (id, agent_id, timestamp, type, data, metadata) VALUES (?, ?, ?, ?, ?, ?)`,
            [
                memoryEntry.id,
                memoryEntry.agentId,
                memoryEntry.timestamp,
                memoryEntry.type,
                JSON.stringify(memoryEntry.data),
                JSON.stringify(memoryEntry.metadata || {})
            ]
        );
    }

    // User team methods
    async getAllUserTeams() {
        const rows = await this.all('SELECT * FROM user_teams');
        return rows.map(row => ({
            userId: row.user_id,
            players: JSON.parse(row.players),
            lineup: JSON.parse(row.lineup || '{}'),
            preferences: JSON.parse(row.preferences || '{}'),
            createdAt: row.created_at,
            updatedAt: row.updated_at
        }));
    }

    async getUserTeam(userId) {
        const row = await this.get('SELECT * FROM user_teams WHERE user_id = ?', [userId]);
        if (row) {
            return {
                userId: row.user_id,
                players: JSON.parse(row.players),
                lineup: JSON.parse(row.lineup || '{}'),
                preferences: JSON.parse(row.preferences || '{}'),
                createdAt: row.created_at,
                updatedAt: row.updated_at
            };
        }
        return null;
    }

    async saveUserTeam(userTeam) {
        await this.run(
            `INSERT OR REPLACE INTO user_teams (user_id, players, lineup, preferences, updated_at) 
             VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)`,
            [
                userTeam.userId,
                JSON.stringify(userTeam.players),
                JSON.stringify(userTeam.lineup || {}),
                JSON.stringify(userTeam.preferences || {})
            ]
        );
    }

    // Player methods
    async getAllPlayers() {
        const rows = await this.all('SELECT * FROM players');
        return rows.map(row => JSON.parse(row.data));
    }

    async getPlayer(playerId) {
        const row = await this.get('SELECT * FROM players WHERE player_id = ?', [playerId]);
        if (row) {
            return JSON.parse(row.data);
        }
        return null;
    }

    async savePlayer(player) {
        await this.run(
            `INSERT OR REPLACE INTO players (player_id, full_name, first_name, last_name, position, team_id, data, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)`,
            [
                player.playerId,
                player.fullName,
                player.firstName,
                player.lastName,
                player.primaryPosition?.abbreviation || player.primaryPosition?.name,
                player.currentTeam?.id,
                JSON.stringify(player)
            ]
        );
    }

    // Player stats methods
    async updatePlayerStats(playerId, stats) {
        await this.run(
            `INSERT OR REPLACE INTO player_stats (player_id, season, games, goals, assists, points, data, updated_at)
             VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)`,
            [
                playerId,
                stats.season,
                stats.games,
                stats.goals,
                stats.assists,
                stats.points,
                JSON.stringify(stats)
            ]
        );
    }

    async getPlayerStats(playerId, season) {
        const row = await this.get(
            'SELECT * FROM player_stats WHERE player_id = ? AND season = ?',
            [playerId, season]
        );
        
        if (row) {
            return JSON.parse(row.data);
        }
        return null;
    }

    // Recommendations methods
    async saveUserRecommendations(userId, recommendations) {
        await this.run(
            'INSERT INTO recommendations (user_id, recommendations) VALUES (?, ?)',
            [userId, JSON.stringify(recommendations)]
        );
    }

    async getUserRecommendations(userId, limit = 10) {
        const rows = await this.all(
            'SELECT * FROM recommendations WHERE user_id = ? ORDER BY generated_at DESC LIMIT ?',
            [userId, limit]
        );
        
        return rows.map(row => ({
            id: row.id,
            userId: row.user_id,
            recommendations: JSON.parse(row.recommendations),
            generatedAt: row.generated_at
        }));
    }

    async close() {
        if (this.db) {
            await new Promise((resolve, reject) => {
                this.db.close((err) => {
                    if (err) {
                        logger.error('Error closing database:', err);
                        reject(err);
                    } else {
                        logger.info('Database connection closed');
                        resolve();
                    }
                });
            });
        }
    }
}