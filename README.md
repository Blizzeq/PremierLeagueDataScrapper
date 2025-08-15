# FPL Data Collector

A comprehensive Python tool for collecting **ALL raw data** from the Fantasy Premier League (FPL) API. This tool fetches complete, unprocessed data including all 101 player attributes, fixtures, teams, and gameweek information - perfect for AI analysis and decision-making.

## Features

- **Complete Data Collection**: All 101 player attributes, fixtures, teams, and gameweeks
- **Error Handling & Retry Logic**: Automatic retry for failed API calls
- **Data Validation**: Validates completeness of collected data
- **Command-Line Arguments**: Flexible control via CLI options
- **Data Comparison Tool**: Compare data between different collection dates
- **Verbose Mode**: Detailed output for debugging
- **Configurable Player Histories**: Choose how many player histories to fetch
- **Date-Organized Storage**: Automatic organization by collection date

## 🎯 Purpose

This tool is designed for FPL managers who want to:

- Get **complete raw data** without any analysis or filtering
- Feed data directly to AI models (ChatGPT, Claude, etc.) for squad optimization
- Access all 101 player attributes available in the FPL API
- Track price changes, injuries, and transfers
- Analyze fixtures and team performance

## 📊 What Data is Collected?

### Players (685 total, 101 attributes each)

- **Basic Info**: Name, team, position, price
- **Performance**: Points, minutes, goals, assists, clean sheets
- **Advanced Stats**: xG, xA, xGI, xGC (expected metrics)
- **Defensive**: Tackles, recoveries, clearances, blocks, interceptions
- **Per 90 Stats**: All metrics calculated per 90 minutes
- **Rankings**: Position in every statistical category
- **Ownership**: Selection %, transfers in/out
- **Set Pieces**: Penalty, corner, and free-kick order
- **Injury Status**: Availability and chance of playing
- **Value Metrics**: Form, value season, price changes
- **Meta Data**: Birth date, squad number, Opta code

### Fixtures (380 total)

- Match results and scores
- Upcoming fixtures with kickoff times
- Fixture difficulty ratings (FDR)
- Home/Away designations

### Teams (20 total)

- Team strengths (attack/defense, home/away)
- Season statistics
- Goals scored/conceded
- League position and form

### Gameweeks (38 total)

- Deadlines and status
- Average scores
- Most selected/captained players
- Chip usage statistics

### Player Histories

- Match-by-match performance data
- Historical price changes
- Upcoming fixture difficulty

## 🚀 Quick Start

### Prerequisites

- Python 3.6 or higher
- Internet connection

### Installation

1. Clone or download this repository:

```bash
git clone https://github.com/yourusername/PremierLeague.git
cd PremierLeague
```

2. Install required packages:

```bash
pip install requests
```

That's it! No complex dependencies needed.

### Basic Usage

Run the collector with options:

```bash
# Basic usage
python fpl_data_collector.py

# With verbose output
python fpl_data_collector.py -v

# Fetch more player histories (default is 100)
python fpl_data_collector.py -p 200

# Save to custom directory
python fpl_data_collector.py -o my_data

# Validate existing data only
python fpl_data_collector.py --validate-only
```

Compare data between dates:

```bash
# Interactive mode
python compare_data.py

# Direct comparison
python compare_data.py 2024-08-15 2024-08-16
```

The scripts will:

1. Connect to the FPL API
2. Fetch all available data (takes ~30 seconds)
3. Save data in date-organized folders: `data/yyyy-mm-dd/`
4. Validate data completeness
5. Generate validation report

## 📁 Output Files

The collector creates a folder with today's date (e.g., `data/2024-08-15/`) and saves three files with timestamps:

### Example Output Structure:
```
data/
├── 2024-08-15/
│   ├── fpl_data_143022.json      # Complete JSON data
│   ├── fpl_players_143022.csv    # All players in CSV
│   └── fpl_report_143022.txt     # Human-readable report
├── 2024-08-16/
│   ├── fpl_data_091530.json
│   ├── fpl_players_091530.csv
│   └── fpl_report_091530.txt
└── 2024-08-17/
    └── ...
```

### File Contents:

1. **`fpl_data_HHMMSS.json`** - Complete JSON dump with all raw data from the API
2. **`fpl_players_HHMMSS.csv`** - CSV file with all 685 players and their 101 attributes
3. **`fpl_report_HHMMSS.txt`** - Human-readable text report organized in sections
4. **`validation_HHMMSS.json`** - Data validation report with completeness checks

## 🤖 Using with AI (ChatGPT, Claude, etc.)

### Optimal Workflow

1. **Run the collector** after gameweek ends (usually Tuesday morning):

```bash
python fpl_data_collector.py
```

2. **Open the text report** from the `data/` folder

3. **Copy the entire report** (or relevant sections)

4. **Paste into your AI assistant** with a prompt like:

```
Here is my current FPL squad:
[List your 15 players]

I have X free transfers and Y.Y million in the bank.

Based on the data provided:
1. Who should I transfer in/out?
2. Who should be my captain for the next gameweek?
3. Are any of my players injured or at risk?
4. Which players have the best fixtures coming up?
5. Who are the best differential picks with low ownership?
```

### Tips for AI Analysis

- **For transfers**: Focus on the PERFORMANCE, FORM, and FIXTURES sections
- **For captain choices**: Look at ATTACKING stats and upcoming fixtures
- **For differentials**: Check players with low ownership but high form
- **For price changes**: Monitor transfers in/out in current gameweek

## 📋 Data Structure

### JSON Structure

```json
{
  "players": [...],        // 685 players with 101 fields each
  "teams": [...],          // 20 teams
  "fixtures": [...],       // 380 fixtures
  "gameweeks": [...],      // 38 gameweeks
  "live_gameweek": {...},  // Current GW live data
  "player_histories": {...}, // Top 100 players' history
  "team_stats": {...},     // Calculated team statistics
  "next_5_gameweeks": [...] // Upcoming fixtures
}
```

### Player Fields (101 total)

<details>
<summary>Click to see all 101 player fields</summary>

1. **Identification**: id, code, first_name, second_name, web_name
2. **Team & Position**: team, team_code, element_type, squad_number
3. **Pricing**: now_cost, cost_change_event, cost_change_start
4. **Points & Form**: total_points, points_per_game, form, event_points
5. **Playing Time**: minutes, starts, starts_per_90
6. **Attacking**: goals_scored, assists, expected_goals, expected_assists
7. **Defensive**: clean_sheets, goals_conceded, saves, tackles, recoveries
8. **Discipline**: yellow_cards, red_cards, own_goals
9. **Penalties**: penalties_scored, penalties_saved, penalties_missed
10. **Set Pieces**: corners_order, freekicks_order, penalties_order
11. **ICT Index**: influence, creativity, threat, ict_index
12. **Rankings**: All statistical rankings (price, form, points, etc.)
13. **Ownership**: selected_by_percent, transfers_in, transfers_out
14. **Availability**: status, chance_of_playing_this_round, chance_of_playing_next_round
15. **Value**: value_form, value_season, ep_this, ep_next
16. **Meta**: birth_date, region, photo, special, removed

</details>

## 🔄 When to Run

### After Each Gameweek (Recommended)

- **Tuesday morning**: After all matches are complete
- Gets final scores, bonus points, and price changes
- Most accurate injury updates

### Before Deadline

- **Friday afternoon**: Before the gameweek deadline
- Latest injury news from press conferences
- Final price predictions

### During Gameweek

- Live data available but not recommended for decisions
- Better to wait for final data

## ⚙️ Configuration

The script uses sensible defaults, but you can modify:

- **Output directory**: Change `Path("data")` in the code
- **Number of player histories**: Modify the `[:100]` slice (line ~70)
- **API timeouts**: Adjust if you have slow connection

## 🛠️ Troubleshooting

### Common Issues

**"Connection Error"**

- Check your internet connection
- FPL API might be temporarily down (rare)
- Try again in a few minutes

**"No current gameweek"**

- Normal between seasons
- Script will use GW1 as default

**Large file sizes**

- JSON file can be 5-10 MB
- Text report can be 2-5 MB
- This is normal with complete data

## 📈 Advanced Usage

### Filtering Data

```python
# Example: Get only players from a specific team
import json

with open('data/fpl_data_TIMESTAMP.json', 'r') as f:
    data = json.load(f)

arsenal_players = [p for p in data['players'] if p['team'] == 1]
```

### Automated Collection

Create a simple scheduler (cron on Linux/Mac, Task Scheduler on Windows):

```bash
# Run every Tuesday at 10 AM
0 10 * * 2 /usr/bin/python3 /path/to/fpl_data_collector.py
```

---

**Author: Jakub Krasuski**
