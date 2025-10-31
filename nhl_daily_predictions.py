from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
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

# Database and auth imports
from database import get_db, Prediction, AccuracyStats, User, update_accuracy_stats
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
NHL_API_BASE = "https://api-web.nhle.com/v1"
SPORTSDB_API_KEY = "123"  # Updated API key
SPORTSDB_API_BASE = "https://www.thesportsdb.com/api/v1/json"

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

# Create FastAPI app
app = FastAPI(
    title="NHL Daily Predictions",
    description="AI-powered NHL game predictions with win probabilities",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    """Fetch NHL data from free NHL Stats API and TheSportsDB"""
    
    def __init__(self):
        self.base_url = NHL_API_BASE
        self.sportsdb_url = f"{SPORTSDB_API_BASE}/{SPORTSDB_API_KEY}"
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
                
                game_data = {
                    "home_team": home_team.get("name", {}).get("default", ""),
                    "away_team": away_team.get("name", {}).get("default", ""),
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
        """Get current season team statistics"""
        try:
            abbrev = self.get_team_abbrev(team_name)
            
            # Get standings which includes team stats
            url = f"{self.base_url}/standings/now"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Find team in standings
            for standing in data.get("standings", []):
                if standing.get("teamAbbrev", {}).get("default") == abbrev:
                    return {
                        "team_name": standing.get("teamName", {}).get("default", team_name),
                        "abbrev": abbrev,
                        "wins": standing.get("wins", 0),
                        "losses": standing.get("losses", 0),
                        "ot_losses": standing.get("otLosses", 0),
                        "points": standing.get("points", 0),
                        "games_played": standing.get("gamesPlayed", 0),
                        "goals_for": standing.get("goalFor", 0),
                        "goals_against": standing.get("goalAgainst", 0),
                        "goal_diff": standing.get("goalDifferential", 0),
                        "point_pct": standing.get("pointPctg", 0),
                        "streak": standing.get("streakCode", "N/A"),
                        "home_record": f"{standing.get('homeWins', 0)}-{standing.get('homeLosses', 0)}-{standing.get('homeOtLosses', 0)}",
                        "road_record": f"{standing.get('roadWins', 0)}-{standing.get('roadLosses', 0)}-{standing.get('roadOtLosses', 0)}",
                        "last_10": f"{standing.get('l10Wins', 0)}-{standing.get('l10Losses', 0)}-{standing.get('l10OtLosses', 0)}"
                    }
            
            return {"team_name": team_name, "error": "Team not found"}
            
        except Exception as e:
            print(f"Error fetching team stats: {e}")
            return {"team_name": team_name, "error": str(e)}
    
    def get_team_roster_summary(self, team_abbrev: str) -> Dict[str, Any]:
        """Get key players from team roster - top scorers and goalies"""
        try:
            url = f"{self.base_url}/roster/{team_abbrev}/current"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            forwards = data.get("forwards", [])
            defensemen = data.get("defensemen", [])
            goalies = data.get("goalies", [])
            
            # Get top forwards by position (simplified - would need stats API for actual points)
            top_forwards = []
            for player in forwards[:3]:  # Top 3 forwards from roster
                name = f"{player.get('firstName', {}).get('default', '')} {player.get('lastName', {}).get('default', '')}"
                top_forwards.append(name.strip())
            
            # Get defensemen
            top_defense = []
            for player in defensemen[:2]:  # Top 2 D
                name = f"{player.get('firstName', {}).get('default', '')} {player.get('lastName', {}).get('default', '')}"
                top_defense.append(name.strip())
            
            # Get goalies
            goalie_names = []
            for player in goalies:
                name = f"{player.get('firstName', {}).get('default', '')} {player.get('lastName', {}).get('default', '')}"
                goalie_names.append(name.strip())
            
            return {
                "top_forwards": top_forwards,
                "top_defense": top_defense,
                "goalies": goalie_names
            }
            
        except Exception as e:
            print(f"Error fetching roster for {team_abbrev}: {e}")
            return {
                "top_forwards": [],
                "top_defense": [],
                "goalies": []
            }

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
        
        print(f"🎯 Home roster: {home_roster}")
        print(f"🎯 Away roster: {away_roster}")
        
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
- Home: [Player name] is [brief reason for impact potential]
- Away: [Player name] is [brief reason for impact potential]

**Projected Starting Goalies:**
- Home: [Goalie name] (projected)
- Away: [Goalie name] (projected)
Monitor pregame reports for confirmed starters.

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
        
        return f"""You are an expert NHL analyst. Analyze the matchup below and provide:

1) WIN PROBABILITY section with exact lines:
Home Team: XX%
Away Team: YY%

2) ANALYSIS section in NHL reporter style: start with a 1–2 sentence lede like a game preview. Then provide 3–5 concise, data-driven bullets. Do NOT restate percentages or confidence here. Focus on:
- Current form and last-10 trends
- Goal differential and goals for/against context
- Home vs road splits relevant to this matchup
- Schedule/rest factors implied by records (no made-up injuries)
- Brief style/tempo implications derived from provided stats only

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
Last 10: {home_stats['last_10']}
Streak: {home_stats['streak']}

AWAY: {away_stats['team_name']}
Record: {away_stats['wins']}-{away_stats['losses']}-{away_stats['ot_losses']} ({away_stats['points']} pts)
Road Record: {away_stats['road_record']}
Goals: {away_stats['goals_for']} for, {away_stats['goals_against']} against
Last 10: {away_stats['last_10']}
Streak: {away_stats['streak']}"""

# Initialize analyzer
analyzer = MatchupAnalyzer(client) if client else None

# Setup routes directly in this file to avoid circular imports
from fastapi.responses import HTMLResponse
from nhl_html import get_html_template

@app.get("/", response_class=HTMLResponse)
async def root():
    """Home page showing today's NHL games"""
    return get_html_template()

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
        home_team = request.get("home_team", "")
        away_team = request.get("away_team", "")
        game_date = request.get("game_date") or datetime.now().strftime("%Y-%m-%d")
        
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
    """Get prediction accuracy statistics from database"""
    try:
        # Get or create overall stats record
        from database import get_or_create_overall_stats
        stats = get_or_create_overall_stats(db)
        
        # Recalculate stats to ensure they're current
        update_accuracy_stats(db)
        db.refresh(stats)
        
        return {
            "success": True,
            "total_predictions": stats.total_predictions,
            "correct_predictions": stats.correct_predictions,
            "accuracy_percentage": round(stats.accuracy_percentage, 1),
            "last_7_days_accuracy": round(stats.last_7_days_accuracy or 0, 1),
            "last_30_days_accuracy": round(stats.last_30_days_accuracy or 0, 1),
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

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "NHL Daily Predictions",
        "openai_configured": client is not None,
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
    
    print("🌐 Starting server on http://127.0.0.1:8001")
    print("=" * 50)
    
    uvicorn.run(app, host="127.0.0.1", port=8001)
