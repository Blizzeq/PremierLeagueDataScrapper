#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FPL DATA COMPARISON TOOL
Compare data between different collection dates to track changes
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

class FPLDataComparator:
    """Compare FPL data between different dates"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        
    def find_data_files(self) -> List[Tuple[str, Path]]:
        """Find all available data files organized by date"""
        files = []
        
        if not self.data_dir.exists():
            print(f"[ERROR] Data directory '{self.data_dir}' not found")
            return files
            
        # Find all date folders
        for date_folder in sorted(self.data_dir.iterdir()):
            if date_folder.is_dir():
                # Find JSON files in this date folder
                json_files = list(date_folder.glob("fpl_data_*.json"))
                if json_files:
                    # Get the most recent file from this date
                    latest_file = sorted(json_files)[-1]
                    files.append((date_folder.name, latest_file))
                    
        return files
    
    def load_data(self, filepath: Path) -> Dict:
        """Load JSON data from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load {filepath}: {e}")
            return {}
    
    def compare_players(self, old_data: Dict, new_data: Dict) -> Dict:
        """Compare player data between two datasets"""
        comparison = {
            'price_changes': [],
            'ownership_changes': [],
            'injury_updates': [],
            'form_changes': [],
            'new_players': [],
            'removed_players': []
        }
        
        old_players = {p['id']: p for p in old_data.get('players', [])}
        new_players = {p['id']: p for p in new_data.get('players', [])}
        
        # Find new and removed players
        old_ids = set(old_players.keys())
        new_ids = set(new_players.keys())
        
        for pid in new_ids - old_ids:
            comparison['new_players'].append({
                'name': new_players[pid]['web_name'],
                'team': new_players[pid]['team'],
                'price': new_players[pid]['now_cost'] / 10
            })
            
        for pid in old_ids - new_ids:
            comparison['removed_players'].append({
                'name': old_players[pid]['web_name'],
                'team': old_players[pid]['team']
            })
        
        # Compare common players
        for pid in old_ids & new_ids:
            old_p = old_players[pid]
            new_p = new_players[pid]
            
            # Price changes
            if old_p['now_cost'] != new_p['now_cost']:
                comparison['price_changes'].append({
                    'name': new_p['web_name'],
                    'old_price': old_p['now_cost'] / 10,
                    'new_price': new_p['now_cost'] / 10,
                    'change': (new_p['now_cost'] - old_p['now_cost']) / 10
                })
            
            # Ownership changes (significant only)
            old_ownership = float(old_p['selected_by_percent'])
            new_ownership = float(new_p['selected_by_percent'])
            if abs(new_ownership - old_ownership) > 2.0:  # More than 2% change
                comparison['ownership_changes'].append({
                    'name': new_p['web_name'],
                    'old_ownership': old_ownership,
                    'new_ownership': new_ownership,
                    'change': new_ownership - old_ownership
                })
            
            # Injury updates
            if old_p['status'] != new_p['status']:
                comparison['injury_updates'].append({
                    'name': new_p['web_name'],
                    'old_status': old_p['status'],
                    'new_status': new_p['status'],
                    'news': new_p.get('news', '')
                })
            
            # Form changes (significant only)
            try:
                old_form = float(old_p.get('form', 0))
                new_form = float(new_p.get('form', 0))
                if abs(new_form - old_form) > 1.0:  # Significant form change
                    comparison['form_changes'].append({
                        'name': new_p['web_name'],
                        'old_form': old_form,
                        'new_form': new_form,
                        'change': new_form - old_form
                    })
            except (ValueError, TypeError):
                pass
                
        return comparison
    
    def compare_fixtures(self, old_data: Dict, new_data: Dict) -> Dict:
        """Compare fixture data between two datasets"""
        comparison = {
            'new_results': [],
            'fixture_changes': []
        }
        
        old_fixtures = {f['id']: f for f in old_data.get('fixtures', [])}
        new_fixtures = {f['id']: f for f in new_data.get('fixtures', [])}
        
        for fid in old_fixtures.keys() & new_fixtures.keys():
            old_f = old_fixtures[fid]
            new_f = new_fixtures[fid]
            
            # Check for new results
            if not old_f['finished'] and new_f['finished']:
                comparison['new_results'].append({
                    'gameweek': new_f['event'],
                    'home_team': new_f['team_h'],
                    'away_team': new_f['team_a'],
                    'score': f"{new_f['team_h_score']}-{new_f['team_a_score']}"
                })
            
            # Check for fixture time changes
            if old_f.get('kickoff_time') != new_f.get('kickoff_time'):
                comparison['fixture_changes'].append({
                    'gameweek': new_f['event'],
                    'home_team': new_f['team_h'],
                    'away_team': new_f['team_a'],
                    'old_time': old_f.get('kickoff_time'),
                    'new_time': new_f.get('kickoff_time')
                })
                
        return comparison
    
    def generate_comparison_report(self, date1: str, date2: str) -> str:
        """Generate a comparison report between two dates"""
        files = self.find_data_files()
        
        # Find the specified dates
        file1 = None
        file2 = None
        
        for date, filepath in files:
            if date == date1:
                file1 = filepath
            if date == date2:
                file2 = filepath
                
        if not file1 or not file2:
            return f"[ERROR] Could not find data for both dates: {date1}, {date2}"
        
        # Load data
        old_data = self.load_data(file1)
        new_data = self.load_data(file2)
        
        if not old_data or not new_data:
            return "[ERROR] Failed to load data files"
        
        # Compare data
        player_changes = self.compare_players(old_data, new_data)
        fixture_changes = self.compare_fixtures(old_data, new_data)
        
        # Generate report
        report = []
        report.append("=" * 60)
        report.append("FPL DATA COMPARISON REPORT")
        report.append(f"Comparing: {date1} -> {date2}")
        report.append("=" * 60)
        report.append("")
        
        # Price changes
        if player_changes['price_changes']:
            report.append("PRICE CHANGES:")
            report.append("-" * 40)
            for change in sorted(player_changes['price_changes'], 
                               key=lambda x: abs(x['change']), reverse=True)[:20]:
                sign = "+" if change['change'] > 0 else ""
                report.append(f"  {change['name']}: GBP{change['old_price']:.1f}m -> GBP{change['new_price']:.1f}m ({sign}{change['change']:.1f})")
            report.append("")
        
        # Ownership changes
        if player_changes['ownership_changes']:
            report.append("SIGNIFICANT OWNERSHIP CHANGES (>2%):")
            report.append("-" * 40)
            for change in sorted(player_changes['ownership_changes'], 
                               key=lambda x: abs(x['change']), reverse=True)[:15]:
                sign = "+" if change['change'] > 0 else ""
                report.append(f"  {change['name']}: {change['old_ownership']:.1f}% -> {change['new_ownership']:.1f}% ({sign}{change['change']:.1f}%)")
            report.append("")
        
        # Injury updates
        if player_changes['injury_updates']:
            report.append("INJURY STATUS UPDATES:")
            report.append("-" * 40)
            for update in player_changes['injury_updates'][:20]:
                report.append(f"  {update['name']}: {update['old_status']} -> {update['new_status']}")
                if update['news']:
                    report.append(f"    News: {update['news']}")
            report.append("")
        
        # Form changes
        if player_changes['form_changes']:
            report.append("SIGNIFICANT FORM CHANGES:")
            report.append("-" * 40)
            for change in sorted(player_changes['form_changes'], 
                               key=lambda x: abs(x['change']), reverse=True)[:15]:
                sign = "+" if change['change'] > 0 else ""
                report.append(f"  {change['name']}: {change['old_form']:.1f} -> {change['new_form']:.1f} ({sign}{change['change']:.1f})")
            report.append("")
        
        # New players
        if player_changes['new_players']:
            report.append("NEW PLAYERS:")
            report.append("-" * 40)
            for player in player_changes['new_players']:
                report.append(f"  {player['name']} - Team {player['team']} - GBP{player['price']:.1f}m")
            report.append("")
        
        # Removed players
        if player_changes['removed_players']:
            report.append("REMOVED PLAYERS:")
            report.append("-" * 40)
            for player in player_changes['removed_players']:
                report.append(f"  {player['name']} - Team {player['team']}")
            report.append("")
        
        # New results
        if fixture_changes['new_results']:
            report.append("NEW MATCH RESULTS:")
            report.append("-" * 40)
            for result in fixture_changes['new_results']:
                report.append(f"  GW{result['gameweek']}: Team {result['home_team']} vs Team {result['away_team']} - Score: {result['score']}")
            report.append("")
        
        # Summary
        report.append("SUMMARY:")
        report.append("-" * 40)
        report.append(f"  Price changes: {len(player_changes['price_changes'])}")
        report.append(f"  Ownership changes: {len(player_changes['ownership_changes'])}")
        report.append(f"  Injury updates: {len(player_changes['injury_updates'])}")
        report.append(f"  Form changes: {len(player_changes['form_changes'])}")
        report.append(f"  New players: {len(player_changes['new_players'])}")
        report.append(f"  Removed players: {len(player_changes['removed_players'])}")
        report.append(f"  New results: {len(fixture_changes['new_results'])}")
        
        return "\n".join(report)
    
    def interactive_compare(self):
        """Interactive comparison mode"""
        files = self.find_data_files()
        
        if len(files) < 2:
            print("[ERROR] Need at least 2 data collections to compare")
            return
        
        print("=" * 60)
        print("FPL DATA COMPARISON TOOL")
        print("=" * 60)
        print("\nAvailable data collections:")
        for i, (date, filepath) in enumerate(files):
            file_size = filepath.stat().st_size / (1024 * 1024)  # MB
            print(f"  {i+1}. {date} ({file_size:.1f} MB)")
        
        print("\nSelect two dates to compare:")
        
        try:
            idx1 = int(input("Enter number for OLDER data: ")) - 1
            idx2 = int(input("Enter number for NEWER data: ")) - 1
            
            if 0 <= idx1 < len(files) and 0 <= idx2 < len(files):
                date1 = files[idx1][0]
                date2 = files[idx2][0]
                
                print(f"\nComparing {date1} -> {date2}...")
                report = self.generate_comparison_report(date1, date2)
                print("\n" + report)
                
                # Save report
                save = input("\nSave report to file? (y/n): ").lower()
                if save == 'y':
                    filename = f"comparison_{date1}_to_{date2}.txt"
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(report)
                    print(f"Report saved to: {filename}")
            else:
                print("[ERROR] Invalid selection")
                
        except (ValueError, IndexError):
            print("[ERROR] Invalid input")

def main():
    """Main function for comparison tool"""
    
    if len(sys.argv) == 3:
        # Direct comparison mode
        comparator = FPLDataComparator()
        report = comparator.generate_comparison_report(sys.argv[1], sys.argv[2])
        print(report)
    else:
        # Interactive mode
        comparator = FPLDataComparator()
        comparator.interactive_compare()

if __name__ == "__main__":
    main()