import { EventEmitter } from 'events';
import { logger } from '../utils/logger.js';

/**
 * Base Agent class for persistent fantasy hockey agents
 * Provides core functionality for state management, memory, and communication
 */
export class BaseAgent extends EventEmitter {
    constructor(services, agentId, config = {}) {
        super();
        this.agentId = agentId;
        this.services = services;
        this.config = {
            memorySize: 1000,
            persistenceInterval: 30000, // 30 seconds
            autoSave: true,
            ...config
        };
        
        this.state = new Map();
        this.memory = [];
        this.isInitialized = false;
        this.lastPersistence = Date.now();
        
        // Set up auto-persistence
        if (this.config.autoSave) {
            this.setupAutoPersistence();
        }
    }

    async initialize() {
        try {
            await this.loadState();
            await this.loadMemory();
            this.isInitialized = true;
            this.emit('initialized');
            logger.info(`Agent ${this.agentId} initialized successfully`);
        } catch (error) {
            logger.error(`Failed to initialize agent ${this.agentId}:`, error);
            throw error;
        }
    }

    async loadState() {
        try {
            const savedState = await this.services.database.getAgentState(this.agentId);
            if (savedState) {
                this.state = new Map(Object.entries(savedState.data || {}));
                logger.debug(`Loaded state for agent ${this.agentId}`);
            }
        } catch (error) {
            logger.error(`Failed to load state for agent ${this.agentId}:`, error);
        }
    }

    async loadMemory() {
        try {
            const savedMemory = await this.services.database.getAgentMemory(this.agentId, this.config.memorySize);
            if (savedMemory && savedMemory.length > 0) {
                this.memory = savedMemory;
                logger.debug(`Loaded ${savedMemory.length} memory entries for agent ${this.agentId}`);
            }
        } catch (error) {
            logger.error(`Failed to load memory for agent ${this.agentId}:`, error);
        }
    }

    async saveState() {
        try {
            const stateData = Object.fromEntries(this.state);
            await this.services.database.saveAgentState(this.agentId, stateData);
            this.lastPersistence = Date.now();
            logger.debug(`Saved state for agent ${this.agentId}`);
        } catch (error) {
            logger.error(`Failed to save state for agent ${this.agentId}:`, error);
        }
    }

    async addMemory(type, data, metadata = {}) {
        const memoryEntry = {
            id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
            timestamp: new Date().toISOString(),
            type,
            data,
            metadata,
            agentId: this.agentId
        };

        this.memory.unshift(memoryEntry);
        
        // Limit memory size
        if (this.memory.length > this.config.memorySize) {
            this.memory = this.memory.slice(0, this.config.memorySize);
        }

        // Persist to database
        try {
            await this.services.database.addAgentMemory(memoryEntry);
        } catch (error) {
            logger.error(`Failed to persist memory for agent ${this.agentId}:`, error);
        }

        this.emit('memoryAdded', memoryEntry);
        return memoryEntry;
    }

    getMemory(type = null, limit = null) {
        let filteredMemory = this.memory;
        
        if (type) {
            filteredMemory = this.memory.filter(entry => entry.type === type);
        }
        
        if (limit) {
            filteredMemory = filteredMemory.slice(0, limit);
        }
        
        return filteredMemory;
    }

    setState(key, value) {
        const oldValue = this.state.get(key);
        this.state.set(key, value);
        
        this.emit('stateChanged', { key, oldValue, newValue: value });
        
        if (this.config.autoSave) {
            this.scheduleStateSave();
        }
    }

    getState(key, defaultValue = null) {
        return this.state.get(key) || defaultValue;
    }

    getAllState() {
        return Object.fromEntries(this.state);
    }

    clearMemory(type = null) {
        if (type) {
            this.memory = this.memory.filter(entry => entry.type !== type);
        } else {
            this.memory = [];
        }
        
        this.emit('memoryCleared', { type });
    }

    setupAutoPersistence() {
        this.persistenceTimer = setInterval(async () => {
            if (Date.now() - this.lastPersistence >= this.config.persistenceInterval) {
                await this.saveState();
            }
        }, this.config.persistenceInterval);
    }

    scheduleStateSave() {
        if (this.saveStateTimeout) {
            clearTimeout(this.saveStateTimeout);
        }
        
        this.saveStateTimeout = setTimeout(async () => {
            await this.saveState();
        }, 1000); // Debounce saves to 1 second
    }

    async shutdown() {
        if (this.persistenceTimer) {
            clearInterval(this.persistenceTimer);
        }
        
        if (this.saveStateTimeout) {
            clearTimeout(this.saveStateTimeout);
        }
        
        await this.saveState();
        this.emit('shutdown');
        logger.info(`Agent ${this.agentId} shut down successfully`);
    }

    // Abstract methods to be implemented by specific agents
    async processInput(input) {
        throw new Error('processInput method must be implemented by subclass');
    }

    async generateRecommendations() {
        throw new Error('generateRecommendations method must be implemented by subclass');
    }
}