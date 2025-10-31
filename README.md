# 🏒 SkateIQ - NHL Daily Matchup Predictions

AI-powered NHL game predictions using GPT-4o and real-time NHL data. Get win probabilities, confidence ratings, and reporter-style analysis featuring actual player projections and matchup insights.

## Features

- **Daily NHL Schedule**: Automatically fetches today's games from the official NHL API
- **AI-Powered Analysis**: Uses GPT-4o to generate in-depth, reporter-style game previews
- **Real Player Data**: References actual team rosters, top forwards, and projected starting goalies
- **Win Probabilities**: Data-driven predictions with confidence ratings (X/10)
- **Live Stats**: Current standings, recent form, home/road splits, and goal differentials
- **Beautiful UI**: Modern, responsive design with gradient backgrounds and smooth animations

## Tech Stack

- **Backend**: FastAPI (Python)
- **AI**: OpenAI GPT-4o
- **Data Sources**: NHL Official API, team rosters, standings
- **Frontend**: HTML/CSS/JavaScript (embedded)
- **Deployment**: Uvicorn ASGI server

## Installation

1. Clone the repository:
```bash
git clone https://github.com/A71as/SkateIQ.git
cd SkateIQ
```

2. Install dependencies:
```bash
pip install fastapi uvicorn[standard] pydantic requests python-dotenv openai
```

3. Create a `.env` file with your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

Run the server:
```bash
python nhl_daily_predictions.py
```

Open your browser to:
```
http://127.0.0.1:8001
```

Click "Get AI Prediction" on any matchup to see:
- Win probability percentages
- Confidence rating (X/10)
- Reporter-style analysis with:
  - Game preview lede
  - Key tactical factors
  - Projected impact players (actual names)
  - Projected starting goalies
  - Injuries/notes

## Example Analysis

```
The Vegas Golden Knights host the Colorado Avalanche in what promises to be 
a thrilling encounter between two of the NHL's hottest teams...

- The Golden Knights have a strong 6-1-3 record in their last 10...
- At home, Vegas remains unbeaten in regulation (3-0-1)...

**Projected Impact Players**:
Home: Jack Eichel has been a playmaker recently...
Away: Ross Colton offering physical play and timely offensive contributions...

**Projected Starting Goalies**:
Home: Adin Hill (projected)
Away: Mackenzie Blackwood (projected)
```

## API Endpoints

- `GET /` - Main web interface
- `GET /api/todays-games` - Today's NHL schedule
- `POST /api/analyze` - Generate AI prediction for a matchup
- `GET /health` - Health check

## Project Structure

```
SkateIQ/
├── nhl_daily_predictions.py  # Main app & AI logic
├── nhl_routes.py              # API endpoints
├── nhl_html.py                # Frontend template
├── .env                       # Environment variables (not committed)
├── .gitignore                 # Git ignore rules
└── README.md                  # This file
```

## Credits

- NHL data from [NHL Official API](https://api-web.nhle.com/)
- AI analysis powered by OpenAI GPT-4o
- Built by [A71as](https://github.com/A71as)

## License

MIT License - feel free to use and modify!

---

**Note**: Requires an OpenAI API key. Get one at [platform.openai.com](https://platform.openai.com/)
