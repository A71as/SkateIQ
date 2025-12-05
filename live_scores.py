"""
Live NHL Game Score Service
Fetches real-time game scores and status updates
Handles prediction locking when games start
"""
import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from database import get_db, Prediction
from sqlalchemy.orm import Session
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LiveScoreService:
    """Service for fetching live NHL game scores and managing prediction locks"""
    
    def __init__(self):
        self.base_url = "https://api-web.nhle.com/v1"
        self.game_states = {
            "FUT": "Future",      # Game not started
            "PRE": "Pre-game",    # Pre-game activities
            "LIVE": "Live",       # Game in progress
            "CRIT": "Critical",   # Critical moments (overtime, shootout)
            "OFF": "Official",    # Game finished
            "FINAL": "Final"      # Game final
        }
    
    async def get_live_scores(self, date: str) -> List[Dict]:
        """Fetch live scores for games on a specific date"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/score/{date}"
                
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        logger.error(f"API request failed with status {response.status}")
                        return []
                    
                    data = await response.json()
                    games = data.get("games", [])
                    
                    live_games = []
                    for game in games:
                        home_team = game.get("homeTeam", {})
                        away_team = game.get("awayTeam", {})
                        
                        game_info = {
                            "game_id": str(game.get("id", "")),
                            "home_team": home_team.get("name", {}).get("default", ""),
                            "away_team": away_team.get("name", {}).get("default", ""),
                            "home_score": home_team.get("score", 0),
                            "away_score": away_team.get("score", 0),
                            "game_state": game.get("gameState", "FUT"),
                            "game_state_display": self.game_states.get(game.get("gameState", "FUT"), "Unknown"),
                            "period": game.get("period", 0),
                            "time_remaining": game.get("clock", {}).get("timeRemaining", ""),
                            "start_time": game.get("startTimeUTC", ""),
                            "venue": game.get("venue", {}).get("default", ""),
                            "is_live": game.get("gameState") in ["LIVE", "CRIT"],
                            "is_finished": game.get("gameState") in ["OFF", "FINAL"],
                            "is_started": game.get("gameState") not in ["FUT", "PRE"]
                        }
                        
                        # Add period information for live games
                        if game_info["is_live"]:
                            period_info = self._format_period_info(game_info["period"], game_info["time_remaining"])
                            game_info["period_display"] = period_info
                        
                        live_games.append(game_info)
                    
                    logger.info(f"Fetched {len(live_games)} games for {date}")
                    return live_games
                    
        except Exception as e:
            logger.error(f"Error fetching live scores for {date}: {e}")
            return []
    
    def _format_period_info(self, period: int, time_remaining: str) -> str:
        """Format period and time information for display"""
        if period == 0:
            return "Pre-game"
        elif period <= 3:
            if time_remaining:
                return f"Period {period} - {time_remaining}"
            else:
                return f"Period {period}"
        elif period == 4:
            if time_remaining:
                return f"OT - {time_remaining}"
            else:
                return "Overtime"
        elif period == 5:
            return "Shootout"
        else:
            return f"Period {period}"
    
    async def check_prediction_locks(self) -> List[Dict]:
        """
        Check and update prediction lock status for all active games
        Returns list of games with lock status
        """
        try:
            # Get live scores first
            today = datetime.now().strftime('%Y-%m-%d')
            live_games = await self.get_live_scores(today)
            
            # Create database session
            from database import SessionLocal
            db = SessionLocal()
            lock_info = []
            
            try:
                for game in live_games:
                    game_date = game.get("date", datetime.now().strftime('%Y-%m-%d'))
                    
                    # Find predictions for this game
                    predictions = db.query(Prediction).filter(
                        Prediction.home_team == game["home_team"],
                        Prediction.away_team == game["away_team"],
                        Prediction.game_date == game_date
                    ).all()
                    
                    is_locked = game["is_started"]  # Lock if game has started
                    
                    # Update prediction lock status in database
                    for pred in predictions:
                        if is_locked and not pred.is_locked:
                            pred.is_locked = True
                            pred.game_status = game["game_state"]
                            logger.info(f"Locked prediction: {pred.away_team} @ {pred.home_team}")
                        
                        # Update live scores
                        if game["is_live"] or game["is_finished"]:
                            pred.live_home_score = game["home_score"]
                            pred.live_away_score = game["away_score"]
                            pred.game_status = game["game_state"]
                    
                    # Add game info to response
                    lock_info.append({
                        "game_id": game["game_id"],
                        "home_team": game["home_team"],
                        "away_team": game["away_team"],
                        "date": game_date,
                        "is_locked": is_locked,
                        "game_status": game["game_state"],
                        "home_score": game["home_score"],
                        "away_score": game["away_score"],
                        "predictions_count": len(predictions)
                    })
                
                db.commit()
                return lock_info
                
            except Exception as e:
                db.rollback()
                logger.error(f"Error checking prediction locks: {e}")
                raise
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error in check_prediction_locks: {e}")
            return []
    
    async def get_game_summary(self, game_id: str) -> Optional[Dict]:
        """Get detailed game summary including scoring plays, penalties, etc."""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/game/{game_id}/summary"
                
                async with session.get(url, timeout=10) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    
                    # Extract key information
                    summary = {
                        "game_id": game_id,
                        "home_team": data.get("homeTeam", {}).get("name", {}).get("default", ""),
                        "away_team": data.get("awayTeam", {}).get("name", {}).get("default", ""),
                        "home_score": data.get("homeTeam", {}).get("score", 0),
                        "away_score": data.get("awayTeam", {}).get("score", 0),
                        "period": data.get("period", 0),
                        "game_state": data.get("gameState", ""),
                        "scoring_plays": [],
                        "penalties": [],
                        "shots": {
                            "home": data.get("homeTeam", {}).get("sog", 0),
                            "away": data.get("awayTeam", {}).get("sog", 0)
                        }
                    }
                    
                    # Extract scoring plays
                    for play in data.get("scoring", []):
                        summary["scoring_plays"].append({
                            "period": play.get("period", 0),
                            "time": play.get("time", ""),
                            "team": play.get("team", {}).get("abbrev", ""),
                            "scorer": play.get("scorer", {}).get("player", {}).get("name", {}).get("default", ""),
                            "assists": [
                                assist.get("player", {}).get("name", {}).get("default", "")
                                for assist in play.get("assists", [])
                            ],
                            "strength": play.get("strength", ""),
                            "game_winner": play.get("gameWinner", False)
                        })
                    
                    return summary
                    
        except Exception as e:
            logger.error(f"Error fetching game summary for {game_id}: {e}")
            return None


# Background task for live score updates
class LiveScoreUpdater:
    """Background service that continuously updates live scores"""
    
    def __init__(self, live_service: LiveScoreService, connection_manager=None, update_interval: int = 30):
        self.update_interval = update_interval  # seconds
        self.live_service = live_service
        self.connection_manager = connection_manager
        self.is_running = False
    
    async def start_monitoring(self):
        """Start the live score monitoring loop"""
        self.is_running = True
        logger.info(f"Starting live score monitoring (interval: {self.update_interval}s)")
        
        while self.is_running:
            try:
                # Get today's date
                today = datetime.now().strftime('%Y-%m-%d')
                
                # Fetch live scores
                games = await self.live_service.get_live_scores(today)
                
                if games:
                    # Check for prediction locks and live updates
                    lock_info = await self.live_service.check_prediction_locks()
                    
                    if lock_info:
                        locked_count = sum(1 for g in lock_info if g["is_locked"])
                        if locked_count > 0:
                            logger.info(f"Live update: {locked_count} games with locked predictions")
                        
                        # Broadcast updates to WebSocket clients
                        if self.connection_manager:
                            await self.connection_manager.broadcast({
                                "type": "live_scores_update",
                                "data": games,
                                "lock_info": lock_info,
                                "timestamp": datetime.now().isoformat()
                            })
                    
                    # Log live games
                    live_games = [g for g in games if g["is_live"]]
                    if live_games:
                        logger.info(f"Live games: {len(live_games)}")
                        for game in live_games[:3]:  # Log first 3
                            logger.info(f"  {game['away_team']} {game['away_score']} - {game['home_score']} {game['home_team']} ({game['period_display']})")
                
                # Wait before next update
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in live score monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def stop_monitoring(self):
        """Stop the live score monitoring"""
        self.is_running = False
        logger.info("Stopping live score monitoring")


# Helper functions for easy access
async def start_live_score_service(live_service, connection_manager=None, update_interval=30):
    """Start the live score monitoring service"""
    updater = LiveScoreUpdater(live_service, connection_manager, update_interval)
    await updater.start_monitoring()
    return updater