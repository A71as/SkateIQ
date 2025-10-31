# 🏒 NHL Predictive Matchup Analyzer

AI-powered NHL game predictions using GPT-4 Advanced Reasoning to analyze team matchups and generate detailed prediction reports.

## Features

### 🤖 Advanced AI Analysis
- Uses GPT-4 Turbo for sophisticated reasoning about game outcomes
- Analyzes multiple factors: recent performance, home ice advantage, scoring trends
- Generates natural-language prediction reports in professional sports analyst style

### 📊 Real-Time NHL Data
- Fetches current season statistics from NHL Stats API
- Team records, goals, streaks, home/road performance
- Last 10 games, point percentages, goal differentials

### 📝 Comprehensive Reports Include:
1. **Executive Summary** - Quick matchup overview
2. **Key Matchup Factors** - Home ice, offense, defense, momentum
3. **Statistical Edge** - Which team has advantages in key metrics
4. **X-Factors** - Intangibles that could swing the game
5. **Prediction** - Winner, confidence level (1-10), expected score
6. **Betting Insight** - Value analysis and over/under considerations

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements_analyzer.txt
```

### 2. Get OpenAI API Key

1. Go to [OpenAI Platform](https://platform.openai.com/api-keys)
2. Create an account or sign in
3. Generate a new API key
4. Copy your API key

### 3. Configure Environment

Copy `.env.matchup` to `.env` and add your API key:

```bash
cp .env.matchup .env
```

Edit `.env`:
```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

## Usage

### Start the Server

```bash
python matchup_analyzer.py
```

The server will start on http://127.0.0.1:8001

### Access the Web Interface

1. Open http://127.0.0.1:8001 in your browser
2. Select the **Home Team** from the dropdown
3. Select the **Away Team** from the dropdown
4. Click **"🤖 Analyze Matchup with AI"**
5. Wait 10-15 seconds for AI analysis
6. View comprehensive prediction report!

## How It Works

### Data Collection
```
NHL Stats API → Team Statistics → AI Analysis
    ↓
- Current standings
- Win/loss records  
- Home/road splits
- Goals for/against
- Recent streaks
- Last 10 games
```

### AI Reasoning Process
```
GPT-4 Turbo analyzes:
    ├── Statistical advantages
    ├── Home ice impact
    ├── Momentum & streaks
    ├── Offensive firepower
    ├── Defensive strength
    └── Intangible factors
         ↓
    Prediction Report
```

## API Endpoints

### `POST /api/analyze`

Analyze a matchup and generate prediction.

**Request:**
```json
{
  "home_team": "Toronto Maple Leafs",
  "away_team": "Boston Bruins",
  "game_date": "2024-11-15" // optional
}
```

**Response:**
```json
{
  "success": true,
  "home_team": "Toronto Maple Leafs",
  "away_team": "Boston Bruins",
  "home_stats": {
    "wins": 12,
    "losses": 5,
    "points": 25,
    "home_record": "7-2-0",
    "goals_for": 45,
    "goals_against": 32,
    // ... more stats
  },
  "away_stats": { /* ... */ },
  "analysis": "**EXECUTIVE SUMMARY**\n\nThis matchup...",
  "generated_at": "2024-11-01T10:30:00"
}
```

### `GET /health`

Health check endpoint.

## Example Prediction Output

```markdown
**EXECUTIVE SUMMARY**

The Maple Leafs host the Bruins in what promises to be a high-intensity 
Atlantic Division showdown. Toronto's explosive offense faces Boston's 
stingy defensive structure, creating a classic clash of styles.

**KEY MATCHUP FACTORS**

Home Ice Advantage:
- Maple Leafs boast a 7-2-0 home record, feeding off Scotiabank Arena energy
- Historical success suggests 65% win probability at home vs Boston

Offensive Firepower:
- Toronto averaging 3.4 goals/game, 4th in NHL
- Boston's disciplined system allows only 2.5 goals/game
- Edge: Maple Leafs in raw scoring, Bruins in defensive efficiency

**PREDICTION**

Winner: Toronto Maple Leafs
Confidence: 7/10
Expected Score: 4-2 Maple Leafs

Key to Victory:
- Maple Leafs: Capitalize on power plays, maintain offensive pressure
- Bruins: Limit odd-man rushes, strong defensive-zone coverage
```

## Cost Considerations

### OpenAI API Pricing (GPT-4 Turbo)
- **Input**: ~$0.01 per 1K tokens
- **Output**: ~$0.03 per 1K tokens
- **Per Analysis**: ~$0.05-$0.10 (typical)

**Monthly Estimate:**
- 100 analyses = ~$5-10
- 500 analyses = ~$25-50

💡 **Tip**: Start with a small credit balance to test!

## Customization

### Change AI Model

Edit `matchup_analyzer.py`:

```python
# For faster/cheaper predictions
model="gpt-3.5-turbo"  # ~$0.001 per analysis

# For best quality (current)
model="gpt-4-turbo-preview"  # ~$0.05 per analysis

# For maximum capability
model="gpt-4"  # ~$0.10 per analysis
```

### Adjust Analysis Depth

Modify the `temperature` parameter:

```python
temperature=0.3  # More focused, consistent
temperature=0.7  # Balanced (default)
temperature=0.9  # More creative, varied
```

## Troubleshooting

### "OpenAI API key not configured"
✅ **Solution**: Add your API key to `.env` file

### "Failed to fetch team data"
✅ **Solution**: Check internet connection, NHL API may be temporarily down

### "Rate limit exceeded"
✅ **Solution**: You've hit OpenAI rate limits, wait a minute and try again

### Slow Analysis (>30 seconds)
✅ **Solution**: Normal for GPT-4. Switch to gpt-3.5-turbo for faster results

## Development

### Run with Auto-Reload

```bash
uvicorn matchup_analyzer:app --reload --port 8001
```

### Test API Directly

```bash
curl -X POST http://127.0.0.1:8001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "home_team": "Edmonton Oilers",
    "away_team": "Calgary Flames"
  }'
```

## Future Enhancements

- [ ] Add historical head-to-head analysis
- [ ] Include player injury reports
- [ ] Power play/penalty kill statistics
- [ ] Goaltender matchup analysis
- [ ] Save prediction history
- [ ] Compare AI predictions vs actual results
- [ ] Multi-game predictions
- [ ] Playoff probability calculator

## Tech Stack

- **Backend**: FastAPI (Python)
- **AI**: OpenAI GPT-4 Turbo
- **Data**: NHL Stats API (free, official)
- **Frontend**: Vanilla JavaScript + Modern CSS
- **Deployment**: Uvicorn ASGI server

## License

MIT License - Feel free to use and modify!

## Credits

- NHL data provided by NHL Stats API
- AI predictions powered by OpenAI GPT-4
- Built with ❤️ for hockey fans

---

**Enjoy predicting NHL games with AI! 🏒🤖**
