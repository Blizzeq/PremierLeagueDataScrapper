#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FPL RAW DATA COLLECTOR
Fetches ALL raw data from Fantasy Premier League API
With error handling, retry logic, validation, and command-line arguments
"""

import requests
import json
import csv
import time
import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class FPLDataCollector:
    """Collects ALL raw data from FPL API with error handling and validation"""
    
    BASE_URL = "https://fantasy.premierleague.com/api"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds
    
    def __init__(self, verbose: bool = False, top_players: int = 100):
        self.session = requests.Session()
        self.data = {}
        self.verbose = verbose
        self.top_players = top_players
        
    def _api_call(self, url: str, description: str = "") -> Optional[Dict]:
        """Make API call with retry logic"""
        for attempt in range(self.MAX_RETRIES):
            try:
                if self.verbose and attempt > 0:
                    print(f"  Retry attempt {attempt + 1}/{self.MAX_RETRIES}...")
                    
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == self.MAX_RETRIES - 1:
                    print(f"[ERROR] Failed to fetch {description}: {str(e)}")
                    return None
                time.sleep(self.RETRY_DELAY)
                
        return None
        
    def collect_all_data(self) -> Dict[str, Any]:
        """Fetches ALL available data from FPL with error handling"""
        
        print("=" * 60)
        print("FPL DATA COLLECTION")
        print("=" * 60)
        
        # 1. MAIN DATA - all players, teams, gameweeks
        print("\n[1/6] Fetching players, teams, gameweeks...")
        url = f"{self.BASE_URL}/bootstrap-static/"
        bootstrap = self._api_call(url, "bootstrap data")
        
        if not bootstrap:
            print("[CRITICAL] Failed to fetch main data. Aborting.")
            return {}
            
        self.data['players'] = bootstrap['elements']  # ALL 685 PLAYERS
        self.data['teams'] = bootstrap['teams']  # ALL 20 TEAMS
        self.data['gameweeks'] = bootstrap['events']  # ALL 38 GAMEWEEKS
        self.data['positions'] = bootstrap['element_types']  # POSITIONS
        self.data['game_settings'] = bootstrap.get('game_settings', {})
        self.data['phases'] = bootstrap.get('phases', [])
        self.data['chips'] = bootstrap.get('chips', [])
        
        print(f"[OK] Fetched {len(self.data['players'])} players")
        print(f"[OK] Fetched {len(self.data['teams'])} teams")
        print(f"[OK] Fetched {len(self.data['gameweeks'])} gameweeks")
        
        # Data validation
        if len(self.data['players']) < 600:
            print(f"[WARNING] Only {len(self.data['players'])} players found (expected ~685)")
        
        # Find current gameweek
        current_gw = None
        for gw in self.data['gameweeks']:
            if gw.get('is_current'):
                current_gw = gw['id']
                break
            elif gw.get('is_next'):
                current_gw = gw['id']
                break
        if not current_gw:
            current_gw = 1
            
        print(f"[OK] Current/Next gameweek: GW{current_gw}")
        
        # 2. ALL FIXTURES (past and future)
        print("\n[2/6] Fetching all fixtures...")
        url = f"{self.BASE_URL}/fixtures/"
        fixtures_data = self._api_call(url, "fixtures")
        
        if fixtures_data:
            self.data['fixtures'] = fixtures_data
            finished = len([f for f in self.data['fixtures'] if f['finished']])
            upcoming = len([f for f in self.data['fixtures'] if not f['finished']])
            print(f"[OK] Fetched {len(self.data['fixtures'])} fixtures ({finished} finished, {upcoming} upcoming)")
        else:
            self.data['fixtures'] = []
            print("[WARNING] Failed to fetch fixtures")
        
        # 3. LIVE DATA FROM CURRENT GAMEWEEK
        print(f"\n[3/6] Fetching live data from GW{current_gw}...")
        url = f"{self.BASE_URL}/event/{current_gw}/live/"
        live_data = self._api_call(url, f"GW{current_gw} live data")
        
        if live_data:
            self.data['live_gameweek'] = live_data
            print(f"[OK] Fetched live data")
        else:
            self.data['live_gameweek'] = {}
            print("[WARNING] No live data available")
        
        # 4. PLAYER HISTORIES (configurable top N by ownership)
        print(f"\n[4/6] Fetching player histories (top {self.top_players} by ownership)...")
        self.data['player_histories'] = {}
        
        # Sort players by ownership and get top N
        sorted_players = sorted(self.data['players'], 
                              key=lambda x: float(x['selected_by_percent']), 
                              reverse=True)[:self.top_players]
        
        successful_histories = 0
        failed_histories = []
        
        for i, player in enumerate(sorted_players):
            if i % 20 == 0:
                print(f"  Progress: {i}/{self.top_players}...")
                
            url = f"{self.BASE_URL}/element-summary/{player['id']}/"
            player_data = self._api_call(url, f"player {player['web_name']}")
            
            if player_data:
                self.data['player_histories'][player['id']] = player_data
                successful_histories += 1
            else:
                failed_histories.append(player['web_name'])
        
        print(f"[OK] Fetched history for {successful_histories}/{self.top_players} players")
        if failed_histories and self.verbose:
            print(f"[INFO] Failed to fetch: {', '.join(failed_histories[:5])}...")
        
        # 5. TEAM STATISTICS FROM CURRENT SEASON
        print("\n[5/6] Calculating team statistics...")
        self.data['team_stats'] = {}
        for team in self.data['teams']:
            team_id = team['id']
            # Calculate stats based on fixtures
            home_games = [f for f in self.data['fixtures'] 
                         if f['team_h'] == team_id and f['finished']]
            away_games = [f for f in self.data['fixtures'] 
                         if f['team_a'] == team_id and f['finished']]
            
            self.data['team_stats'][team_id] = {
                'name': team['name'],
                'short_name': team['short_name'],
                'games_played': len(home_games) + len(away_games),
                'home_games': len(home_games),
                'away_games': len(away_games),
                'total_goals_scored': sum(f['team_h_score'] or 0 for f in home_games) + 
                                     sum(f['team_a_score'] or 0 for f in away_games),
                'total_goals_conceded': sum(f['team_a_score'] or 0 for f in home_games) + 
                                       sum(f['team_h_score'] or 0 for f in away_games),
            }
        
        print(f"[OK] Calculated statistics for {len(self.data['team_stats'])} teams")
        
        # 6. NEXT 5 GAMEWEEKS FIXTURES
        print("\n[6/6] Preparing next 5 gameweeks schedule...")
        next_5_gws = []
        for gw_num in range(current_gw, min(current_gw + 5, 39)):
            gw_fixtures = [f for f in self.data['fixtures'] if f['event'] == gw_num]
            next_5_gws.append({
                'gameweek': gw_num,
                'fixtures': gw_fixtures
            })
        self.data['next_5_gameweeks'] = next_5_gws
        
        print(f"[OK] Prepared fixture schedule")
        
        # Add metadata
        self.data['metadata'] = {
            'collection_time': datetime.now().isoformat(),
            'player_count': len(self.data['players']),
            'fixture_count': len(self.data['fixtures']),
            'histories_collected': successful_histories,
            'current_gameweek': current_gw
        }
        
        return self.data
    
    def validate_data(self) -> Dict[str, Any]:
        """Validate collected data completeness"""
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': []
        }
        
        # Check player count
        if len(self.data.get('players', [])) < 600:
            validation['warnings'].append(f"Low player count: {len(self.data.get('players', []))}")
            
        # Check fixtures
        if len(self.data.get('fixtures', [])) < 380:
            validation['warnings'].append(f"Low fixture count: {len(self.data.get('fixtures', []))}")
            
        # Check teams
        if len(self.data.get('teams', [])) != 20:
            validation['errors'].append(f"Invalid team count: {len(self.data.get('teams', []))}")
            validation['is_valid'] = False
            
        # Check player fields
        if self.data.get('players'):
            sample_player = self.data['players'][0]
            expected_fields = ['id', 'web_name', 'team', 'now_cost', 'total_points']
            missing_fields = [f for f in expected_fields if f not in sample_player]
            if missing_fields:
                validation['warnings'].append(f"Missing player fields: {missing_fields}")
                
        return validation
    
    def save_data(self, data: Optional[Dict] = None, output_dir: str = "data") -> Dict[str, str]:
        """Saves ALL data to files with validation"""
        
        if data is None:
            data = self.data
            
        # Validate data before saving
        validation = self.validate_data()
        if not validation['is_valid']:
            print("\n[ERROR] Data validation failed:")
            for error in validation['errors']:
                print(f"  - {error}")
            return {}
            
        if validation['warnings']:
            print("\n[WARNING] Data validation warnings:")
            for warning in validation['warnings']:
                print(f"  - {warning}")
            
        # Create directory with date format: data/yyyy-mm-dd
        date_str = datetime.now().strftime('%Y-%m-%d')
        time_str = datetime.now().strftime('%H%M%S')
        
        # Create data directory with date subdirectory
        save_dir = Path(output_dir) / date_str
        save_dir.mkdir(parents=True, exist_ok=True)
        
        print("\n" + "=" * 60)
        print("SAVING DATA")
        print("=" * 60)
        
        files_saved = {}
        
        # 1. Full JSON data
        filename = save_dir / f"fpl_data_{time_str}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n[OK] Full JSON data: {filename}")
            files_saved['json'] = str(filename)
        except Exception as e:
            print(f"[ERROR] Failed to save JSON: {e}")
        
        # 2. Players CSV for easy analysis
        players_csv = save_dir / f"fpl_players_{time_str}.csv"
        try:
            with open(players_csv, 'w', newline='', encoding='utf-8') as f:
                if data['players']:
                    writer = csv.DictWriter(f, fieldnames=data['players'][0].keys())
                    writer.writeheader()
                    writer.writerows(data['players'])
            print(f"[OK] Players CSV: {players_csv}")
            files_saved['csv'] = str(players_csv)
        except Exception as e:
            print(f"[ERROR] Failed to save CSV: {e}")
        
        # 3. Comprehensive text report with ALL data
        report_file = save_dir / f"fpl_report_{time_str}.txt"
        try:
            self._generate_text_report(data, report_file)
            print(f"[OK] Full text report: {report_file}")
            files_saved['report'] = str(report_file)
        except Exception as e:
            print(f"[ERROR] Failed to save report: {e}")
        
        # 4. Save validation report
        validation_file = save_dir / f"validation_{time_str}.json"
        try:
            with open(validation_file, 'w', encoding='utf-8') as f:
                json.dump(validation, f, indent=2)
            print(f"[OK] Validation report: {validation_file}")
            files_saved['validation'] = str(validation_file)
        except Exception as e:
            print(f"[ERROR] Failed to save validation: {e}")
        
        return files_saved
    
    def _generate_text_report(self, data: Dict, filename: Path) -> None:
        """Generates comprehensive text report with ALL 101 player fields"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("FANTASY PREMIER LEAGUE - COMPLETE RAW DATA\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            
            # Add data summary
            f.write("DATA SUMMARY\n")
            f.write("-" * 80 + "\n")
            f.write(f"Players: {len(data.get('players', []))}\n")
            f.write(f"Teams: {len(data.get('teams', []))}\n")
            f.write(f"Fixtures: {len(data.get('fixtures', []))}\n")
            f.write(f"Player Histories: {len(data.get('player_histories', {}))}\n")
            f.write("\n")
            
            # SECTION 1: ALL PLAYERS WITH ALL 101 FIELDS
            f.write("SECTION 1: ALL PLAYERS - COMPLETE DATA\n")
            f.write("-" * 80 + "\n")
            
            # Map team IDs to names for readability
            team_names = {t['id']: t['name'] for t in data.get('teams', [])}
            position_names = {p['id']: p['singular_name_short'] for p in data.get('positions', [])}
            
            for player in data.get('players', []):
                f.write(f"\n{'='*40}\n")
                f.write(f"ID: {player['id']} | {player['first_name']} {player['second_name']} ({player['web_name']})\n")
                f.write(f"Team: {team_names.get(player['team'], 'Unknown')} | Position: {position_names.get(player['element_type'], 'Unknown')}\n")
                f.write(f"-"*40 + "\n")
                
                # PRICING
                f.write("PRICING:\n")
                f.write(f"  Current: GBP{player['now_cost']/10}m | GW Change: GBP{player['cost_change_event']/10}m | Total Change: GBP{player['cost_change_start']/10}m\n")
                
                # OWNERSHIP & TRANSFERS
                f.write("OWNERSHIP & TRANSFERS:\n")
                f.write(f"  Selected by: {player['selected_by_percent']}% | Transfers In (GW): {player['transfers_in_event']} | Out: {player['transfers_out_event']}\n")
                f.write(f"  Total Transfers In: {player['transfers_in']} | Out: {player['transfers_out']}\n")
                
                # PERFORMANCE
                f.write("PERFORMANCE:\n")
                f.write(f"  Total Points: {player['total_points']} | PPG: {player['points_per_game']} | Form: {player['form']}\n")
                f.write(f"  Minutes: {player['minutes']} | Starts: {player.get('starts', 0)} | Starts/90: {player.get('starts_per_90', 0)}\n")
                
                # ATTACKING STATS
                f.write("ATTACKING:\n")
                f.write(f"  Goals: {player['goals_scored']} | Assists: {player['assists']} | Bonus: {player['bonus']} | BPS: {player['bps']}\n")
                f.write(f"  xG: {player.get('expected_goals', 0)} | xA: {player.get('expected_assists', 0)} | xGI: {player.get('expected_goal_involvements', 0)}\n")
                f.write(f"  xG/90: {player.get('expected_goals_per_90', 0)} | xA/90: {player.get('expected_assists_per_90', 0)} | xGI/90: {player.get('expected_goal_involvements_per_90', 0)}\n")
                
                # DEFENSIVE STATS
                f.write("DEFENSIVE:\n")
                f.write(f"  Clean Sheets: {player['clean_sheets']} | CS/90: {player.get('clean_sheets_per_90', 0)}\n")
                f.write(f"  Goals Conceded: {player['goals_conceded']} | GC/90: {player.get('goals_conceded_per_90', 0)}\n")
                f.write(f"  xGC: {player.get('expected_goals_conceded', 0)} | xGC/90: {player.get('expected_goals_conceded_per_90', 0)}\n")
                f.write(f"  Saves: {player['saves']} | Saves/90: {player.get('saves_per_90', 0)}\n")
                f.write(f"  Clearances/Blocks/Int: {player.get('clearances_blocks_interceptions', 0)}\n")
                f.write(f"  Recoveries: {player.get('recoveries', 0)} | Tackles: {player.get('tackles', 0)}\n")
                f.write(f"  Defensive Contribution: {player.get('defensive_contribution', 0)} | DC/90: {player.get('defensive_contribution_per_90', 0)}\n")
                
                # DISCIPLINE & PENALTIES
                f.write("DISCIPLINE & SET PIECES:\n")
                f.write(f"  Yellow Cards: {player['yellow_cards']} | Red Cards: {player['red_cards']} | Own Goals: {player.get('own_goals', 0)}\n")
                f.write(f"  Penalties Scored: {player.get('penalties_scored', 0)} | Saved: {player.get('penalties_saved', 0)} | Missed: {player.get('penalties_missed', 0)}\n")
                f.write(f"  Penalties Order: {player.get('penalties_order', 'N/A')} | Text: {player.get('penalties_text', '')}\n")
                f.write(f"  Corners/IFK Order: {player.get('corners_and_indirect_freekicks_order', 'N/A')} | Text: {player.get('corners_and_indirect_freekicks_text', '')}\n")
                f.write(f"  Direct FK Order: {player.get('direct_freekicks_order', 'N/A')} | Text: {player.get('direct_freekicks_text', '')}\n")
                
                # ICT INDEX
                f.write("ICT INDEX:\n")
                f.write(f"  Influence: {player['influence']} | Creativity: {player['creativity']} | Threat: {player['threat']} | ICT: {player['ict_index']}\n")
                
                # RANKINGS
                f.write("RANKINGS:\n")
                f.write(f"  Price: {player.get('now_cost_rank', 'N/A')} | Form: {player.get('form_rank', 'N/A')} | PPG: {player.get('points_per_game_rank', 'N/A')}\n")
                f.write(f"  Selected: {player.get('selected_rank', 'N/A')} | ICT: {player.get('ict_index_rank', 'N/A')}\n")
                f.write(f"  Influence: {player.get('influence_rank', 'N/A')} | Creativity: {player.get('creativity_rank', 'N/A')} | Threat: {player.get('threat_rank', 'N/A')}\n")
                
                # STATUS & AVAILABILITY
                f.write("STATUS:\n")
                f.write(f"  Status: {player['status']} | Chance This GW: {player['chance_of_playing_this_round']}% | Next GW: {player['chance_of_playing_next_round']}%\n")
                if player['news']:
                    f.write(f"  News: {player['news']} (Added: {player['news_added']})\n")
                
                # VALUE & EXPECTATIONS
                f.write("VALUE & PROJECTIONS:\n")
                f.write(f"  Value Form: {player['value_form']} | Value Season: {player['value_season']}\n")
                f.write(f"  EP Next: {player['ep_next']} | EP This: {player['ep_this']}\n")
                f.write(f"  Dreamteam Count: {player['dreamteam_count']} | In Dreamteam: {player['in_dreamteam']}\n")
                
                # META DATA
                f.write("META:\n")
                f.write(f"  Birth Date: {player.get('birth_date', 'N/A')} | Squad Number: {player.get('squad_number', 'N/A')}\n")
                f.write(f"  Team Join: {player.get('team_join_date', 'N/A')} | Region: {player.get('region', 'N/A')}\n")
                f.write(f"  Opta Code: {player.get('opta_code', 'N/A')} | Photo: {player.get('photo', 'N/A')}\n")
                f.write(f"  Special: {player.get('special', False)} | Removed: {player.get('removed', False)}\n")
                f.write(f"  Can Transact: {player.get('can_transact', True)} | Can Select: {player.get('can_select', True)}\n")
                
            # SECTION 2: ALL FIXTURES
            f.write("\n\n" + "="*80 + "\n")
            f.write("SECTION 2: ALL FIXTURES\n")
            f.write("-" * 80 + "\n")
            
            team_shorts = {t['id']: t['short_name'] for t in data.get('teams', [])}
            
            for fixture in data.get('fixtures', []):
                f.write(f"\nGW{fixture['event']}: {team_names.get(fixture['team_h'], 'Unknown')} vs {team_names.get(fixture['team_a'], 'Unknown')}\n")
                f.write(f"  ID: {fixture['id']} | {team_shorts.get(fixture['team_h'], '???')} vs {team_shorts.get(fixture['team_a'], '???')}\n")
                
                if fixture['finished']:
                    f.write(f"  RESULT: {fixture['team_h_score']} - {fixture['team_a_score']}\n")
                else:
                    f.write(f"  Kickoff: {fixture['kickoff_time']}\n")
                    
                f.write(f"  Difficulty - Home: {fixture['team_h_difficulty']} | Away: {fixture['team_a_difficulty']}\n")
            
            # SECTION 3: TEAMS
            f.write("\n\n" + "="*80 + "\n")
            f.write("SECTION 3: TEAMS\n")
            f.write("-" * 80 + "\n")
            
            for team in data.get('teams', []):
                f.write(f"\n{team['name']} ({team['short_name']})\n")
                f.write(f"  ID: {team['id']} | Code: {team['code']}\n")
                f.write(f"  Strength - Attack: {team.get('strength_attack_home', 0)}H/{team.get('strength_attack_away', 0)}A\n")
                f.write(f"  Strength - Defence: {team.get('strength_defence_home', 0)}H/{team.get('strength_defence_away', 0)}A\n")
                f.write(f"  Strength - Overall: {team.get('strength_overall_home', 0)}H/{team.get('strength_overall_away', 0)}A\n")
                
                if team['id'] in data.get('team_stats', {}):
                    stats = data['team_stats'][team['id']]
                    f.write(f"  Season Stats: {stats['games_played']} games | {stats['total_goals_scored']} GF | {stats['total_goals_conceded']} GA\n")
            
            # SECTION 4: GAMEWEEKS
            f.write("\n\n" + "="*80 + "\n")
            f.write("SECTION 4: GAMEWEEKS\n")
            f.write("-" * 80 + "\n")
            
            for gw in data.get('gameweeks', []):
                status = []
                if gw['finished']: status.append('Finished')
                if gw.get('is_current'): status.append('Current')
                if gw.get('is_next'): status.append('Next')
                
                f.write(f"\nGW{gw['id']}: {gw['name']} [{', '.join(status) if status else 'Future'}]\n")
                f.write(f"  Deadline: {gw['deadline_time']}\n")
                if gw.get('average_entry_score'):
                    f.write(f"  Average Score: {gw['average_entry_score']} | Highest: {gw.get('highest_score', 'N/A')}\n")
                if gw.get('most_selected'):
                    f.write(f"  Most Selected: {gw['most_selected']} | Most Captained: {gw.get('most_captained', 'N/A')}\n")

def main():
    """Main function with command-line arguments"""
    
    parser = argparse.ArgumentParser(description='FPL Data Collector')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Enable verbose output')
    parser.add_argument('-o', '--output', default='data', 
                       help='Output directory (default: data)')
    parser.add_argument('-p', '--players', type=int, default=100,
                       help='Number of player histories to fetch (default: 100)')
    parser.add_argument('--validate-only', action='store_true',
                       help='Only validate existing data without fetching new')
    
    args = parser.parse_args()
    
    collector = FPLDataCollector(verbose=args.verbose, top_players=args.players)
    
    if args.validate_only:
        # Load most recent data and validate
        data_dir = Path(args.output)
        if not data_dir.exists():
            print("[ERROR] No data directory found")
            return
            
        # Find most recent date folder
        date_folders = sorted([d for d in data_dir.iterdir() if d.is_dir()], reverse=True)
        if not date_folders:
            print("[ERROR] No data folders found")
            return
            
        latest_folder = date_folders[0]
        json_files = list(latest_folder.glob("fpl_data_*.json"))
        if not json_files:
            print(f"[ERROR] No data files found in {latest_folder}")
            return
            
        latest_file = sorted(json_files, reverse=True)[0]
        print(f"Validating: {latest_file}")
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            collector.data = json.load(f)
            
        validation = collector.validate_data()
        print("\nValidation Results:")
        print(f"Valid: {validation['is_valid']}")
        if validation['errors']:
            print("Errors:")
            for error in validation['errors']:
                print(f"  - {error}")
        if validation['warnings']:
            print("Warnings:")
            for warning in validation['warnings']:
                print(f"  - {warning}")
    else:
        # Fetch ALL data
        all_data = collector.collect_all_data()
        
        if not all_data:
            print("\n[CRITICAL] No data collected. Exiting.")
            return
        
        # Save data
        files = collector.save_data(all_data, args.output)
        
        if files:
            print("\n" + "=" * 60)
            print("COMPLETE!")
            print("=" * 60)
            print("\nAll FPL data has been collected and saved.")
            print("\nGenerated files:")
            for file_type, path in files.items():
                print(f"  {file_type}: {path}")
            print("\nYou can now send these files to AI for analysis.")
        else:
            print("\n[ERROR] Failed to save data files")
    
    return collector.data

if __name__ == "__main__":
    main()