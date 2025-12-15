from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import uvicorn
import os
from datetime import datetime, timedelta
import requests
from openai import OpenAI
from dotenv import load_dotenv
import hashlib
import json
from pathlib import Path
import asyncio
import logging

# Live scores import
from live_scores import LiveScoreService, LiveScoreUpdater

# MoneyPuck data service
from moneypuck_service import MoneyPuckService

# Game result scraper
from game_result_scraper import run_scheduler
import threading

# Database and auth imports
from database import get_db, Prediction, AccuracyStats, User, update_accuracy_stats, SessionLocal
from auth import (
    get_current_user, 
    require_current_user, 
    authenticate_user, 
    create_access_token, 
    create_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

# Load environment variables
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NHL_API_BASE = "https://api-web.nhle.com/v1"  # For schedules and live scores
MONEYPUCK_BASE = "https://moneypuck.com"  # For team stats and analytics

# Team name normalization - map short names to full names
TEAM_NAME_MAP = {
    # Short name -> Full name
    "Ducks": "Anaheim Ducks",
    "Bruins": "Boston Bruins",
    "Sabres": "Buffalo Sabres",
    "Flames": "Calgary Flames",
    "Hurricanes": "Carolina Hurricanes",
    "Blackhawks": "Chicago Blackhawks",
    "Avalanche": "Colorado Avalanche",
    "Blue Jackets": "Columbus Blue Jackets",
    "Stars": "Dallas Stars",
    "Red Wings": "Detroit Red Wings",
    "Oilers": "Edmonton Oilers",
    "Panthers": "Florida Panthers",
    "Kings": "Los Angeles Kings",
    "Wild": "Minnesota Wild",
    "Canadiens": "Montreal Canadiens",
    "Montréal Canadiens": "Montreal Canadiens",
    "Predators": "Nashville Predators",
    "Devils": "New Jersey Devils",
    "Islanders": "New York Islanders",
    "Rangers": "New York Rangers",
    "Senators": "Ottawa Senators",
    "Flyers": "Philadelphia Flyers",
    "Penguins": "Pittsburgh Penguins",
    "Sharks": "San Jose Sharks",
    "Kraken": "Seattle Kraken",
    "Blues": "St. Louis Blues",
    "Lightning": "Tampa Bay Lightning",
    "Maple Leafs": "Toronto Maple Leafs",
    "Canucks": "Vancouver Canucks",
    "Golden Knights": "Vegas Golden Knights",
    "Capitals": "Washington Capitals",
    "Jets": "Winnipeg Jets",
    "Mammoth": "Utah Hockey Club",  # Utah's short name
    "Hockey Club": "Utah Hockey Club",
    "Coyotes": "Arizona Coyotes",
}

def normalize_team_name(team_name: str) -> str:
    """Convert any team name variation to the full official name"""
    if not team_name:
        return team_name
    
    # Already full name
    if team_name in ["Anaheim Ducks", "Boston Bruins", "Buffalo Sabres", "Calgary Flames",
                     "Carolina Hurricanes", "Chicago Blackhawks", "Colorado Avalanche",
                     "Columbus Blue Jackets", "Dallas Stars", "Detroit Red Wings",
                     "Edmonton Oilers", "Florida Panthers", "Los Angeles Kings",
                     "Minnesota Wild", "Montreal Canadiens", "Nashville Predators",
                     "New Jersey Devils", "New York Islanders", "New York Rangers",
                     "Ottawa Senators", "Philadelphia Flyers", "Pittsburgh Penguins",
                     "San Jose Sharks", "Seattle Kraken", "St. Louis Blues",
                     "Tampa Bay Lightning", "Toronto Maple Leafs", "Vancouver Canucks",
                     "Vegas Golden Knights", "Washington Capitals", "Winnipeg Jets",
                     "Utah Hockey Club", "Arizona Coyotes"]:
        return team_name
    
    # Map from short name
    return TEAM_NAME_MAP.get(team_name, team_name)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Simple in-memory cache with TTL
class PredictionCache:
    def __init__(self, ttl_hours=6):
        self.cache = {}
        self.ttl = timedelta(hours=ttl_hours)
    
    def _get_key(self, home_team: str, away_team: str, date: str) -> str:
        """Generate cache key from matchup details"""
        data = f"{home_team}_{away_team}_{date}"
        return hashlib.md5(data.encode()).hexdigest()
    
    def get(self, home_team: str, away_team: str, date: str) -> Optional[Dict]:
        """Get cached prediction if not expired"""
        key = self._get_key(home_team, away_team, date)
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() - entry['timestamp'] < self.ttl:
                return entry['data']
            else:
                # Remove expired entry
                del self.cache[key]
        return None
    
    def set(self, home_team: str, away_team: str, date: str, data: Dict):
        """Store prediction in cache"""
        key = self._get_key(home_team, away_team, date)
        self.cache[key] = {
            'data': data,
            'timestamp': datetime.now()
        }
    
    def clear_old_entries(self):
        """Remove expired cache entries"""
        now = datetime.now()
        expired_keys = [
            key for key, entry in self.cache.items()
            if now - entry['timestamp'] >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]

# Initialize cache (6 hour TTL - predictions valid for same day)
prediction_cache = PredictionCache(ttl_hours=6)

# Initialize live score services
live_score_service = LiveScoreService()
live_score_updater = None  # Will be initialized at startup

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Remove disconnected clients
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Create FastAPI app
app = FastAPI(
    title="NHL Daily Predictions powered by MoneyPuck",
    description="AI-powered NHL game predictions with advanced analytics from MoneyPuck.com",
    version="3.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Application startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize live score updater and daily scraper on startup"""
    global live_score_updater
    
    # Start live score monitoring
    print("🚀 Starting live score updater...")
    live_score_updater = LiveScoreUpdater(live_score_service, manager)
    asyncio.create_task(live_score_updater.start_monitoring())
    
    # Start daily result scraper in background thread
    print("📅 Starting daily result scraper scheduler...")
    scraper_thread = threading.Thread(target=run_scheduler, daemon=True)
    scraper_thread.start()
    print("✅ Daily scraper will run automatically at 2:00 AM every day")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean shutdown of live score updater"""
    global live_score_updater
    if live_score_updater:
        print("🛑 Stopping live score updater...")
        await live_score_updater.stop_monitoring()

class MatchupRequest(BaseModel):
    home_team: str
    away_team: str
    game_date: Optional[str] = None

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class NHLDataFetcher:
    """Fetch NHL data from NHL API (schedules) and MoneyPuck (stats/analytics)"""
    
    def __init__(self):
        self.base_url = NHL_API_BASE
        self.moneypuck = MoneyPuckService()
        self.session = requests.Session()
        self.team_abbrevs = {
            "Anaheim Ducks": "ANA", "Boston Bruins": "BOS", "Buffalo Sabres": "BUF",
            "Calgary Flames": "CGY", "Carolina Hurricanes": "CAR", "Chicago Blackhawks": "CHI",
            "Colorado Avalanche": "COL", "Columbus Blue Jackets": "CBJ", "Dallas Stars": "DAL",
            "Detroit Red Wings": "DET", "Edmonton Oilers": "EDM", "Florida Panthers": "FLA",
            "Los Angeles Kings": "LAK", "Minnesota Wild": "MIN", "Montreal Canadiens": "MTL",
            "Nashville Predators": "NSH", "New Jersey Devils": "NJD", "New York Islanders": "NYI",
            "New York Rangers": "NYR", "Ottawa Senators": "OTT", "Philadelphia Flyers": "PHI",
            "Pittsburgh Penguins": "PIT", "San Jose Sharks": "SJS", "Seattle Kraken": "SEA",
            "St. Louis Blues": "STL", "Tampa Bay Lightning": "TBL", "Toronto Maple Leafs": "TOR",
            "Vancouver Canucks": "VAN", "Vegas Golden Knights": "VGK", "Washington Capitals": "WSH",
            "Winnipeg Jets": "WPG", "Arizona Coyotes": "ARI", "Utah Hockey Club": "UTA"
        }
    
    def get_todays_games(self) -> list:
        """Fetch today's NHL games from NHL Stats API"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Try NHL official API first
            print(f"🔍 Fetching games from NHL API for {today}")
            url = f"{self.base_url}/score/{today}"
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            print(f"📊 NHL API Response keys: {data.keys() if data else 'None'}")
            
            games = []
            game_list = data.get("games", [])
            
            print(f"📅 Found {len(game_list)} games")
            
            for game in game_list:
                away_team = game.get("awayTeam", {})
                home_team = game.get("homeTeam", {})
                
                # Get full team names (e.g., "Vancouver Canucks" not just "Canucks")
                home_full_name = home_team.get("commonName", {}).get("default", "") or home_team.get("placeName", {}).get("default", "") + " " + home_team.get("name", {}).get("default", "")
                away_full_name = away_team.get("commonName", {}).get("default", "") or away_team.get("placeName", {}).get("default", "") + " " + away_team.get("name", {}).get("default", "")
                
                game_data = {
                    "home_team": home_full_name.strip(),
                    "away_team": away_full_name.strip(),
                    "time": game.get("startTimeUTC", "TBD"),
                    "date": today,
                    "event_id": str(game.get("id", "")),
                    "game_state": game.get("gameState", ""),
                    "home_abbrev": home_team.get("abbrev", ""),
                    "away_abbrev": away_team.get("abbrev", "")
                }
                
                print(f"🏒 Game: {game_data['away_team']} @ {game_data['home_team']} ({game_data['game_state']})")
                games.append(game_data)
            
            print(f"✅ Returning {len(games)} NHL games")
            return games
            
        except Exception as e:
            print(f"❌ Error fetching today's games from NHL API: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to TheSportsDB
            print("🔄 Trying TheSportsDB as fallback...")
            try:
                today = datetime.now().strftime("%Y-%m-%d")
                url = f"{self.sportsdb_url}/eventsday.php?d={today}&l=4380"
                
                print(f"🔍 Fetching games from: {url}")
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                print(f"📊 TheSportsDB Response: {data}")
                
                games = []
                events = data.get("events", [])
                
                print(f"📅 Found {len(events) if events else 0} events")
                
                if events:
                    for event in events:
                        # Only include NHL games
                        if event.get("strLeague") == "NHL":
                            game = {
                                "home_team": event.get("strHomeTeam", ""),
                                "away_team": event.get("strAwayTeam", ""),
                                "time": event.get("strTime", "TBD"),
                                "date": event.get("dateEvent", today),
                                "event_id": event.get("idEvent", "")
                            }
                            print(f"🏒 Game: {game['away_team']} @ {game['home_team']} at {game['time']}")
                            games.append(game)
                
                print(f"✅ Returning {len(games)} NHL games from TheSportsDB")
                return games
            except Exception as e2:
                print(f"❌ TheSportsDB also failed: {e2}")
                return []
    
    def get_team_abbrev(self, team_name: str) -> str:
        """Get team abbreviation from full name"""
        for full_name, abbrev in self.team_abbrevs.items():
            if team_name.lower() in full_name.lower():
                return abbrev
        return team_name[:3].upper()
    
    def get_team_stats(self, team_name: str) -> Dict[str, Any]:
        """Get current season team statistics from MoneyPuck (enhanced analytics)"""
        try:
            # Use MoneyPuck for comprehensive team stats with advanced analytics
            stats = self.moneypuck.get_team_stats(team_name)
            
            if stats:
                return stats
            
            # Fallback to default stats
            return {"team_name": team_name, "error": "Team not found"}
            
        except Exception as e:
            print(f"Error fetching team stats from MoneyPuck: {e}")
            return {"team_name": team_name, "error": str(e)}
    
    def get_team_roster_summary(self, team_abbrev: str) -> Dict[str, Any]:
        """Get key players from team roster - using MoneyPuck as default, NHL API as fallback"""
        try:
            # Use MoneyPuck for roster data (primary source)
            team_name = self.moneypuck.abbrev_to_name.get(team_abbrev, team_abbrev)
            roster = self.moneypuck.get_team_roster(team_name)
            
            # If MoneyPuck returns valid data, use it
            if roster and (roster.get('top_forwards') or roster.get('goalies')):
                print(f"✅ Using MoneyPuck roster for {team_name}")
                return roster
            
            # Fallback to NHL API if MoneyPuck has no data
            print(f"⚠️ MoneyPuck roster empty, trying NHL API for {team_abbrev}")
            url = f"{NHL_API_BASE}/roster/{team_abbrev}/current"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            forwards = []
            defense = []
            goalies = []
            
            # Parse roster by position
            for position_type, players in data.items():
                if isinstance(players, list):
                    for player in players:
                        player_name = player.get('firstName', {}).get('default', '') + ' ' + player.get('lastName', {}).get('default', '')
                        position = player.get('positionCode', '')
                        
                        if position == 'G':
                            goalies.append(player_name)
                        elif position == 'D':
                            defense.append(player_name)
                        else:  # F, L, R, C
                            forwards.append(player_name)
            
            print(f"✅ Using NHL API roster for {team_abbrev}")
            return {
                "top_forwards": forwards[:3] if forwards else [],
                "top_defense": defense[:2] if defense else [],
                "goalies": goalies[:2] if goalies else []
            }
            
        except Exception as e:
            print(f"❌ Error fetching roster for {team_abbrev}: {e}")
            # Final fallback to MoneyPuck placeholder
            team_name = self.moneypuck.abbrev_to_name.get(team_abbrev, team_abbrev)
            return self.moneypuck.get_team_roster(team_name)

class MatchupAnalyzer:
    """AI-powered NHL matchup analysis"""
    
    def __init__(self, openai_client):
        self.client = openai_client
        self.fetcher = NHLDataFetcher()

    def _extract_probs_and_confidence(self, analysis: str, home_team: str, away_team: str):
        """Best-effort extraction of probabilities and confidence from AI text.
        Returns (home_prob:int, away_prob:int, confidence:Optional[int])."""
        import re
        if not analysis:
            return 50, 50, None

        text = analysis
        home_prob = None
        away_prob = None
        confidence = None

        # 1) Preferred explicit lines
        m_home = re.search(r"Home\s*Team:\s*(\d{1,3})%", text, re.IGNORECASE)
        m_away = re.search(r"Away\s*Team:\s*(\d{1,3})%", text, re.IGNORECASE)
        if m_home and m_away:
            home_prob = int(m_home.group(1))
            away_prob = int(m_away.group(1))

        # 2) JSON summary line e.g. JSON: {"home_prob":62, "away_prob":38, "confidence":8}
        if home_prob is None or away_prob is None:
            try:
                import json
                m_json_line = re.search(r"JSON:\s*(\{.*\})", text, re.IGNORECASE)
                if m_json_line:
                    jd = json.loads(m_json_line.group(1))
                    if isinstance(jd, dict):
                        if home_prob is None and isinstance(jd.get("home_prob"), (int, float)):
                            home_prob = int(jd.get("home_prob"))
                        if away_prob is None and isinstance(jd.get("away_prob"), (int, float)):
                            away_prob = int(jd.get("away_prob"))
                        if isinstance(jd.get("confidence"), (int, float)):
                            confidence = int(jd.get("confidence"))
            except Exception:
                pass

        # 3) Team-name anchored percentages
        if home_prob is None:
            pattern_home_name = re.escape(home_team)
            m = re.search(rf"{pattern_home_name}[^\n%]*?(\d{{1,3}})%", text, re.IGNORECASE)
            if m:
                home_prob = int(m.group(1))
        if away_prob is None:
            pattern_away_name = re.escape(away_team)
            m = re.search(rf"{pattern_away_name}[^\n%]*?(\d{{1,3}})%", text, re.IGNORECASE)
            if m:
                away_prob = int(m.group(1))

        # 4) Any two percentages in order (fallback)
        if home_prob is None or away_prob is None:
            nums = [int(x) for x in re.findall(r"(\d{1,3})%", text)]
            if len(nums) >= 2:
                # assume first is home, second is away
                home_prob = nums[0]
                away_prob = nums[1]

        # Confidence
        if confidence is None:
            m_conf = re.search(r"(\d{1,2})\s*/\s*10", text)
            if m_conf:
                confidence = int(m_conf.group(1))

        # Defaults and normalization
        if home_prob is None and away_prob is None:
            home_prob, away_prob = 50, 50
        elif home_prob is None and away_prob is not None:
            away_prob = max(0, min(100, away_prob))
            home_prob = max(0, min(100, 100 - away_prob))
        elif home_prob is not None and away_prob is None:
            home_prob = max(0, min(100, home_prob))
            away_prob = max(0, min(100, 100 - home_prob))
        else:
            # Clamp and renormalize to sum 100 if off
            home_prob = max(0, min(100, home_prob))
            away_prob = max(0, min(100, away_prob))
            total = home_prob + away_prob
            if total != 100 and total > 0:
                home_scaled = round(home_prob * 100 / total)
                away_scaled = 100 - home_scaled
                home_prob, away_prob = home_scaled, away_scaled

        return int(home_prob), int(away_prob), (int(confidence) if confidence is not None else None)

    def _extract_analysis_text(self, analysis: str) -> str:
        """Extract only the ANALYSIS section (exclude percentages and confidence)."""
        if not analysis:
            return ""
        import re
        text = analysis
        # Try to capture text under **ANALYSIS** heading until next heading or end
        m = re.search(r"(?is)\*\*ANALYSIS\*\*\s*(.+?)(?:\n\s*\*\*[A-Z \-/]+\*\*|\Z)", text)
        if m:
            body = m.group(1).strip()
        else:
            # Fallback: drop lines that look like prob/conf and keep the rest
            lines = []
            for line in text.splitlines():
                lt = line.strip()
                if not lt:
                    continue
                if re.search(r"Home\s*Team:\s*\d+%", lt, re.IGNORECASE):
                    continue
                if re.search(r"Away\s*Team:\s*\d+%", lt, re.IGNORECASE):
                    continue
                if re.search(r"\bCONFIDENCE\b", lt, re.IGNORECASE):
                    continue
                if re.search(r"\d+\s*/\s*10", lt):
                    continue
                lines.append(line)
            body = "\n".join(lines).strip()
        return body
    
    def analyze_matchup(self, home_team: str, away_team: str, game_date: Optional[str] = None) -> Dict[str, Any]:
        """Analyze matchup and generate AI prediction with win probabilities"""
        
        print(f"📊 Fetching stats for: {home_team} (home) vs {away_team} (away)")
        
        # Fetch team stats
        home_stats = self.fetcher.get_team_stats(home_team)
        away_stats = self.fetcher.get_team_stats(away_team)
        
        print(f"🏠 Home stats: {home_stats}")
        print(f"✈️  Away stats: {away_stats}")
        
        if "error" in home_stats or "error" in away_stats:
            return {
                "error": "Failed to fetch team data",
                "home_stats": home_stats,
                "away_stats": away_stats
            }
        
        # Fetch roster info for player context
        home_roster = self.fetcher.get_team_roster_summary(home_stats.get("abbrev", ""))
        away_roster = self.fetcher.get_team_roster_summary(away_stats.get("abbrev", ""))
        
        print(f"🎯 Home roster ({home_team}): Forwards: {', '.join(home_roster.get('top_forwards', [])[:3])}, Defense: {', '.join(home_roster.get('top_defense', [])[:2])}, Goalies: {', '.join(home_roster.get('goalies', []))}") 
        print(f"🎯 Away roster ({away_team}): Forwards: {', '.join(away_roster.get('top_forwards', [])[:3])}, Defense: {', '.join(away_roster.get('top_defense', [])[:2])}, Goalies: {', '.join(away_roster.get('goalies', []))}")
        
        # Build prompt for GPT
        prompt = self._build_analysis_prompt(home_stats, away_stats, home_roster, away_roster, game_date)
        
        try:
            # Use GPT-4o for advanced reasoning and analysis
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert NHL analyst writing in the engaging style of a beat reporter. Provide matchup analysis with win probabilities.

Your response MUST follow this EXACT format and structure:

**WIN PROBABILITY**
Home Team: XX%
Away Team: YY%

**ANALYSIS**
[Opening paragraph: 2-3 sentences setting up the matchup like a game preview, mentioning teams, their status/streaks, and what makes this game compelling. Do NOT use bold text or bullets here.]

**Current Form and Last-10 Trends:** [1-2 sentences comparing both teams' recent records and momentum]
**Goal Differential and Goals Context:** [1-2 sentences on goals scored/conceded and what it reveals about each team's style]
**Home vs Road Splits:** [1-2 sentences on home team's home record and away team's road record]
**Schedule/Rest Factors:** [1 sentence on any momentum or rest implications from their records]
**Style/Tempo Implications:** [1-2 sentences predicting game pace and style based on stats]

**Projected Impact Players:**
Home: Name 2-3 actual players from the roster (forwards/defense) who could impact the game, with brief reasoning for each.
Away: Name 2-3 actual players from the roster (forwards/defense) who could impact the game, with brief reasoning for each.

**Projected Starting Goalies:**
Home: [Select from actual goalie names provided] (projected starter)
Away: [Select from actual goalie names provided] (projected starter)
Note: Monitor pregame reports for confirmed starters.

**Injuries/Notes:**
[Only mention widely confirmed injuries; otherwise state: "No notable injuries confirmed as of today."]

**CONFIDENCE**
X/10 – [Brief reasoning in one sentence]

CRITICAL FORMATTING RULES:
- Use **Bold Text:** for all section headers (Current Form, Goal Differential, etc.)
- Use bullet points (- ) ONLY for Projected Impact Players and Projected Starting Goalies sections
- Do NOT use bullets or bold for the opening paragraph
- Keep each section to 1-2 sentences maximum
- Do NOT restate percentages or confidence scores in the ANALYSIS section
- Use actual player names from the roster data provided
- Percentages must add up to 100%
- Be factual and grounded in provided stats only"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_completion_tokens=500
            )
            
            analysis = response.choices[0].message.content
            
            print(f"🤖 AI Analysis:\n{analysis}\n")
            
            # Extract probabilities and confidence
            h_prob, a_prob, conf = self._extract_probs_and_confidence(
                analysis=analysis,
                home_team=home_stats.get("team_name", home_team),
                away_team=away_stats.get("team_name", away_team)
            )

            # Extract clean ANALYSIS text only (no percentages/confidence)
            analysis_text = self._extract_analysis_text(analysis)

            # Fallback simple model if parsing failed (e.g., 50/50 with no confidence)
            used_fallback = False
            if (h_prob, a_prob) == (50, 50) and conf is None:
                used_fallback = True
                # Heuristic: point percentage + goal differential + last-10, with home advantage
                def last10_winpct(s):
                    try:
                        l10 = str(s.get("last_10", "0-0-0")).split("-")
                        w = float(l10[0]); l = float(l10[1]); o = float(l10[2])
                        tot = max(1.0, w + l + o)
                        return w / tot
                    except Exception:
                        return 0.5

                def score(s):
                    pct = float(s.get("point_pct", 0))                   # 0..1
                    gd = float(s.get("goal_diff", 0))
                    gp = max(1.0, float(s.get("games_played", 1)))
                    gd_norm = 0.5 + 0.5 * max(-1.0, min(1.0, gd / max(10.0, gp)))  # 0..1
                    l10 = last10_winpct(s)                                 # 0..1
                    return 0.6 * pct + 0.25 * gd_norm + 0.15 * l10

                home_score = score(home_stats) + 0.05  # stronger home ice advantage
                away_score = score(away_stats)
                total = max(1e-6, home_score + away_score)
                h_prob = int(round(home_score * 100 / total))
                a_prob = 100 - h_prob
                # derive a simple confidence from margin
                margin = abs(h_prob - a_prob)
                conf = max(3, min(9, int(round(margin / 10)) + 4))
                if not analysis_text:
                    winner = "home" if h_prob > a_prob else ("away" if a_prob > h_prob else "either")
                    analysis_text = (
                        "Key factors considered: current point percentage, normalized goal differential, recent (last-10) form, and home-ice advantage. "
                        f"The model slightly favors the {winner} side based on these indicators."
                    )

            # Ensure we always have a confidence value
            if conf is None:
                margin = abs(h_prob - a_prob)
                conf = max(3, min(9, int(round(margin / 10)) + 4))

            # Ensure we always have a minimal analysis block
            if not analysis_text or not str(analysis_text).strip():
                analysis_text = (
                    "Model returned no narrative; using calculated probabilities from standings, recent form, and goal differential."
                )
            
            result = {
                "success": True,
                "home_team": home_stats.get("team_name", home_team),
                "away_team": away_stats.get("team_name", away_team),
                "game_date": game_date or "Next matchup",
                "home_stats": home_stats,
                "away_stats": away_stats,
                "analysis": analysis,
                "analysis_text": analysis_text,
                "home_prob": h_prob,
                "away_prob": a_prob,
                "confidence": conf,
                "generated_at": datetime.now().isoformat()
            }
            
            print(f"✅ Returning result: home={result['home_team']}, away={result['away_team']}")
            print(f"   Parsed probs -> home: {h_prob}%, away: {a_prob}%, confidence: {conf if conf is not None else 'N/A'}")
            
            return result
            
        except Exception as e:
            return {
                "error": f"AI analysis failed: {str(e)}",
                "home_stats": home_stats,
                "away_stats": away_stats
            }
    
    def _build_analysis_prompt(self, home_stats: Dict, away_stats: Dict, home_roster: Dict, away_roster: Dict, game_date: Optional[str]) -> str:
        """Build prompt for AI analysis"""
        
        # Format player lists
        home_forwards_str = ", ".join(home_roster.get("top_forwards", [])[:3]) if home_roster.get("top_forwards") else "top-line forwards"
        away_forwards_str = ", ".join(away_roster.get("top_forwards", [])[:3]) if away_roster.get("top_forwards") else "top-line forwards"
        
        home_goalies_str = ", ".join(home_roster.get("goalies", [])[:2]) if home_roster.get("goalies") else "TBD"
        away_goalies_str = ", ".join(away_roster.get("goalies", [])[:2]) if away_roster.get("goalies") else "TBD"
        
        return f"""You are an expert NHL analyst using MoneyPuck's advanced analytics. Analyze the matchup below and provide:

1) WIN PROBABILITY section with exact lines:
Home Team: XX%
Away Team: YY%

2) ANALYSIS section in NHL reporter style: start with a 1–2 sentence lede like a game preview. Then provide 3–5 concise, data-driven bullets. Do NOT restate percentages or confidence here. Focus on:
- Current form and last-10 trends
- Goal differential, actual goals vs expected goals (xGoals) from MoneyPuck
- Home vs road splits relevant to this matchup
- Advanced metrics: Corsi%, Fenwick%, shooting%, save%
- Power play and penalty kill efficiency
- Style/tempo implications derived from stats

Also within ANALYSIS include these subsections with bold headings:

**Projected Impact Players**: Reference these actual players when discussing likely goal/assist contributors:
- Home: {home_forwards_str}
- Away: {away_forwards_str}
Mention 1-2 players per team with a brief reason based on their role and team form.

**Projected Starting Goalies**: 
- Home: {home_goalies_str} (likely starter based on roster)
- Away: {away_goalies_str} (likely starter based on roster)
Note that these are projections; confirm with pregame reports.

**Injuries/Notes**: Only mention if widely known and non-speculative; otherwise say "No notable injuries confirmed as of today." Do NOT make up injuries.

The ANALYSIS section must NOT restate percentages or confidence.

3) CONFIDENCE as X/10

At the very end, output a single line starting with:
JSON: {{"home_prob": XX, "away_prob": YY, "confidence": X}}

Use integers for percentages. Ensure XX + YY = 100.

HOME: {home_stats['team_name']}
Record: {home_stats['wins']}-{home_stats['losses']}-{home_stats['ot_losses']} ({home_stats['points']} pts)
Home Record: {home_stats['home_record']}
Goals: {home_stats['goals_for']} for, {home_stats['goals_against']} against
Expected Goals (MoneyPuck): {home_stats.get('xGoalsFor', 'N/A')} xGF, {home_stats.get('xGoalsAgainst', 'N/A')} xGA
Corsi For %: {home_stats.get('corsiFor', 'N/A')}%
Shooting %: {home_stats.get('shooting_pct', 'N/A')}% | Save %: {home_stats.get('save_pct', 'N/A')}%
Power Play: {home_stats.get('pp_pct', 'N/A')}% | Penalty Kill: {home_stats.get('pk_pct', 'N/A')}%
Last 10: {home_stats['last_10']}
Streak: {home_stats['streak']}

AWAY: {away_stats['team_name']}
Record: {away_stats['wins']}-{away_stats['losses']}-{away_stats['ot_losses']} ({away_stats['points']} pts)
Road Record: {away_stats['road_record']}
Goals: {away_stats['goals_for']} for, {away_stats['goals_against']} against
Expected Goals (MoneyPuck): {away_stats.get('xGoalsFor', 'N/A')} xGF, {away_stats.get('xGoalsAgainst', 'N/A')} xGA
Corsi For %: {away_stats.get('corsiFor', 'N/A')}%
Shooting %: {away_stats.get('shooting_pct', 'N/A')}% | Save %: {away_stats.get('save_pct', 'N/A')}%
Power Play: {away_stats.get('pp_pct', 'N/A')}% | Penalty Kill: {away_stats.get('pk_pct', 'N/A')}%
Last 10: {away_stats['last_10']}
Streak: {away_stats['streak']}

Data source: MoneyPuck.com - Advanced NHL Analytics"""

# Initialize analyzer
analyzer = MatchupAnalyzer(client) if client else None

# Setup routes directly in this file to avoid circular imports
from fastapi.responses import HTMLResponse
from nhl_html import get_html_template

@app.get("/", response_class=HTMLResponse)
async def root():
    """Home page showing today's NHL games"""
    return get_html_template()

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_dashboard():
    """Analytics dashboard with charts and performance metrics"""
    from analytics_html import get_analytics_html_template
    return get_analytics_html_template()

@app.get("/live-scores-test", response_class=HTMLResponse)
async def live_scores_test():
    """Serve the live scores test page"""
    try:
        with open("test_live_scores.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Test page not found")

@app.get("/api/games/{date}")
async def get_games_by_date(date: str):
    """Get NHL games for a specific date (YYYY-MM-DD format)"""
    try:
        fetcher = NHLDataFetcher()
        
        # Validate date format
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
        
        # Fetch games for specific date
        url = f"{fetcher.base_url}/score/{date}"
        response = fetcher.session.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        games = []
        game_list = data.get("games", [])
        
        for game in game_list:
            away_team = game.get("awayTeam", {})
            home_team = game.get("homeTeam", {})
            
            games.append({
                "home_team": home_team.get("name", {}).get("default", ""),
                "away_team": away_team.get("name", {}).get("default", ""),
                "time": game.get("startTimeUTC", "TBD"),
                "date": date,
                "event_id": str(game.get("id", "")),
                "game_state": game.get("gameState", ""),
                "home_abbrev": home_team.get("abbrev", ""),
                "away_abbrev": away_team.get("abbrev", ""),
                "home_score": home_team.get("score"),
                "away_score": away_team.get("score")
            })
        
        return {
            "success": True,
            "date": date,
            "games": games,
            "count": len(games)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch games for {date}: {str(e)}"
        )

@app.get("/api/todays-games")
async def get_todays_games():
    """Get today's NHL games schedule"""
    try:
        fetcher = NHLDataFetcher()
        games = fetcher.get_todays_games()
        return {
            "success": True,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "games": games,
            "count": len(games)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch today's games: {str(e)}"
        )

@app.post("/api/analyze")
async def analyze_matchup(request: dict):
    """Analyze matchup and generate AI prediction"""
    
    if not analyzer:
        raise HTTPException(
            status_code=500,
            detail="Analyzer not initialized. Please configure OPENAI_API_KEY."
        )
    
    try:
        # Normalize team names (e.g., "Mammoth" -> "Utah Hockey Club")
        home_team = normalize_team_name(request.get("home_team", ""))
        away_team = normalize_team_name(request.get("away_team", ""))
        game_date = request.get("game_date") or datetime.now().strftime("%Y-%m-%d")
        
        print(f"📝 Normalized teams: {request.get('away_team')} -> {away_team}, {request.get('home_team')} -> {home_team}")
        
        # Check if predictions are locked for this game
        try:
            prediction_locks = await live_score_service.check_prediction_locks()
            for lock in prediction_locks:
                if (lock.get("home_team") == home_team and 
                    lock.get("away_team") == away_team and 
                    lock.get("is_locked", False)):
                    raise HTTPException(
                        status_code=423,  # 423 Locked
                        detail=f"Predictions are locked for {away_team} @ {home_team}. Game has started or is in progress."
                    )
        except HTTPException:
            raise
        except Exception as e:
            # If live score service fails, log but don't block predictions
            print(f"⚠️ Warning: Could not check prediction locks: {e}")
        
        # Check cache first
        cached_result = prediction_cache.get(home_team, away_team, game_date)
        if cached_result:
            print(f"💾 Cache hit for {home_team} vs {away_team} on {game_date}")
            return cached_result
        
        print(f"\n🔍 Analyzing: {home_team} vs {away_team}")
        result = analyzer.analyze_matchup(
            home_team=home_team,
            away_team=away_team,
            game_date=game_date
        )
        
        # Store in cache if successful
        if "error" not in result:
            prediction_cache.set(home_team, away_team, game_date, result)
            print(f"💾 Cached prediction for {home_team} vs {away_team}")
            
            # Store prediction in database for accuracy tracking
            if result.get("home_prob") and result.get("away_prob") and result.get("confidence"):
                # Get database session (use dependency injection pattern)
                from database import SessionLocal
                db = SessionLocal()
                try:
                    # Parse game date
                    if 'T' in game_date:
                        game_date_obj = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
                    else:
                        game_date_obj = datetime.strptime(game_date, '%Y-%m-%d')
                    
                    # Check if prediction already exists
                    existing = db.query(Prediction).filter(
                        Prediction.home_team == result.get("home_team", home_team),
                        Prediction.away_team == result.get("away_team", away_team),
                        Prediction.game_date == game_date_obj
                    ).first()
                    
                    if existing:
                        # Update existing prediction
                        existing.home_prob = float(result["home_prob"])
                        existing.away_prob = float(result["away_prob"])
                        existing.confidence = str(result["confidence"])
                        existing.predicted_winner = "home" if result["home_prob"] > result["away_prob"] else "away"
                        existing.analysis_text = result.get("analysis", "")
                    else:
                        # Create new prediction
                        prediction = Prediction(
                            home_team=result.get("home_team", home_team),
                            away_team=result.get("away_team", away_team),
                            game_date=game_date_obj,
                            home_prob=float(result["home_prob"]),
                            away_prob=float(result["away_prob"]),
                            confidence=str(result["confidence"]),
                            predicted_winner="home" if result["home_prob"] > result["away_prob"] else "away",
                            analysis_text=result.get("analysis", ""),
                            user_id=None  # Anonymous prediction
                        )
                        db.add(prediction)
                    
                    db.commit()
                    print(f"📊 Stored prediction in database")
                    
                    # Add lock status and live scores to result
                    if existing:
                        result["is_locked"] = existing.is_locked
                        result["game_status"] = existing.game_status
                        result["live_home_score"] = existing.live_home_score
                        result["live_away_score"] = existing.live_away_score
                except Exception as db_error:
                    db.rollback()
                    print(f"⚠️ Database error: {db_error}")
                finally:
                    db.close()
        
        print(f"✅ Analysis complete!")
        return result
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

@app.get("/api/accuracy")
async def get_accuracy_stats(db: Session = Depends(get_db)):
    """Get comprehensive prediction accuracy statistics from database"""
    try:
        # Get or create overall stats record
        from database import get_or_create_overall_stats
        stats = get_or_create_overall_stats(db)
        
        # Recalculate stats to ensure they're current
        update_accuracy_stats(db)
        db.refresh(stats)
        
        # Calculate accuracy percentages from available fields
        last_7_days_accuracy = round(
            (stats.last_7_days_correct / stats.last_7_days_total * 100) 
            if stats.last_7_days_total > 0 else 0, 1
        )
        last_30_days_accuracy = round(
            (stats.last_30_days_correct / stats.last_30_days_total * 100) 
            if stats.last_30_days_total > 0 else 0, 1
        )
        
        # Confidence-based accuracy
        high_conf_accuracy = round(
            (stats.high_confidence_correct / stats.high_confidence_total * 100)
            if stats.high_confidence_total > 0 else 0, 1
        )
        med_conf_accuracy = round(
            (stats.medium_confidence_correct / stats.medium_confidence_total * 100)
            if stats.medium_confidence_total > 0 else 0, 1
        )
        low_conf_accuracy = round(
            (stats.low_confidence_correct / stats.low_confidence_total * 100)
            if stats.low_confidence_total > 0 else 0, 1
        )
        
        # Parse team stats
        import json
        best_teams = json.loads(stats.best_teams) if stats.best_teams else []
        worst_teams = json.loads(stats.worst_teams) if stats.worst_teams else []
        
        # Get locked predictions count
        locked_count = db.query(Prediction).filter(Prediction.is_locked == True).count()
        pending_count = db.query(Prediction).filter(
            Prediction.is_correct.is_(None),
            Prediction.is_locked == False
        ).count()
        
        return {
            "success": True,
            "overall": {
                "total_predictions": stats.total_predictions,
                "correct_predictions": stats.correct_predictions,
                "accuracy_percentage": round(stats.accuracy_percentage, 1),
                "locked_predictions": locked_count,
                "pending_results": pending_count
            },
            "time_based": {
                "last_7_days": {
                    "accuracy": last_7_days_accuracy,
                    "total": stats.last_7_days_total,
                    "correct": stats.last_7_days_correct
                },
                "last_30_days": {
                    "accuracy": last_30_days_accuracy,
                    "total": stats.last_30_days_total,
                    "correct": stats.last_30_days_correct
                }
            },
            "confidence_based": {
                "high": {
                    "accuracy": high_conf_accuracy,
                    "total": stats.high_confidence_total,
                    "correct": stats.high_confidence_correct,
                    "label": "8-10 Confidence"
                },
                "medium": {
                    "accuracy": med_conf_accuracy,
                    "total": stats.medium_confidence_total,
                    "correct": stats.medium_confidence_correct,
                    "label": "5-7 Confidence"
                },
                "low": {
                    "accuracy": low_conf_accuracy,
                    "total": stats.low_confidence_total,
                    "correct": stats.low_confidence_correct,
                    "label": "1-4 Confidence"
                }
            },
            "team_performance": {
                "best_teams": best_teams,
                "worst_teams": worst_teams
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve accuracy stats: {str(e)}"
        )

@app.post("/api/update-result")
async def update_game_result(request: dict, db: Session = Depends(get_db)):
    """Update prediction with actual game result"""
    try:
        home_team = request.get("home_team")
        away_team = request.get("away_team")
        game_date = request.get("game_date")
        winner = request.get("winner")  # "home" or "away"
        
        if not all([home_team, away_team, game_date, winner]):
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        if winner not in ["home", "away"]:
            raise HTTPException(status_code=400, detail="Winner must be 'home' or 'away'")
        
        # Parse game date
        if 'T' in game_date:
            game_date_obj = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
        else:
            game_date_obj = datetime.strptime(game_date, '%Y-%m-%d')
        
        # Find prediction
        prediction = db.query(Prediction).filter(
            Prediction.home_team == home_team,
            Prediction.away_team == away_team,
            Prediction.game_date == game_date_obj
        ).first()
        
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # Update result
        prediction.actual_winner = winner
        prediction.is_correct = (prediction.predicted_winner == winner)
        
        db.commit()
        
        # Update accuracy stats
        update_accuracy_stats(db)
        
        return {
            "success": True,
            "prediction": {
                "home_team": prediction.home_team,
                "away_team": prediction.away_team,
                "game_date": prediction.game_date.isoformat(),
                "predicted_winner": prediction.predicted_winner,
                "actual_winner": prediction.actual_winner,
                "is_correct": prediction.is_correct
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update result: {str(e)}"
        )

@app.post("/api/predictions/lock")
async def lock_prediction(request: dict, db: Session = Depends(get_db)):
    """Manually lock a prediction to prevent modifications"""
    try:
        home_team = request.get("home_team")
        away_team = request.get("away_team")
        game_date = request.get("game_date")
        
        if not all([home_team, away_team, game_date]):
            raise HTTPException(status_code=400, detail="Missing required fields: home_team, away_team, game_date")
        
        # Parse game date
        if 'T' in game_date:
            game_date_obj = datetime.fromisoformat(game_date.replace('Z', '+00:00'))
        else:
            game_date_obj = datetime.strptime(game_date, '%Y-%m-%d')
        
        # Find prediction
        prediction = db.query(Prediction).filter(
            Prediction.home_team == home_team,
            Prediction.away_team == away_team,
            Prediction.game_date == game_date_obj
        ).first()
        
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        if prediction.is_locked:
            return {
                "success": True,
                "message": "Prediction was already locked",
                "prediction": {
                    "home_team": prediction.home_team,
                    "away_team": prediction.away_team,
                    "game_date": prediction.game_date.isoformat(),
                    "is_locked": prediction.is_locked
                }
            }
        
        # Lock the prediction
        prediction.is_locked = True
        db.commit()
        
        return {
            "success": True,
            "message": "Prediction locked successfully",
            "prediction": {
                "home_team": prediction.home_team,
                "away_team": prediction.away_team,
                "game_date": prediction.game_date.isoformat(),
                "is_locked": prediction.is_locked
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to lock prediction: {str(e)}"
        )

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user account"""
    try:
        user = create_user(db, user_data.username, user_data.email, user_data.password)
        
        # Create access token
        access_token = create_access_token(data={"sub": user.username})
        
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
        )

@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login and receive JWT token"""
    user = authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me")
async def get_current_user_info(current_user: User = Depends(require_current_user)):
    """Get current user information"""
    return {
        "username": current_user.username,
        "email": current_user.email,
        "is_premium": current_user.is_premium,
        "created_at": current_user.created_at.isoformat()
    }

# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/api/analytics/accuracy-trends")
async def get_accuracy_trends_endpoint(
    days: int = 30, 
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get accuracy trends over time"""
    try:
        from analytics import get_accuracy_trends
        user_id = current_user.id if current_user else None
        data = get_accuracy_trends(db, days=days, user_id=user_id)
        return {"success": True, **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/confidence-analysis")
async def get_confidence_analysis_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get accuracy by confidence level"""
    try:
        from analytics import get_confidence_analysis
        user_id = current_user.id if current_user else None
        data = get_confidence_analysis(db, user_id=user_id)
        return {"success": True, **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/team-performance")
async def get_team_performance_endpoint(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get team-specific prediction performance"""
    try:
        from analytics import get_team_performance
        user_id = current_user.id if current_user else None
        data = get_team_performance(db, user_id=user_id, limit=limit)
        return {"success": True, **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/streaks")
async def get_prediction_streaks_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get current and longest prediction streaks"""
    try:
        from analytics import get_prediction_streaks
        user_id = current_user.id if current_user else None
        data = get_prediction_streaks(db, user_id=user_id)
        return {"success": True, **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics/home-away")
async def get_home_away_analysis_endpoint(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get home vs away prediction analysis"""
    try:
        from analytics import get_home_away_analysis
        user_id = current_user.id if current_user else None
        data = get_home_away_analysis(db, user_id=user_id)
        return {"success": True, **data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ADMIN/UTILITY ENDPOINTS
# ============================================================================

@app.post("/api/admin/scrape-results")
async def trigger_result_scrape(days_back: int = 1, current_user: User = Depends(require_current_user)):
    """Manually trigger game result scraping (admin only)"""
    # For now, allow any authenticated user - in production, add admin role check
    try:
        from game_result_scraper import NHLResultScraper
        
        scraper = NHLResultScraper()
        stats = scraper.scrape_recent_games(days_back=days_back)
        
        return {
            "success": True,
            "message": f"Scraped last {days_back} days",
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Scraping failed: {str(e)}"
        )

@app.get("/api/admin/unresolved-predictions")
async def get_unresolved_predictions(days_back: int = 7, current_user: User = Depends(require_current_user)):
    """Get predictions that haven't been updated with results yet"""
    try:
        from game_result_scraper import NHLResultScraper
        
        scraper = NHLResultScraper()
        unresolved = scraper.get_unresolved_predictions(days_back=days_back)
        
        return {
            "success": True,
            "count": len(unresolved),
            "predictions": unresolved,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get unresolved predictions: {str(e)}"
        )

# Live Scores WebSocket endpoint
@app.websocket("/ws/live-scores")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time live score updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and listen for client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Live Scores REST endpoints
@app.get("/api/live-scores")
async def get_live_scores():
    """Get current live scores for all active games"""
    try:
        live_scores = await live_score_service.get_live_scores()
        return {
            "success": True,
            "live_scores": live_scores,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch live scores: {str(e)}"
        )

@app.get("/api/live-scores/{game_id}")
async def get_game_live_score(game_id: str):
    """Get live score for a specific game"""
    try:
        game_summary = await live_score_service.get_game_summary(game_id)
        if not game_summary:
            raise HTTPException(
                status_code=404,
                detail=f"Game {game_id} not found or not active"
            )
        
        return {
            "success": True,
            "game": game_summary,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch game {game_id}: {str(e)}"
        )

@app.post("/api/live-scores/refresh")
async def refresh_live_scores():
    """Manually trigger live scores refresh"""
    try:
        live_scores = await live_score_service.get_live_scores()
        
        # Broadcast to all connected WebSocket clients
        await manager.broadcast({
            "type": "live_scores_update",
            "data": live_scores,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "message": "Live scores refreshed and broadcasted",
            "games_count": len(live_scores),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh live scores: {str(e)}"
        )

@app.get("/api/prediction-locks")
async def get_prediction_locks():
    """Get current prediction lock status for all games"""
    try:
        locks = await live_score_service.check_prediction_locks()
        return {
            "success": True,
            "prediction_locks": locks,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check prediction locks: {str(e)}"
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "NHL Daily Predictions",
        "openai_configured": client is not None,
        "live_scores_active": live_score_updater is not None,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("🏒 NHL Daily Predictions")
    print("=" * 50)
    
    if not OPENAI_API_KEY:
        print("⚠️  WARNING: OPENAI_API_KEY not set!")
        print("   Please add your OpenAI API key to .env file")
        print()
    else:
        print("✅ OpenAI API configured")
    
    # Get port from environment variable (for Docker/cloud deployments)
    port = int(os.getenv("PORT", 8001))
    host = os.getenv("HOST", "0.0.0.0")  # 0.0.0.0 for Docker containers
    
    print(f"🌐 Starting server on {host}:{port}")
    print("=" * 50)
    
    uvicorn.run(app, host=host, port=port)
