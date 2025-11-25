
import numpy as np
from datetime import datetime

class FeatureBuilder:
    
    # Competition type encoding
    COMPETITION_TYPES = {
        "domestic_league": 0,
        "european_cup": 1,
        "domestic_cup": 2,
        "other": 3
    }
    
    # European league IDs for cross-league team matching
    EUROPEAN_COMPETITIONS = {2, 3, 848}  # UCL, UEL, UECL
    
    # Top domestic leagues by prestige
    TOP_LEAGUES = {39, 140, 135, 78, 61}  # PL, La Liga, Serie A, Bundesliga, Ligue 1
    
    def build_features(self, fixture_details, standings, home_last_10, away_last_10, 
                      home_stats, away_stats, h2h, home_injuries, away_injuries, odds,
                      home_players=None, away_players=None, home_coach=None, away_coach=None,
                      home_recent_stats=None, away_recent_stats=None,
                      competition_info=None, round_info=None):
        """
        Extract comprehensive features from API data for ML models.
        Returns a rich feature dictionary with 80+ features.
        
        New optional parameters for enhanced predictions:
        - home_players/away_players: Player stats including goals, assists
        - home_coach/away_coach: Coach info and tenure
        - home_recent_stats/away_recent_stats: Match statistics from recent games
        - competition_info: Competition metadata (type, format, prestige)
        - round_info: Round information (knockout vs group, final, etc.)
        """
        
        try:
            fixture = fixture_details['response'][0]
            home_id = fixture['teams']['home']['id']
            away_id = fixture['teams']['away']['id']
            home_name = fixture['teams']['home']['name']
            away_name = fixture['teams']['away']['name']
            league_id = fixture.get('league', {}).get('id', 0)
            league_round = fixture.get('league', {}).get('round', '')
        except (KeyError, IndexError, TypeError) as e:
            print(f"Warning: Failed to extract fixture details: {e}")
            home_id = away_id = league_id = 0
            home_name = away_name = league_round = "Unknown"

        # Core IDs
        features = {
            "home_id": home_id,
            "away_id": away_id,
            "home_name": home_name,
            "away_name": away_name,
            "league_id": league_id,
        }
        
        # ========== COMPETITION TYPE FEATURES ==========
        comp_features = self._extract_competition_features(
            league_id, league_round, competition_info, round_info
        )
        features.update(comp_features)

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

        # ========== ENHANCED FEATURES (from new data sources) ==========
        
        # Player-based features (top scorer dependency, squad depth)
        home_player_stats = self._extract_player_features(home_players, "home")
        away_player_stats = self._extract_player_features(away_players, "away")
        features.update(home_player_stats)
        features.update(away_player_stats)
        
        # Coach features (tenure, experience)
        home_coach_features = self._extract_coach_features(home_coach, "home")
        away_coach_features = self._extract_coach_features(away_coach, "away")
        features.update(home_coach_features)
        features.update(away_coach_features)
        
        # Recent match statistics (possession, shots, xG patterns)
        home_match_stats = self._extract_recent_match_stats(home_recent_stats, home_last_10, home_id, "home")
        away_match_stats = self._extract_recent_match_stats(away_recent_stats, away_last_10, away_id, "away")
        features.update(home_match_stats)
        features.update(away_match_stats)
        
        # Discipline features (cards from recent matches)
        home_discipline = self._extract_discipline_features(home_last_10, home_id, "home")
        away_discipline = self._extract_discipline_features(away_last_10, away_id, "away")
        features.update(home_discipline)
        features.update(away_discipline)
        
        # Goal timing patterns
        home_timing = self._extract_goal_timing(home_last_10, home_id, "home")
        away_timing = self._extract_goal_timing(away_last_10, away_id, "away")
        features.update(home_timing)
        features.update(away_timing)

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

    # ========== NEW ENHANCED FEATURE EXTRACTION METHODS ==========
    
    def _extract_player_features(self, players_response, prefix):
        """
        Extract player-based features: top scorer goals, squad depth, key player dependency.
        """
        features = {
            f"{prefix}_top_scorer_goals": 0,
            f"{prefix}_top_scorer_name": None,
            f"{prefix}_top_assister_assists": 0,
            f"{prefix}_squad_goals_total": 0,
            f"{prefix}_players_with_goals": 0,
            f"{prefix}_top_scorer_dependency": 0.0,  # % of goals from top scorer
        }
        
        if not players_response or 'response' not in players_response:
            return features
        
        try:
            players = players_response['response']
            if not players:
                return features
            
            # Collect all scorers
            scorers = []
            assisters = []
            total_goals = 0
            
            for p in players:
                player_info = p.get('player', {})
                stats = p.get('statistics', [{}])[0] if p.get('statistics') else {}
                goals_data = stats.get('goals', {})
                
                goals = goals_data.get('total') or 0
                assists = goals_data.get('assists') or 0
                
                if goals > 0:
                    scorers.append({
                        'name': player_info.get('name', 'Unknown'),
                        'goals': goals
                    })
                    total_goals += goals
                
                if assists > 0:
                    assisters.append({
                        'name': player_info.get('name', 'Unknown'),
                        'assists': assists
                    })
            
            # Sort and extract top performer data
            scorers.sort(key=lambda x: x['goals'], reverse=True)
            assisters.sort(key=lambda x: x['assists'], reverse=True)
            
            if scorers:
                features[f"{prefix}_top_scorer_goals"] = scorers[0]['goals']
                features[f"{prefix}_top_scorer_name"] = scorers[0]['name']
                features[f"{prefix}_squad_goals_total"] = total_goals
                features[f"{prefix}_players_with_goals"] = len(scorers)
                features[f"{prefix}_top_scorer_dependency"] = scorers[0]['goals'] / max(total_goals, 1)
            
            if assisters:
                features[f"{prefix}_top_assister_assists"] = assisters[0]['assists']
                
        except Exception as e:
            print(f"Error extracting player features: {e}")
        
        return features
    
    def _extract_coach_features(self, coach_response, prefix):
        """
        Extract coach features: tenure (new manager bounce effect), career experience.
        """
        features = {
            f"{prefix}_coach_name": None,
            f"{prefix}_coach_tenure_days": 0,
            f"{prefix}_coach_is_new": False,  # < 90 days
            f"{prefix}_coach_career_teams": 0,
        }
        
        if not coach_response or 'response' not in coach_response:
            return features
        
        try:
            coaches = coach_response['response']
            if not coaches:
                return features
            
            # Get the current/most recent coach
            coach = coaches[0]
            features[f"{prefix}_coach_name"] = coach.get('name', 'Unknown')
            
            # Calculate tenure from career data
            career = coach.get('career', [])
            features[f"{prefix}_coach_career_teams"] = len(career)
            
            # Find current team stint
            for stint in career:
                if stint.get('end') is None:  # Current position
                    start_date = stint.get('start')
                    if start_date:
                        try:
                            start = datetime.strptime(start_date, "%Y-%m-%d")
                            tenure_days = (datetime.now() - start).days
                            features[f"{prefix}_coach_tenure_days"] = tenure_days
                            features[f"{prefix}_coach_is_new"] = tenure_days < 90
                        except:
                            pass
                    break
                    
        except Exception as e:
            print(f"Error extracting coach features: {e}")
        
        return features
    
    def _extract_recent_match_stats(self, recent_stats, fixtures_response, team_id, prefix):
        """
        Extract aggregated statistics from recent matches (possession, shots, xG).
        """
        features = {
            f"{prefix}_avg_possession": 50.0,
            f"{prefix}_avg_shots": 0,
            f"{prefix}_avg_shots_on_target": 0,
            f"{prefix}_avg_corners": 0,
            f"{prefix}_shot_accuracy": 0.0,
        }
        
        # If we have detailed stats from the API, use those
        if recent_stats:
            try:
                total_possession = 0
                total_shots = 0
                total_sot = 0
                total_corners = 0
                count = 0
                
                for match_stat in recent_stats:
                    stats = match_stat.get('stats', [])
                    for team_stats in stats:
                        if team_stats.get('team', {}).get('id') == team_id:
                            stat_list = team_stats.get('statistics', [])
                            for s in stat_list:
                                stat_type = s.get('type', '')
                                value = s.get('value')
                                
                                if stat_type == 'Ball Possession' and value:
                                    total_possession += int(str(value).replace('%', ''))
                                elif stat_type == 'Total Shots' and value:
                                    total_shots += int(value)
                                elif stat_type == 'Shots on Goal' and value:
                                    total_sot += int(value)
                                elif stat_type == 'Corner Kicks' and value:
                                    total_corners += int(value)
                            count += 1
                
                if count > 0:
                    features[f"{prefix}_avg_possession"] = total_possession / count
                    features[f"{prefix}_avg_shots"] = total_shots / count
                    features[f"{prefix}_avg_shots_on_target"] = total_sot / count
                    features[f"{prefix}_avg_corners"] = total_corners / count
                    features[f"{prefix}_shot_accuracy"] = total_sot / max(total_shots, 1)
                    
            except Exception as e:
                print(f"Error extracting recent match stats: {e}")
        
        return features
    
    def _extract_discipline_features(self, fixtures_response, team_id, prefix):
        """
        Extract discipline features from recent matches (yellow/red cards).
        """
        features = {
            f"{prefix}_yellow_cards_last5": 0,
            f"{prefix}_red_cards_last5": 0,
            f"{prefix}_cards_per_game": 0.0,
        }
        
        if not fixtures_response or 'response' not in fixtures_response:
            return features
        
        try:
            yellow_cards = 0
            red_cards = 0
            matches_analyzed = 0
            
            for f in fixtures_response['response'][:5]:  # Last 5 matches
                # Get events if available in the fixture data
                events = f.get('events', [])
                
                for event in events:
                    if event.get('team', {}).get('id') == team_id:
                        event_type = event.get('type', '')
                        detail = event.get('detail', '')
                        
                        if event_type == 'Card':
                            if 'Yellow' in detail:
                                yellow_cards += 1
                            elif 'Red' in detail:
                                red_cards += 1
                
                matches_analyzed += 1
            
            features[f"{prefix}_yellow_cards_last5"] = yellow_cards
            features[f"{prefix}_red_cards_last5"] = red_cards
            if matches_analyzed > 0:
                features[f"{prefix}_cards_per_game"] = (yellow_cards + red_cards * 2) / matches_analyzed
                
        except Exception as e:
            print(f"Error extracting discipline features: {e}")
        
        return features
    
    def _extract_goal_timing(self, fixtures_response, team_id, prefix):
        """
        Extract goal timing patterns (early goals, late goals, comeback ability).
        """
        features = {
            f"{prefix}_early_goals_pct": 0.0,  # Goals 0-30 min
            f"{prefix}_late_goals_pct": 0.0,   # Goals 75+ min
            f"{prefix}_first_half_goals_pct": 0.0,
            f"{prefix}_conceded_late_pct": 0.0,  # Important for fitness/concentration
        }
        
        if not fixtures_response or 'response' not in fixtures_response:
            return features
        
        try:
            goals_scored = {'early': 0, 'first_half': 0, 'late': 0, 'total': 0}
            goals_conceded = {'late': 0, 'total': 0}
            
            for f in fixtures_response['response'][:10]:
                events = f.get('events', [])
                is_home = f['teams']['home']['id'] == team_id
                
                for event in events:
                    if event.get('type') == 'Goal' and event.get('detail') != 'Missed Penalty':
                        minute = event.get('time', {}).get('elapsed', 45)
                        scoring_team_id = event.get('team', {}).get('id')
                        
                        if scoring_team_id == team_id:
                            # We scored
                            goals_scored['total'] += 1
                            if minute <= 30:
                                goals_scored['early'] += 1
                            if minute <= 45:
                                goals_scored['first_half'] += 1
                            if minute >= 75:
                                goals_scored['late'] += 1
                        else:
                            # We conceded
                            goals_conceded['total'] += 1
                            if minute >= 75:
                                goals_conceded['late'] += 1
            
            if goals_scored['total'] > 0:
                features[f"{prefix}_early_goals_pct"] = goals_scored['early'] / goals_scored['total']
                features[f"{prefix}_first_half_goals_pct"] = goals_scored['first_half'] / goals_scored['total']
                features[f"{prefix}_late_goals_pct"] = goals_scored['late'] / goals_scored['total']
            
            if goals_conceded['total'] > 0:
                features[f"{prefix}_conceded_late_pct"] = goals_conceded['late'] / goals_conceded['total']
                
        except Exception as e:
            print(f"Error extracting goal timing: {e}")
        
        return features

    # ========== COMPETITION-TYPE FEATURE EXTRACTION ==========
    
    def _extract_competition_features(self, league_id, league_round, competition_info=None, round_info=None):
        """
        Extract competition-specific features for different tournament types.
        Handles domestic leagues, European cups (UCL/UEL), knockout stages, etc.
        """
        features = {
            # Competition type (one-hot encoded)
            "is_domestic_league": 0,
            "is_european_cup": 0,
            "is_domestic_cup": 0,
            
            # Stage features
            "is_knockout_stage": 0,
            "is_group_stage": 0,
            "is_final": 0,
            "is_two_leg_tie": 0,
            "is_neutral_venue": 0,
            
            # For analysis LLM
            "is_knockout": False,
            "is_two_leg": False,
            "is_european": False,
            "competition_type": "domestic_league",
            "competition_name": "",
            
            # Prestige and stakes
            "competition_prestige": 1.0,
            "stakes_multiplier": 1.0,
            
            # Competition metadata
            "competition_type_encoded": 0,
            "league_id": league_id,
        }
        
        # Use provided competition_info or infer from league_id
        if competition_info is None:
            competition_info = self._infer_competition_info(league_id)
        
        # Set competition name
        features["competition_name"] = competition_info.get("name", "")
        
        comp_type = competition_info.get("type", "domestic_league")
        features["competition_type"] = comp_type  # For analysis LLM
        
        # Set competition type flags
        if comp_type == "domestic_league":
            features["is_domestic_league"] = 1
            features["competition_type_encoded"] = 0
        elif comp_type == "european_cup":
            features["is_european_cup"] = 1
            features["is_european"] = True  # For analysis LLM
            features["competition_type_encoded"] = 1
        elif comp_type == "domestic_cup":
            features["is_domestic_cup"] = 1
            features["competition_type_encoded"] = 2
        
        # Set prestige factor
        features["competition_prestige"] = competition_info.get("prestige_factor", 1.0)
        
        # Analyze round information
        if round_info:
            features["is_knockout_stage"] = 1 if round_info.get("is_knockout") else 0
            features["is_group_stage"] = 1 if round_info.get("is_group_stage") else 0
            features["is_final"] = 1 if round_info.get("is_final") else 0
            features["is_knockout"] = bool(round_info.get("is_knockout"))  # For analysis LLM
        elif league_round:
            # Infer from round string
            round_lower = league_round.lower()
            is_knockout = self._is_knockout_round_str(round_lower)
            features["is_knockout_stage"] = 1 if is_knockout else 0
            features["is_knockout"] = is_knockout  # For analysis LLM
            features["is_group_stage"] = 1 if "group" in round_lower else 0
            features["is_final"] = 1 if "final" in round_lower and "semi" not in round_lower else 0
        
        # Two-leg tie detection
        if competition_info.get("two_leg_knockout") and features["is_knockout_stage"] and not features["is_final"]:
            features["is_two_leg_tie"] = 1
            features["is_two_leg"] = True  # For analysis LLM
        
        # Neutral venue (typically finals)
        if competition_info.get("neutral_final") and features["is_final"]:
            features["is_neutral_venue"] = 1
        
        # Stakes multiplier (higher for knockouts, finals)
        stakes = 1.0
        if features["is_knockout_stage"]:
            stakes *= 1.3
        if features["is_final"]:
            stakes *= 1.5
        if features["is_european_cup"]:
            stakes *= 1.2
        features["stakes_multiplier"] = stakes
        
        # Form reliability (lower for European games - domestic form less predictive)
        if features["is_european_cup"]:
            features["home_form_reliability"] = 0.6
            features["away_form_reliability"] = 0.6
        else:
            features["home_form_reliability"] = 1.0
            features["away_form_reliability"] = 1.0
        
        return features
    
    # Competition name lookup
    COMPETITION_NAMES = {
        2: "UEFA Champions League",
        3: "UEFA Europa League",
        848: "UEFA Conference League",
        39: "Premier League",
        140: "La Liga",
        135: "Serie A",
        78: "Bundesliga",
        61: "Ligue 1",
        40: "Championship",
        41: "League One",
        42: "League Two",
        45: "FA Cup",
        48: "League Cup (Carabao Cup)",
    }
    
    def _infer_competition_info(self, league_id):
        """Infer competition info when not provided."""
        name = self.COMPETITION_NAMES.get(league_id, "")
        
        if league_id in self.EUROPEAN_COMPETITIONS:
            return {
                "type": "european_cup",
                "format": "group_knockout",
                "two_leg_knockout": True,
                "neutral_final": True,
                "prestige_factor": 1.5 if league_id == 2 else 1.3 if league_id == 3 else 1.1,
                "name": name
            }
        elif league_id in self.TOP_LEAGUES:
            return {
                "type": "domestic_league",
                "format": "league",
                "two_leg_knockout": False,
                "neutral_final": False,
                "prestige_factor": 1.0,
                "name": name
            }
        elif league_id in {45, 48}:  # FA Cup, League Cup
            return {
                "type": "domestic_cup",
                "format": "knockout",
                "two_leg_knockout": False,
                "neutral_final": True,
                "prestige_factor": 0.9,
                "name": name
            }
        else:
            return {
                "type": "domestic_league",
                "format": "league",
                "two_leg_knockout": False,
                "neutral_final": False,
                "prestige_factor": 0.8,
                "name": name
            }
    
    def _is_knockout_round_str(self, round_str):
        """Check if round string indicates knockout stage."""
        knockout_keywords = [
            "round of", "quarter", "semi", "final", 
            "knockout", "elimination", "playoff", "1/8", "1/4", "1/2"
        ]
        return any(kw in round_str for kw in knockout_keywords)

