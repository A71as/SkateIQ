# 🏒 SkateIQ - NHL AI-Powered Predictions

**AI-powered NHL game predictions** using GPT-4o and real-time NHL data. Get win probabilities, confidence ratings, and reporter-style analysis with enhanced accuracy tracking and prediction locking.



![Version](https://img.shields.io/badge/version-2.0.0-blue)## Features

![Python](https://img.shields.io/badge/python-3.8+-green)

![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688)- **Daily NHL Schedule**: Automatically fetches today's games from the official NHL API

![License](https://img.shields.io/badge/license-MIT-orange)- **AI-Powered Analysis**: Uses GPT-4o to generate in-depth, reporter-style game previews

- **Real Player Data**: References actual team rosters, top forwards, and projected starting goalies

## ✨ Features- **Win Probabilities**: Data-driven predictions with confidence ratings (X/10)

- **Live Stats**: Current standings, recent form, home/road splits, and goal differentials

### 🎯 Core Predictions- **Beautiful UI**: Modern, responsive design with gradient backgrounds and smooth animations

- **Daily NHL Schedule**: Auto-fetches today's games from official NHL API

- **AI Analysis**: GPT-4o generates reporter-style game previews## Tech Stack

- **Win Probabilities**: Data-driven predictions with percentages (e.g., 52%-48%)

- **Confidence Ratings**: X/10 confidence score for each prediction- **Backend**: FastAPI (Python)

- **Real Player Data**: References actual rosters, top forwards, projected goalies- **AI**: OpenAI GPT-4o

- **Data Sources**: NHL Official API, team rosters, standings

### 📅 Advanced Features- **Frontend**: HTML/CSS/JavaScript (embedded)

- **Future Date Predictions**: View and predict games up to 7 days ahead- **Deployment**: Uvicorn ASGI server

- **Live Accuracy Tracking**: Real-time banner showing prediction success rate

- **Collapsible Analysis**: Clean UI with expandable detailed breakdowns## Installation

- **Persistent Storage**: JSON-based prediction history and accuracy stats

1. Clone the repository:

### 🎨 User Experience```bash

- **Ultra-Modern UI**: Apple-inspired design with glassmorphism effectsgit clone https://github.com/A71as/SkateIQ.git

- **Responsive Layout**: Works seamlessly on desktop, tablet, and mobilecd SkateIQ

- **Smooth Animations**: 0.3s transitions, elegant hover states```

- **Date Picker**: Intuitive calendar selector with smart constraints

2. Install dependencies:

## 🚀 Quick Start```bash

pip install fastapi uvicorn[standard] pydantic requests python-dotenv openai

### Prerequisites```

- Python 3.8 or higher

- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))3. Create a `.env` file with your OpenAI API key:

```

### InstallationOPENAI_API_KEY=your_api_key_here

```

1. **Clone the repository**

```bash## Usage

git clone https://github.com/A71as/SkateIQ.git

cd SkateIQRun the server:

``````bash

python nhl_daily_predictions.py

2. **Install dependencies**```

```bash

pip install -r requirements.txtOpen your browser to:

``````

http://127.0.0.1:8001

3. **Configure environment**```

Create a `.env` file:

```envClick "Get AI Prediction" on any matchup to see:

OPENAI_API_KEY=your_openai_api_key_here- Win probability percentages

```- Confidence rating (X/10)

- Reporter-style analysis with:

4. **Run the server**  - Game preview lede

```bash  - Key tactical factors

python nhl_daily_predictions.py  - Projected impact players (actual names)

```  - Projected starting goalies

  - Injuries/notes

5. **Open in browser**

```## Example Analysis

http://127.0.0.1:8001

``````

The Vegas Golden Knights host the Colorado Avalanche in what promises to be 

## 📖 Usagea thrilling encounter between two of the NHL's hottest teams...



### Getting Predictions- The Golden Knights have a strong 6-1-3 record in their last 10...

- At home, Vegas remains unbeaten in regulation (3-0-1)...

1. **Select a Date**: Use the date picker (today through +7 days)

2. **View Games**: Games load automatically for the selected date**Projected Impact Players**:

3. **Get Prediction**: Click "Get AI Prediction" on any matchupHome: Jack Eichel has been a playmaker recently...

4. **Expand Analysis**: Click "📊 Detailed Analysis" to see full breakdownAway: Ross Colton offering physical play and timely offensive contributions...

5. **Track Accuracy**: Watch live stats update after each prediction

**Projected Starting Goalies**:

### Example Analysis OutputHome: Adin Hill (projected)

Away: Mackenzie Blackwood (projected)

``````

Win Probability: VGK 52% - COL 48%

Confidence: 7/10## API Endpoints



📊 Detailed Analysis (Click to expand)- `GET /` - Main web interface

- `GET /api/todays-games` - Today's NHL schedule

The Vegas Golden Knights host the Colorado Avalanche in a battle - `POST /api/analyze` - Generate AI prediction for a matchup

of Western Conference powerhouses...- `GET /health` - Health check



**Current Form and Last-10 Trends:** ## Project Structure

Vegas at 6-1-3, Colorado 5-1-4, both riding strong momentum.

```

**Goal Differential:** SkateIQ/

Vegas +9 (37 GF, 28 GA), Colorado +11 (41 GF, 30 GA)├── nhl_daily_predictions.py  # Main app & AI logic

├── nhl_routes.py              # API endpoints

**Projected Impact Players:**├── nhl_html.py                # Frontend template

- Home: Jack Eichel - offensive catalyst with elite playmaking├── .env                       # Environment variables (not committed)

- Away: Ross Colton - aggressive forechecking, timely scoring├── .gitignore                 # Git ignore rules

└── README.md                  # This file

**Projected Starting Goalies:**```

- Home: Adin Hill (projected)

- Away: Mackenzie Blackwood (projected)## Credits

```

- NHL data from [NHL Official API](https://api-web.nhle.com/)

## 🛠️ Tech Stack- AI analysis powered by OpenAI GPT-4o

- Built by [A71as](https://github.com/A71as)

| Layer | Technology |

|-------|-----------|## License

| **Backend** | FastAPI (Python 3.8+) |

| **AI Engine** | OpenAI GPT-4o |MIT License - feel free to use and modify!

| **Data Source** | NHL Official API |

| **Storage** | JSON (predictions, accuracy) |---

| **Server** | Uvicorn ASGI |

| **Frontend** | HTML5, CSS3, Vanilla JS |**Note**: Requires an OpenAI API key. Get one at [platform.openai.com](https://platform.openai.com/)

| **Design** | Apple-inspired glassmorphism |

## 📡 API Endpoints

### Core Endpoints

#### `GET /`
Returns the main web interface with Apple-inspired UI

#### `GET /api/games/{date}`
Fetch games for specific date (YYYY-MM-DD format)
```json
{
  "success": true,
  "date": "2025-10-31",
  "games": [...],
  "count": 3
}
```

#### `POST /api/analyze`
Generate AI prediction for a matchup
```json
// Request
{
  "home_team": "Vegas Golden Knights",
  "away_team": "Colorado Avalanche",
  "game_date": "2025-10-31"
}

// Response
{
  "success": true,
  "home_prob": 52,
  "away_prob": 48,
  "confidence": 7,
  "analysis_text": "...",
  "home_stats": {...},
  "away_stats": {...}
}
```

#### `GET /api/accuracy`
Get prediction accuracy statistics
```json
{
  "success": true,
  "total_predictions": 10,
  "correct_predictions": 6,
  "accuracy_percentage": 60.0,
  "recent_predictions": 3
}
```

#### `POST /api/update-result`
Update prediction with actual game result
```json
{
  "home_team": "Vegas Golden Knights",
  "away_team": "Colorado Avalanche",
  "game_date": "2025-10-31",
  "winner": "home"  // or "away"
}
```

#### `GET /health`
Health check endpoint

## 📁 Project Structure

```
SkateIQ/
├── nhl_daily_predictions.py    # Main FastAPI app + AI logic
├── nhl_html.py                  # Frontend template (HTML/CSS/JS)
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (not in git)
├── .gitignore                   # Git ignore rules
├── FEATURES.md                  # Feature documentation
├── README.md                    # This file
└── data/
    └── predictions.json         # Stored predictions & accuracy
```

## 🎯 Accuracy Tracking

SkateIQ tracks all predictions and calculates accuracy over time:

- **Total Predictions**: Count of all generated predictions
- **Correct Predictions**: Predictions that matched actual outcomes
- **Accuracy Percentage**: Success rate (correct/total × 100)
- **Recent Predictions**: Count from last 7 days

Update results manually via `/api/update-result` or automate with game scrapers.

## 💰 Cost Considerations

### OpenAI API Usage (GPT-4o)
- **Input**: ~$2.50 per 1M tokens
- **Output**: ~$10.00 per 1M tokens
- **Per Prediction**: ~$0.02-$0.05 (typical)

**Monthly Estimates:**
- 100 predictions: $2-5
- 500 predictions: $10-25
- 1,000 predictions: $20-50

**6-hour caching** reduces redundant API calls for same matchup.

## 🔮 Roadmap

### Coming Soon
- [ ] User authentication & accounts
- [ ] PostgreSQL database migration
- [ ] Automated result scraping from NHL API
- [ ] Historical accuracy charts & visualizations
- [ ] Team-specific accuracy breakdowns
- [ ] Email notifications for daily picks
- [ ] Betting odds integration
- [ ] Mobile apps (iOS/Android)

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Credits

- **NHL Data**: [NHL Official API](https://api-web.nhle.com/)
- **AI Engine**: OpenAI GPT-4o
- **Design Inspiration**: Apple's design language
- **Developer**: [A71as](https://github.com/A71as)

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/A71as/SkateIQ/issues)
- **Discussions**: [GitHub Discussions](https://github.com/A71as/SkateIQ/discussions)

---

**Built with ❤️ for NHL fans and sports analytics enthusiasts**

*Requires an OpenAI API key. Get yours at [platform.openai.com](https://platform.openai.com/)*
