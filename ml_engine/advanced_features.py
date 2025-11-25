#!/usr/bin/env python3
"""
Advanced Feature Engineering Module
Adds 20+ additional predictive features for improved model accuracy.
"""

import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict


class AdvancedFeatureBuilder:
    """
    Builds advanced features beyond basic stats:
    - Momentum indicators
    - Venue-specific performance
    - Rest days impact
    - Rolling averages with exponential decay
    - Form streaks
    - Season phase
    """
    
    def __init__(self):
        self.team_venue_stats = defaultdict(lambda: {'home': [], 'away': []})
        self.team_last_match = {}  # team_id -> last match date
        
    def add_advanced_features(self, features, home_last_10, away_last_10, fixture_date=None):
        """
        Enhance feature dict with advanced features.
        """
        home_id = features.get('home_id')
        away_id = features.get('away_id')
        
        # 1. Momentum Features (weighted recent results)
        home_momentum = self._calculate_momentum(home_last_10, home_id)
        away_momentum = self._calculate_momentum(away_last_10, away_id)
        
        features.update({
            'home_momentum': home_momentum['score'],
            'home_momentum_trend': home_momentum['trend'],
            'away_momentum': away_momentum['score'],
            'away_momentum_trend': away_momentum['trend'],
            'momentum_diff': home_momentum['score'] - away_momentum['score'],
        })
        
        # 2. Form Streaks
        home_streak = self._get_streak(home_last_10, home_id)
        away_streak = self._get_streak(away_last_10, away_id)
        
        features.update({
            'home_win_streak': home_streak['win'],
            'home_unbeaten_streak': home_streak['unbeaten'],
            'home_winless_streak': home_streak['winless'],
            'away_win_streak': away_streak['win'],
            'away_unbeaten_streak': away_streak['unbeaten'],
            'away_winless_streak': away_streak['winless'],
        })
        
        # 3. Home/Away Specific Form
        home_at_home = self._venue_specific_form(home_last_10, home_id, 'home')
        away_at_away = self._venue_specific_form(away_last_10, away_id, 'away')
        
        features.update({
            'home_home_ppg': home_at_home['ppg'],
            'home_home_goals_for': home_at_home['goals_for'],
            'home_home_goals_against': home_at_home['goals_against'],
            'away_away_ppg': away_at_away['ppg'],
            'away_away_goals_for': away_at_away['goals_for'],
            'away_away_goals_against': away_at_away['goals_against'],
        })
        
        # 4. Rest Days (if fixture date available)
        if fixture_date:
            home_rest = self._calculate_rest_days(home_last_10, fixture_date, home_id)
            away_rest = self._calculate_rest_days(away_last_10, fixture_date, away_id)
            
            features.update({
                'home_rest_days': home_rest,
                'away_rest_days': away_rest,
                'rest_advantage': home_rest - away_rest,
            })
        else:
            features.update({
                'home_rest_days': 7,
                'away_rest_days': 7,
                'rest_advantage': 0,
            })
        
        # 5. Scoring Patterns
        home_scoring = self._scoring_patterns(home_last_10, home_id)
        away_scoring = self._scoring_patterns(away_last_10, away_id)
        
        features.update({
            'home_btts_rate': home_scoring['btts_rate'],
            'home_over25_rate': home_scoring['over25_rate'],
            'home_clean_sheet_rate': home_scoring['clean_sheet_rate'],
            'home_failed_to_score_rate': home_scoring['failed_to_score_rate'],
            'away_btts_rate': away_scoring['btts_rate'],
            'away_over25_rate': away_scoring['over25_rate'],
            'away_clean_sheet_rate': away_scoring['clean_sheet_rate'],
            'away_failed_to_score_rate': away_scoring['failed_to_score_rate'],
        })
        
        # 6. Season Phase (if date available)
        if fixture_date:
            phase = self._get_season_phase(fixture_date)
            features.update({
                'season_phase': phase['phase'],
                'is_early_season': phase['is_early'],
                'is_late_season': phase['is_late'],
            })
        else:
            features.update({
                'season_phase': 2,
                'is_early_season': 0,
                'is_late_season': 0,
            })
        
        # 7. Expected Goals proxies
        home_xg = self._estimate_xg_proxy(home_last_10, home_id)
        away_xg = self._estimate_xg_proxy(away_last_10, away_id)
        
        features.update({
            'home_xg_for_proxy': home_xg['xg_for'],
            'home_xg_against_proxy': home_xg['xg_against'],
            'away_xg_for_proxy': away_xg['xg_for'],
            'away_xg_against_proxy': away_xg['xg_against'],
        })
        
        # 8. Composite Strength Indices
        features.update({
            'home_attack_index': self._attack_index(features, 'home'),
            'home_defense_index': self._defense_index(features, 'home'),
            'away_attack_index': self._attack_index(features, 'away'),
            'away_defense_index': self._defense_index(features, 'away'),
        })
        
        return features
    
    def _calculate_momentum(self, matches_response, team_id):
        """
        Calculate momentum with exponential decay weighting.
        More recent matches count more.
        """
        if not matches_response or 'response' not in matches_response:
            return {'score': 0.5, 'trend': 0}
        
        matches = matches_response['response'][:10]
        if not matches:
            return {'score': 0.5, 'trend': 0}
        
        weighted_sum = 0
        weight_total = 0
        results = []
        
        for i, match in enumerate(matches):
            if match['goals']['home'] is None:
                continue
            
            is_home = match['teams']['home']['id'] == team_id
            gf = match['goals']['home'] if is_home else match['goals']['away']
            ga = match['goals']['away'] if is_home else match['goals']['home']
            
            # Points: 1.0 for win, 0.5 for draw, 0.0 for loss
            if gf > ga:
                result = 1.0
            elif gf == ga:
                result = 0.5
            else:
                result = 0.0
            
            results.append(result)
            
            # Exponential decay: more recent = higher weight
            weight = np.exp(-i * 0.2)  # decay factor
            weighted_sum += result * weight
            weight_total += weight
        
        momentum_score = weighted_sum / max(weight_total, 0.001)
        
        # Trend: compare first half vs second half
        if len(results) >= 4:
            recent = np.mean(results[:len(results)//2])
            older = np.mean(results[len(results)//2:])
            trend = recent - older  # Positive = improving
        else:
            trend = 0
        
        return {'score': round(momentum_score, 4), 'trend': round(trend, 4)}
    
    def _get_streak(self, matches_response, team_id):
        """Calculate current streaks"""
        streaks = {'win': 0, 'unbeaten': 0, 'winless': 0}
        
        if not matches_response or 'response' not in matches_response:
            return streaks
        
        matches = matches_response['response']
        
        win_streak = 0
        unbeaten_streak = 0
        winless_streak = 0
        
        for match in matches:
            if match['goals']['home'] is None:
                continue
            
            is_home = match['teams']['home']['id'] == team_id
            gf = match['goals']['home'] if is_home else match['goals']['away']
            ga = match['goals']['away'] if is_home else match['goals']['home']
            
            if gf > ga:  # Win
                if winless_streak == 0:
                    win_streak += 1
                    unbeaten_streak += 1
                else:
                    break
            elif gf == ga:  # Draw
                if win_streak > 0:
                    streaks['win'] = win_streak
                    win_streak = 0
                if winless_streak == 0:
                    unbeaten_streak += 1
                else:
                    winless_streak += 1
            else:  # Loss
                if win_streak > 0:
                    streaks['win'] = win_streak
                if unbeaten_streak > 0:
                    streaks['unbeaten'] = unbeaten_streak
                winless_streak += 1
                break
        
        if win_streak > 0:
            streaks['win'] = win_streak
        if unbeaten_streak > 0:
            streaks['unbeaten'] = unbeaten_streak
        if winless_streak > 0:
            streaks['winless'] = winless_streak
        
        return streaks
    
    def _venue_specific_form(self, matches_response, team_id, venue_type):
        """Get form specifically for home or away matches"""
        result = {'ppg': 1.0, 'goals_for': 1.0, 'goals_against': 1.0, 'matches': 0}
        
        if not matches_response or 'response' not in matches_response:
            return result
        
        points = 0
        goals_for = 0
        goals_against = 0
        count = 0
        
        for match in matches_response['response']:
            if match['goals']['home'] is None:
                continue
            
            is_home = match['teams']['home']['id'] == team_id
            
            # Filter by venue type
            if venue_type == 'home' and not is_home:
                continue
            if venue_type == 'away' and is_home:
                continue
            
            gf = match['goals']['home'] if is_home else match['goals']['away']
            ga = match['goals']['away'] if is_home else match['goals']['home']
            
            goals_for += gf
            goals_against += ga
            
            if gf > ga:
                points += 3
            elif gf == ga:
                points += 1
            
            count += 1
            if count >= 5:  # Last 5 venue-specific matches
                break
        
        if count > 0:
            result['ppg'] = round(points / count, 2)
            result['goals_for'] = round(goals_for / count, 2)
            result['goals_against'] = round(goals_against / count, 2)
            result['matches'] = count
        
        return result
    
    def _calculate_rest_days(self, matches_response, fixture_date, team_id):
        """Calculate days since last match"""
        if not matches_response or 'response' not in matches_response:
            return 7  # Default assumption
        
        matches = matches_response['response']
        if not matches:
            return 7
        
        try:
            if isinstance(fixture_date, str):
                fixture_dt = datetime.fromisoformat(fixture_date.replace('Z', '+00:00'))
            else:
                fixture_dt = fixture_date
            
            # Find most recent match
            for match in matches:
                match_date = match['fixture']['date']
                match_dt = datetime.fromisoformat(match_date.replace('Z', '+00:00'))
                if match_dt < fixture_dt:
                    rest_days = (fixture_dt - match_dt).days
                    return min(rest_days, 30)  # Cap at 30 days
            
            return 7
        except:
            return 7
    
    def _scoring_patterns(self, matches_response, team_id):
        """Analyze scoring patterns"""
        result = {
            'btts_rate': 0.5,
            'over25_rate': 0.5,
            'clean_sheet_rate': 0.3,
            'failed_to_score_rate': 0.2
        }
        
        if not matches_response or 'response' not in matches_response:
            return result
        
        matches = matches_response['response'][:10]
        if not matches:
            return result
        
        btts = 0
        over25 = 0
        clean_sheet = 0
        failed_to_score = 0
        count = 0
        
        for match in matches:
            if match['goals']['home'] is None:
                continue
            
            is_home = match['teams']['home']['id'] == team_id
            gf = match['goals']['home'] if is_home else match['goals']['away']
            ga = match['goals']['away'] if is_home else match['goals']['home']
            total = gf + ga
            
            if gf > 0 and ga > 0:
                btts += 1
            if total > 2.5:
                over25 += 1
            if ga == 0:
                clean_sheet += 1
            if gf == 0:
                failed_to_score += 1
            
            count += 1
        
        if count > 0:
            result['btts_rate'] = round(btts / count, 3)
            result['over25_rate'] = round(over25 / count, 3)
            result['clean_sheet_rate'] = round(clean_sheet / count, 3)
            result['failed_to_score_rate'] = round(failed_to_score / count, 3)
        
        return result
    
    def _get_season_phase(self, fixture_date):
        """Determine season phase (early/mid/late)"""
        try:
            if isinstance(fixture_date, str):
                dt = datetime.fromisoformat(fixture_date.replace('Z', '+00:00'))
            else:
                dt = fixture_date
            
            month = dt.month
            
            # Season typically Aug-May
            if month in [8, 9, 10]:  # Aug-Oct
                return {'phase': 1, 'is_early': 1, 'is_late': 0}
            elif month in [11, 12, 1, 2]:  # Nov-Feb
                return {'phase': 2, 'is_early': 0, 'is_late': 0}
            else:  # Mar-May
                return {'phase': 3, 'is_early': 0, 'is_late': 1}
        except:
            return {'phase': 2, 'is_early': 0, 'is_late': 0}
    
    def _estimate_xg_proxy(self, matches_response, team_id):
        """Estimate expected goals proxy from actual goals"""
        result = {'xg_for': 1.2, 'xg_against': 1.2}
        
        if not matches_response or 'response' not in matches_response:
            return result
        
        matches = matches_response['response'][:10]
        if not matches:
            return result
        
        gf_list = []
        ga_list = []
        
        for match in matches:
            if match['goals']['home'] is None:
                continue
            
            is_home = match['teams']['home']['id'] == team_id
            gf = match['goals']['home'] if is_home else match['goals']['away']
            ga = match['goals']['away'] if is_home else match['goals']['home']
            
            gf_list.append(gf)
            ga_list.append(ga)
        
        if gf_list:
            # Use trimmed mean as xG proxy (removes outliers)
            gf_sorted = sorted(gf_list)
            ga_sorted = sorted(ga_list)
            
            # Remove top and bottom 10%
            trim = max(1, len(gf_sorted) // 10)
            if len(gf_sorted) > 2:
                result['xg_for'] = round(np.mean(gf_sorted[trim:-trim or None]), 2)
                result['xg_against'] = round(np.mean(ga_sorted[trim:-trim or None]), 2)
            else:
                result['xg_for'] = round(np.mean(gf_sorted), 2)
                result['xg_against'] = round(np.mean(ga_sorted), 2)
        
        return result
    
    def _attack_index(self, features, prefix):
        """Composite attack strength index"""
        goals_avg = features.get(f'{prefix}_goals_for_avg', 1.0)
        form_goals = features.get(f'{prefix}_goals_for_last10', 10) / 10
        momentum = features.get(f'{prefix}_momentum', 0.5)
        
        return round((goals_avg * 0.4 + form_goals * 0.4 + momentum * 0.2) * 100, 1)
    
    def _defense_index(self, features, prefix):
        """Composite defense strength index (lower = better)"""
        goals_avg = features.get(f'{prefix}_goals_against_avg', 1.0)
        form_goals = features.get(f'{prefix}_goals_against_last10', 10) / 10
        clean_rate = features.get(f'{prefix}_clean_sheet_rate', 0.3)
        
        defense_score = goals_avg * 0.4 + form_goals * 0.4 - clean_rate * 0.2
        return round(defense_score * 100, 1)
