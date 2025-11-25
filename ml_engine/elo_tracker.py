#!/usr/bin/env python3
"""
True Elo Rating Tracker
Maintains persistent Elo ratings for all teams, updated match-by-match.
"""

import json
import os
import math
from datetime import datetime

class EloTracker:
    """
    Tracks true Elo ratings across all seasons.
    Updates ratings after each match instead of estimating from form.
    """
    
    def __init__(self, k_factor=32, home_advantage=100, initial_rating=1500):
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.initial_rating = initial_rating
        self.ratings = {}  # team_id -> rating
        self.rating_history = {}  # team_id -> [(date, rating), ...]
        self.matches_processed = 0
        
    def get_rating(self, team_id):
        """Get current Elo rating for a team"""
        if team_id not in self.ratings:
            self.ratings[team_id] = self.initial_rating
        return self.ratings[team_id]
    
    def expected_score(self, rating_a, rating_b):
        """Calculate expected score for team A against team B"""
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    
    def update_ratings(self, home_id, away_id, home_goals, away_goals, match_date=None):
        """
        Update Elo ratings after a match.
        Uses goal difference for more accurate updates.
        """
        # Get current ratings
        home_rating = self.get_rating(home_id)
        away_rating = self.get_rating(away_id)
        
        # Add home advantage for expectation calculation
        home_expected = self.expected_score(home_rating + self.home_advantage, away_rating)
        away_expected = 1 - home_expected
        
        # Determine actual scores (1 for win, 0.5 for draw, 0 for loss)
        if home_goals > away_goals:
            home_actual = 1.0
            away_actual = 0.0
        elif home_goals < away_goals:
            home_actual = 0.0
            away_actual = 1.0
        else:
            home_actual = 0.5
            away_actual = 0.5
        
        # Goal difference multiplier (larger margin = larger rating change)
        goal_diff = abs(home_goals - away_goals)
        if goal_diff == 0:
            gd_multiplier = 1.0
        elif goal_diff == 1:
            gd_multiplier = 1.0
        elif goal_diff == 2:
            gd_multiplier = 1.5
        elif goal_diff == 3:
            gd_multiplier = 1.75
        else:
            gd_multiplier = 1.75 + (goal_diff - 3) * 0.125
        
        # Calculate rating changes
        k_adjusted = self.k_factor * gd_multiplier
        home_change = k_adjusted * (home_actual - home_expected)
        away_change = k_adjusted * (away_actual - away_expected)
        
        # Update ratings
        self.ratings[home_id] = home_rating + home_change
        self.ratings[away_id] = away_rating + away_change
        
        # Track history
        if match_date:
            if home_id not in self.rating_history:
                self.rating_history[home_id] = []
            if away_id not in self.rating_history:
                self.rating_history[away_id] = []
            self.rating_history[home_id].append((match_date, self.ratings[home_id]))
            self.rating_history[away_id].append((match_date, self.ratings[away_id]))
        
        self.matches_processed += 1
        
        return {
            'home_old': home_rating,
            'home_new': self.ratings[home_id],
            'home_change': home_change,
            'away_old': away_rating,
            'away_new': self.ratings[away_id],
            'away_change': away_change
        }
    
    def predict_match(self, home_id, away_id):
        """
        Predict match outcome probabilities using Elo ratings.
        Returns probabilities for home_win, draw, away_win.
        """
        home_rating = self.get_rating(home_id)
        away_rating = self.get_rating(away_id)
        
        # Calculate expected scores with home advantage
        home_expected = self.expected_score(home_rating + self.home_advantage, away_rating)
        away_expected = 1 - home_expected
        
        # Rating difference affects draw probability
        rating_diff = abs((home_rating + self.home_advantage) - away_rating)
        
        # Base draw rate ~27%, decreases for mismatches
        if rating_diff < 50:
            draw_rate = 0.30  # Close match
        elif rating_diff < 100:
            draw_rate = 0.27
        elif rating_diff < 200:
            draw_rate = 0.23
        elif rating_diff < 300:
            draw_rate = 0.18
        else:
            draw_rate = 0.12  # Big mismatch
        
        # Convert expected scores to probabilities
        # expected = P(win) + 0.5 * P(draw)
        # P(win) = expected - 0.5 * P(draw)
        home_win = max(0.05, home_expected - 0.5 * draw_rate)
        away_win = max(0.05, away_expected - 0.5 * draw_rate)
        
        # Normalize
        total = home_win + draw_rate + away_win
        
        return {
            'home_win': round(home_win / total, 4),
            'draw': round(draw_rate / total, 4),
            'away_win': round(away_win / total, 4),
            'home_rating': round(home_rating, 1),
            'away_rating': round(away_rating, 1),
            'rating_diff': round(home_rating + self.home_advantage - away_rating, 1)
        }
    
    def get_top_teams(self, n=20):
        """Get top N rated teams"""
        sorted_teams = sorted(self.ratings.items(), key=lambda x: x[1], reverse=True)
        return sorted_teams[:n]
    
    def save(self, path):
        """Save ratings to file"""
        data = {
            'ratings': self.ratings,
            'rating_history': {str(k): v for k, v in self.rating_history.items()},
            'matches_processed': self.matches_processed,
            'k_factor': self.k_factor,
            'home_advantage': self.home_advantage,
            'initial_rating': self.initial_rating
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load(self, path):
        """Load ratings from file"""
        if os.path.exists(path):
            with open(path, 'r') as f:
                data = json.load(f)
            self.ratings = {int(k): v for k, v in data.get('ratings', {}).items()}
            self.rating_history = {int(k): v for k, v in data.get('rating_history', {}).items()}
            self.matches_processed = data.get('matches_processed', 0)
            self.k_factor = data.get('k_factor', 32)
            self.home_advantage = data.get('home_advantage', 100)
            self.initial_rating = data.get('initial_rating', 1500)
            return True
        return False


def build_elo_from_history(data_dir, output_path):
    """
    Process all historical matches to build Elo ratings.
    """
    tracker = EloTracker()
    
    # Load all season files in order
    season_files = sorted([f for f in os.listdir(data_dir) if f.startswith('season_')])
    
    all_matches = []
    for filename in season_files:
        filepath = os.path.join(data_dir, filename)
        with open(filepath) as f:
            matches = json.load(f)
            all_matches.extend(matches)
    
    # Sort by date
    all_matches.sort(key=lambda x: x['fixture']['date'])
    
    print(f"Processing {len(all_matches)} matches to build Elo ratings...")
    
    for i, match in enumerate(all_matches):
        home_id = match['teams']['home']['id']
        away_id = match['teams']['away']['id']
        home_goals = match['goals']['home']
        away_goals = match['goals']['away']
        match_date = match['fixture']['date']
        
        if home_goals is not None and away_goals is not None:
            tracker.update_ratings(home_id, away_id, home_goals, away_goals, match_date)
        
        if (i + 1) % 500 == 0:
            print(f"  Processed {i + 1}/{len(all_matches)} matches...")
    
    # Save ratings
    tracker.save(output_path)
    
    print(f"\n✅ Elo ratings built from {tracker.matches_processed} matches")
    print(f"   Tracking {len(tracker.ratings)} teams")
    print(f"   Saved to: {output_path}")
    
    # Show top teams
    print("\nTop 10 Rated Teams:")
    for team_id, rating in tracker.get_top_teams(10):
        print(f"   Team {team_id}: {rating:.1f}")
    
    return tracker


if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "../data/historical")
    output_path = os.path.join(os.path.dirname(__file__), "trained_models/elo_ratings.json")
    build_elo_from_history(data_dir, output_path)
