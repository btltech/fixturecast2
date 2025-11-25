
import numpy as np
from datetime import datetime

class FeatureBuilder:
    def build_features(self, fixture_details, standings, home_last_10, away_last_10, 
                      home_stats, away_stats, h2h, home_injuries, away_injuries, odds):
        """
        Extract comprehensive features from API data for ML models.
        Returns a rich feature dictionary with 50+ features.
        """
        
        try:
            fixture = fixture_details['response'][0]
            home_id = fixture['teams']['home']['id']
            away_id = fixture['teams']['away']['id']
            home_name = fixture['teams']['home']['name']
            away_name = fixture['teams']['away']['name']
        except (KeyError, IndexError, TypeError) as e:
            print(f"Warning: Failed to extract fixture details: {e}")
            home_id = away_id = 0
            home_name = away_name = "Unknown"

        # Core IDs
        features = {
            "home_id": home_id,
            "away_id": away_id,
            "home_name": home_name,
            "away_name": away_name,
        }

        # League standings features
        home_rank, home_points = self._get_team_standing(standings, home_id)
        away_rank, away_points = self._get_team_standing(standings, away_id)
        
        features.update({
            "home_league_pos": home_rank,
            "away_league_pos": away_rank,
            "home_league_points": home_points,
            "away_league_points": away_points,
            "rank_difference": away_rank - home_rank,  # Positive if home is better
            "points_difference": home_points - away_points,
        })

        # Recent form (last 10 matches)
        home_form = self._analyze_form(home_last_10, home_id)
        away_form = self._analyze_form(away_last_10, away_id)
        
        features.update({
            "home_wins_last10": home_form['wins'],
            "home_draws_last10": home_form['draws'],
            "home_losses_last10": home_form['losses'],
            "home_points_last10": home_form['points'],
            "home_goals_for_last10": home_form['goals_for'],
            "home_goals_against_last10": home_form['goals_against'],
            "home_goal_diff_last10": home_form['goal_diff'],
            "home_form_last5": home_form['points_last5'],  # Added for short-term form
            
            "away_wins_last10": away_form['wins'],
            "away_draws_last10": away_form['draws'],
            "away_losses_last10": away_form['losses'],
            "away_points_last10": away_form['points'],
            "away_goals_for_last10": away_form['goals_for'],
            "away_goals_against_last10": away_form['goals_against'],
            "away_goal_diff_last10": away_form['goal_diff'],
            "away_form_last5": away_form['points_last5'],  # Added for short-term form
            
            "form_difference": home_form['points'] - away_form['points'],
        })

        # Season statistics
        home_season = self._extract_season_stats(home_stats)
        away_season = self._extract_season_stats(away_stats)
        
        features.update({
            "home_total_matches": home_season['matches_played'],
            "home_total_wins": home_season['wins'],
            "home_total_draws": home_season['draws'],
            "home_total_losses": home_season['losses'],
            "home_goals_for_avg": home_season['goals_for_avg'],
            "home_goals_against_avg": home_season['goals_against_avg'],
            "home_clean_sheets": home_season['clean_sheets'],
            "home_xg_avg": home_season.get('xg_for_avg'),  # Expected goals for
            "home_xga_avg": home_season.get('xg_against_avg'),  # Expected goals against
            
            "away_total_matches": away_season['matches_played'],
            "away_total_wins": away_season['wins'],
            "away_total_draws": away_season['draws'],
            "away_total_losses": away_season['losses'],
            "away_goals_for_avg": away_season['goals_for_avg'],
            "away_goals_against_avg": away_season['goals_against_avg'],
            "away_clean_sheets": away_season['clean_sheets'],
            "away_xg_avg": away_season.get('xg_for_avg'),  # Expected goals for
            "away_xga_avg": away_season.get('xg_against_avg'),  # Expected goals against
        })

        # Head-to-head features
        h2h_stats = self._analyze_h2h(h2h, home_id, away_id)
        features.update({
            "h2h_home_wins": h2h_stats['home_wins'],
            "h2h_draws": h2h_stats['draws'],
            "h2h_away_wins": h2h_stats['away_wins'],
            "h2h_total_matches": h2h_stats['total'],
            "h2h_avg_goals": h2h_stats['avg_goals'],
        })

        # Injuries impact
        features.update({
            "home_injuries_count": self._count_injuries(home_injuries),
            "away_injuries_count": self._count_injuries(away_injuries),
        })

        # Betting odds (if available)
        odds_features = self._extract_odds(odds)
        features.update(odds_features)

        # Derived features - ensure all values are floats
        home_gf_avg = self._safe_float(home_season['goals_for_avg'], 1.0)
        home_ga_avg = self._safe_float(home_season['goals_against_avg'], 1.0)
        away_gf_avg = self._safe_float(away_season['goals_for_avg'], 1.0)
        away_ga_avg = self._safe_float(away_season['goals_against_avg'], 1.0)
        
        features.update({
            "home_attack_strength": home_gf_avg / max(away_ga_avg, 0.5),
            "away_attack_strength": away_gf_avg / max(home_ga_avg, 0.5),
            "home_defense_strength": home_ga_avg / max(away_gf_avg, 0.5),
            "away_defense_strength": away_ga_avg / max(home_gf_avg, 0.5),
        })

        return features

    def _get_team_standing(self, standings_response, team_id):
        """Extract team's league position and points"""
        if not standings_response or 'response' not in standings_response:
            return 10, 0
        try:
            for row in standings_response['response'][0]['league']['standings'][0]:
                if row['team']['id'] == team_id:
                    return row['rank'], row['points']
        except (KeyError, IndexError, TypeError) as e:
            print(f"Warning: Failed to extract team standing: {e}")
        return 10, 0

    def _analyze_form(self, fixtures_response, team_id):
        """
        Analyze recent form from last 10 and last 5 matches.
        Returns points, goals, and other stats for both periods.
        """
        form = {
            'wins': 0, 'draws': 0, 'losses': 0, 'points': 0,
            'goals_for': 0, 'goals_against': 0, 'goal_diff': 0,
            'wins_last5': 0, 'points_last5': 0  # Added for last 5 matches
        }
        
        if not fixtures_response or 'response' not in fixtures_response:
            return form
        
        matches_analyzed = 0
        for f in fixtures_response['response'][:10]:  # Last 10 matches
            if f['goals']['home'] is None or f['goals']['away'] is None:
                continue
            
            matches_analyzed += 1
            is_home = f['teams']['home']['id'] == team_id
            goals_for = f['goals']['home'] if is_home else f['goals']['away']
            goals_against = f['goals']['away'] if is_home else f['goals']['home']
            
            form['goals_for'] += goals_for
            form['goals_against'] += goals_against
            
            points_earned = 0
            if goals_for > goals_against:
                form['wins'] += 1
                points_earned = 3
                if matches_analyzed <= 5:  # Count for last 5
                    form['wins_last5'] += 1
            elif goals_for == goals_against:
                form['draws'] += 1
                points_earned = 1
            else:
                form['losses'] += 1
                points_earned = 0
            
            form['points'] += points_earned
            
            # Track last 5 separately
            if matches_analyzed <= 5:
                form['points_last5'] += points_earned
        
        form['goal_diff'] = form['goals_for'] - form['goals_against']
        return form

    def _safe_float(self, value, default=0.0):
        """Safely convert value to float, handling nested dicts and None"""
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, dict):
            # If it's a dict, try to get 'total' key
            return self._safe_float(value.get('total'), default)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        return default

    def _extract_season_stats(self, stats_response):
        """Extract season-long statistics including xG if available"""
        default = {
            'matches_played': 0, 'wins': 0, 'draws': 0, 'losses': 0,
            'goals_for_avg': 0, 'goals_against_avg': 0, 'clean_sheets': 0,
            'xg_for_avg': None, 'xg_against_avg': None  # Expected goals
        }
        
        if not stats_response or 'response' not in stats_response:
            return default
        
        try:
            resp = stats_response['response']
            # Handle case where response is a list (some API versions) vs dict
            if isinstance(resp, list):
                if not resp: return default
                resp = resp[0]
                
            fixtures = resp.get('fixtures', {})
            goals = resp.get('goals', {})
            
            # Extract goals averages safely
            goals_for = goals.get('for', {})
            goals_against = goals.get('against', {})
            
            # Handle nested average structures
            goals_for_avg_data = goals_for.get('average', {})
            goals_against_avg_data = goals_against.get('average', {})
            
            # Try to extract xG (Expected Goals) if available
            # API-Football may provide this under different paths depending on subscription
            xg_for_avg = None
            xg_against_avg = None
            
            # Check if xG is available (premium API feature)
            if 'expected' in goals_for:
                xg_for_avg = self._safe_float(goals_for.get('expected', {}).get('average', {}).get('total'))
            
            if 'expected' in goals_against:
                xg_against_avg = self._safe_float(goals_against.get('expected', {}).get('average', {}).get('total'))
            
            return {
                'matches_played': int(fixtures.get('played', {}).get('total', 0) or 0),
                'wins': int(fixtures.get('wins', {}).get('total', 0) or 0),
                'draws': int(fixtures.get('draws', {}).get('total', 0) or 0),
                'losses': int(fixtures.get('loses', {}).get('total', 0) or 0),
                'goals_for_avg': self._safe_float(goals_for_avg_data.get('total', 0)),
                'goals_against_avg': self._safe_float(goals_against_avg_data.get('total', 0)),
                'clean_sheets': int(resp.get('clean_sheet', {}).get('total', 0) or 0),
                'xg_for_avg': xg_for_avg,  # Will be None if not available
                'xg_against_avg': xg_against_avg,  # Will be None if not available
            }
        except Exception as e:
            print(f"Error extracting season stats: {e}")
            return default

    def _analyze_h2h(self, h2h_response, home_id, away_id):
        """
        Analyze head-to-head record from current home team's perspective.
        
        home_wins = times current home team won (regardless of venue in that H2H match)
        away_wins = times current away team won (regardless of venue in that H2H match)
        
        This correctly tracks the matchup regardless of who was home/away in past games.
        """
        stats = {'home_wins': 0, 'draws': 0, 'away_wins': 0, 'total': 0, 'avg_goals': 0}
        
        if not h2h_response or 'response' not in h2h_response:
            return stats
        
        total_goals = 0
        for f in h2h_response['response']:
            if f['goals']['home'] is None or f['goals']['away'] is None:
                continue
            
            stats['total'] += 1
            total_goals += f['goals']['home'] + f['goals']['away']
            
            # Determine goals scored by each team in the current matchup context
            # (not the home/away from that particular H2H game)
            if f['teams']['home']['id'] == home_id:
                # Current home team was home in this H2H match
                current_home_goals = f['goals']['home']
                current_away_goals = f['goals']['away']
            elif f['teams']['away']['id'] == home_id:
                # Current home team was away in this H2H match
                current_home_goals = f['goals']['away']
                current_away_goals = f['goals']['home']
            else:
                # Neither team in this H2H is in current matchup (shouldn't happen)
                continue
            
            # Count from current matchup perspective
            if current_home_goals > current_away_goals:
                stats['home_wins'] += 1  # Current home team won
            elif current_home_goals == current_away_goals:
                stats['draws'] += 1
            else:
                stats['away_wins'] += 1  # Current away team won
        
        if stats['total'] > 0:
            stats['avg_goals'] = total_goals / stats['total']
        
        return stats

    def _count_injuries(self, injuries_response):
        """Count number of injured players"""
        if not injuries_response or 'response' not in injuries_response:
            return 0
        return len(injuries_response['response'])

    def _extract_odds(self, odds_response):
        """Extract betting odds as features"""
        default_odds = {
            'odds_home_win': 0, 'odds_draw': 0, 'odds_away_win': 0,
            'odds_available': False
        }
        
        if not odds_response or 'response' not in odds_response:
            return default_odds
        
        try:
            if not odds_response['response']:
                return default_odds
                
            # Look for Match Winner odds
            for bookmaker in odds_response['response'][0].get('bookmakers', []):
                for bet in bookmaker.get('bets', []):
                    if bet['name'] == 'Match Winner':
                        values = bet.get('values', [])
                        for v in values:
                            if v['value'] == 'Home':
                                default_odds['odds_home_win'] = self._safe_float(v['odd'])
                            elif v['value'] == 'Draw':
                                default_odds['odds_draw'] = self._safe_float(v['odd'])
                            elif v['value'] == 'Away':
                                default_odds['odds_away_win'] = self._safe_float(v['odd'])
                        default_odds['odds_available'] = True
                        return default_odds
        except Exception as e:
            print(f"Error extracting odds: {e}")
            pass
        
        return default_odds
