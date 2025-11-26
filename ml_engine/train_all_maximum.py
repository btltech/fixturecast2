#!/usr/bin/env python3
"""
MAXIMUM FEATURE training script for all ML models.
Uses ALL available data:
1. Match history (1,900 matches across 5 seasons)
2. Team statistics files (goals by minute, clean sheets, lineups, cards, etc.)

This extracts ~200+ features per match for maximum predictive power.
"""

import json
import logging
import os
import pickle
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Tuple

import numpy as np

# Add paths
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))


DATA_DIR = os.path.join(os.path.dirname(__file__), "../data/historical")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "trained_models")

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_team_stats():
    """
    Load team statistics from stats files.
    Returns: {season: {team_id: team_stats}}
    """
    all_stats = {}

    for year in [2020, 2021, 2022, 2023, 2024]:
        filepath = os.path.join(DATA_DIR, f"stats_{year}.json")
        if os.path.exists(filepath):
            with open(filepath) as f:
                season_stats = json.load(f)

            # Convert to team_id -> stats mapping
            stats_by_team = {}
            for team_id, data in season_stats.items():
                try:
                    team_data = data["response"]
                    stats_by_team[int(team_id)] = {
                        "form": team_data.get("form", ""),
                        "fixtures": team_data.get("fixtures", {}),
                        "goals_for": team_data.get("goals", {}).get("for", {}),
                        "goals_against": team_data.get("goals", {}).get("against", {}),
                        "biggest": team_data.get("biggest", {}),
                        "clean_sheet": team_data.get("clean_sheet", {}),
                        "failed_to_score": team_data.get("failed_to_score", {}),
                        "penalty": team_data.get("penalty", {}),
                        "lineups": team_data.get("lineups", []),
                        "cards": team_data.get("cards", {}),
                    }
                except (KeyError, TypeError):
                    continue

            all_stats[year] = stats_by_team
            print(f"  Loaded stats for {len(stats_by_team)} teams from {year}")

    return all_stats


def extract_seasonal_features(team_stats):
    """
    Extract all possible features from team seasonal stats.
    Returns a dict of numeric features.
    """
    features = {}

    if not team_stats:
        # Return default neutral features
        return {
            "stat_home_win_rate": 0.4,
            "stat_away_win_rate": 0.3,
            "stat_home_draw_rate": 0.3,
            "stat_away_draw_rate": 0.3,
            "stat_goals_for_home_avg": 1.3,
            "stat_goals_for_away_avg": 1.0,
            "stat_goals_against_home_avg": 1.0,
            "stat_goals_against_away_avg": 1.3,
            "stat_clean_sheet_home_rate": 0.3,
            "stat_clean_sheet_away_rate": 0.2,
            "stat_failed_to_score_home_rate": 0.2,
            "stat_failed_to_score_away_rate": 0.3,
            "stat_penalty_success_rate": 0.75,
            "stat_biggest_win_streak": 3,
            "stat_biggest_lose_streak": 2,
            "stat_goals_0_15_pct": 0.1,
            "stat_goals_16_30_pct": 0.15,
            "stat_goals_31_45_pct": 0.15,
            "stat_goals_46_60_pct": 0.2,
            "stat_goals_61_75_pct": 0.2,
            "stat_goals_76_90_pct": 0.2,
            "stat_conceded_0_15_pct": 0.1,
            "stat_conceded_46_60_pct": 0.2,
            "stat_conceded_76_90_pct": 0.2,
            "stat_yellow_cards_per_game": 2.0,
            "stat_red_cards_per_game": 0.1,
            "stat_primary_formation": 0,
            "stat_form_win_pct": 0.4,
            "stat_form_recent_win_pct": 0.4,
        }

    # FIXTURES DATA
    fixtures = team_stats.get("fixtures", {})
    played = fixtures.get("played", {})
    wins = fixtures.get("wins", {})
    draws = fixtures.get("draws", {})
    loses = fixtures.get("loses", {})

    total_played = played.get("total", 38) or 38
    home_played = played.get("home", 19) or 19
    away_played = played.get("away", 19) or 19

    # Win/draw/loss rates by venue
    features["stat_home_win_rate"] = (wins.get("home", 0) or 0) / home_played
    features["stat_away_win_rate"] = (wins.get("away", 0) or 0) / away_played
    features["stat_home_draw_rate"] = (draws.get("home", 0) or 0) / home_played
    features["stat_away_draw_rate"] = (draws.get("away", 0) or 0) / away_played
    features["stat_home_loss_rate"] = (loses.get("home", 0) or 0) / home_played
    features["stat_away_loss_rate"] = (loses.get("away", 0) or 0) / away_played
    features["stat_total_wins"] = wins.get("total", 0) or 0
    features["stat_total_draws"] = draws.get("total", 0) or 0
    features["stat_total_losses"] = loses.get("total", 0) or 0

    # GOALS FOR DATA
    goals_for = team_stats.get("goals_for", {})
    gf_total = goals_for.get("total", {})
    gf_avg = goals_for.get("average", {})
    gf_minute = goals_for.get("minute", {})
    gf_under_over = goals_for.get("under_over", {})

    features["stat_goals_for_home_avg"] = float(gf_avg.get("home", "1.3") or "1.3")
    features["stat_goals_for_away_avg"] = float(gf_avg.get("away", "1.0") or "1.0")
    features["stat_goals_for_total"] = gf_total.get("total", 50) or 50

    # Goals by minute period (for scoring patterns)
    for period in ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "91-105"]:
        period_data = gf_minute.get(period, {})
        pct_str = period_data.get("percentage", "0%") or "0%"
        try:
            pct = float(pct_str.replace("%", "")) / 100
        except (ValueError, AttributeError):
            pct = 0
        period_key = period.replace("-", "_")
        features[f"stat_goals_{period_key}_pct"] = pct

    # Over/under rates
    for threshold in ["0.5", "1.5", "2.5", "3.5"]:
        uo_data = gf_under_over.get(threshold, {})
        over = uo_data.get("over", 0) or 0
        features[f'stat_goals_over_{threshold.replace(".", "")}'] = over / total_played

    # GOALS AGAINST DATA
    goals_against = team_stats.get("goals_against", {})
    ga_total = goals_against.get("total", {})
    ga_avg = goals_against.get("average", {})
    ga_minute = goals_against.get("minute", {})

    features["stat_goals_against_home_avg"] = float(ga_avg.get("home", "1.0") or "1.0")
    features["stat_goals_against_away_avg"] = float(ga_avg.get("away", "1.3") or "1.3")
    features["stat_goals_against_total"] = ga_total.get("total", 50) or 50

    # Conceded by minute period
    for period in ["0-15", "46-60", "76-90"]:  # Key periods for conceding
        period_data = ga_minute.get(period, {})
        pct_str = period_data.get("percentage", "0%") or "0%"
        try:
            pct = float(pct_str.replace("%", "")) / 100
        except (ValueError, AttributeError):
            pct = 0
        period_key = period.replace("-", "_")
        features[f"stat_conceded_{period_key}_pct"] = pct

    # BIGGEST WINS/LOSSES
    biggest = team_stats.get("biggest", {})
    streak = biggest.get("streak", {})
    goals_biggest = biggest.get("goals", {})

    features["stat_biggest_win_streak"] = streak.get("wins", 1) or 1
    features["stat_biggest_lose_streak"] = streak.get("loses", 1) or 1
    features["stat_biggest_draw_streak"] = streak.get("draws", 1) or 1
    features["stat_biggest_goals_for_home"] = goals_biggest.get("for", {}).get("home", 3) or 3
    features["stat_biggest_goals_for_away"] = goals_biggest.get("for", {}).get("away", 2) or 2
    features["stat_biggest_goals_against_home"] = (
        goals_biggest.get("against", {}).get("home", 3) or 3
    )
    features["stat_biggest_goals_against_away"] = (
        goals_biggest.get("against", {}).get("away", 4) or 4
    )

    # CLEAN SHEET DATA
    clean_sheet = team_stats.get("clean_sheet", {})
    features["stat_clean_sheet_home_rate"] = (clean_sheet.get("home", 0) or 0) / home_played
    features["stat_clean_sheet_away_rate"] = (clean_sheet.get("away", 0) or 0) / away_played
    features["stat_clean_sheet_total"] = clean_sheet.get("total", 10) or 10

    # FAILED TO SCORE DATA
    fts = team_stats.get("failed_to_score", {})
    features["stat_failed_to_score_home_rate"] = (fts.get("home", 0) or 0) / home_played
    features["stat_failed_to_score_away_rate"] = (fts.get("away", 0) or 0) / away_played
    features["stat_failed_to_score_total"] = fts.get("total", 8) or 8

    # PENALTY DATA
    penalty = team_stats.get("penalty", {})
    scored = penalty.get("scored", {})
    missed = penalty.get("missed", {})
    pen_total = scored.get("total", 0) or 0
    pen_scored = pen_total
    pen_missed = missed.get("total", 0) or 0
    if pen_scored + pen_missed > 0:
        features["stat_penalty_success_rate"] = pen_scored / (pen_scored + pen_missed)
    else:
        features["stat_penalty_success_rate"] = 0.75
    features["stat_penalties_taken"] = pen_scored + pen_missed

    # LINEUPS/FORMATIONS
    lineups = team_stats.get("lineups", [])
    if lineups:
        # Encode primary formation as a categorical
        formation_map = {
            "4-3-3": 1,
            "4-4-2": 2,
            "3-4-3": 3,
            "4-2-3-1": 4,
            "3-5-2": 5,
            "4-1-4-1": 6,
            "5-3-2": 7,
            "3-4-2-1": 8,
            "4-5-1": 9,
            "5-4-1": 10,
        }
        primary_formation = lineups[0].get("formation", "4-3-3") if lineups else "4-3-3"
        features["stat_primary_formation"] = formation_map.get(primary_formation, 0)
        features["stat_formation_consistency"] = (
            lineups[0].get("played", 20) / total_played if lineups else 0.5
        )
    else:
        features["stat_primary_formation"] = 0
        features["stat_formation_consistency"] = 0.5

    # CARDS DATA
    cards = team_stats.get("cards", {})
    yellow = cards.get("yellow", {})
    red = cards.get("red", {})

    total_yellow = sum(
        (yellow.get(period, {}).get("total", 0) or 0)
        for period in ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "91-105"]
    )
    total_red = sum(
        (red.get(period, {}).get("total", 0) or 0)
        for period in ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "91-105"]
    )

    features["stat_yellow_cards_per_game"] = total_yellow / total_played
    features["stat_red_cards_per_game"] = total_red / total_played

    # FORM STRING ANALYSIS
    form_str = team_stats.get("form", "")
    if form_str:
        wins_in_form = form_str.count("W")
        draws_in_form = form_str.count("D")
        losses_in_form = form_str.count("L")
        total_form = len(form_str)
        if total_form > 0:
            features["stat_form_win_pct"] = wins_in_form / total_form
            features["stat_form_draw_pct"] = draws_in_form / total_form
            features["stat_form_loss_pct"] = losses_in_form / total_form

        # Recent form (last 10)
        recent = form_str[-10:] if len(form_str) >= 10 else form_str
        if recent:
            features["stat_form_recent_win_pct"] = recent.count("W") / len(recent)
            features["stat_form_recent_draw_pct"] = recent.count("D") / len(recent)
            features["stat_form_recent_loss_pct"] = recent.count("L") / len(recent)
    else:
        features["stat_form_win_pct"] = 0.4
        features["stat_form_draw_pct"] = 0.3
        features["stat_form_loss_pct"] = 0.3
        features["stat_form_recent_win_pct"] = 0.4
        features["stat_form_recent_draw_pct"] = 0.3
        features["stat_form_recent_loss_pct"] = 0.3

    return features


def load_all_matches():
    """Load all historical matches from season files"""
    matches = []
    for filename in sorted(os.listdir(DATA_DIR)):
        if filename.startswith("season_") and filename.endswith(".json"):
            filepath = os.path.join(DATA_DIR, filename)
            with open(filepath) as f:
                season_matches = json.load(f)
                matches.extend(season_matches)
    matches.sort(key=lambda x: x["fixture"]["date"])
    return matches


def build_features_and_labels(matches, team_stats_by_season):
    """
    Build training data with MAXIMUM features:
    1. Progressive match-by-match tracking (~70 features)
    2. Season-level team stats (~50 features per team, 100 total)

    Returns (X, y) where X is list of feature dicts and y is list of outcomes.
    """
    X = []
    y = []

    # Track progressive stats as season goes
    team_progressive = {}
    h2h_stats = {}

    def init_progressive_stats():
        return {
            "points": 0,
            "played": 0,
            "form": [],
            "gf": 0,
            "ga": 0,
            "gf_home": 0,
            "ga_home": 0,
            "gf_away": 0,
            "ga_away": 0,
            "home_played": 0,
            "away_played": 0,
            "home_wins": 0,
            "home_draws": 0,
            "home_losses": 0,
            "away_wins": 0,
            "away_draws": 0,
            "away_losses": 0,
            "clean_sheets": 0,
            "clean_sheets_home": 0,
            "clean_sheets_away": 0,
            "failed_to_score": 0,
            "failed_to_score_home": 0,
            "failed_to_score_away": 0,
            "goals_scored_history": [],
            "goals_conceded_history": [],
            "win_streak": 0,
            "loss_streak": 0,
            "unbeaten_streak": 0,
            "winless_streak": 0,
            "btts_count": 0,
            "over25_count": 0,
        }

    print(f"\nBuilding MAXIMUM features from {len(matches)} matches...")
    print("  - Using progressive match-by-match stats")
    print("  - Using seasonal team statistics")

    current_season = None

    for idx, match in enumerate(matches):
        # Get season from match date
        date_str = match["fixture"]["date"]
        year = int(date_str[:4])
        month = int(date_str[5:7])
        # Season is Aug-May, so Aug-Dec is current year, Jan-May is previous year's season
        if month >= 8:
            season = year
        else:
            season = year - 1

        # Reset progressive stats at season start
        if season != current_season:
            team_progressive = {}
            h2h_stats = {}
            current_season = season
            print(f"  Starting season {season}...")

        home_id = match["teams"]["home"]["id"]
        away_id = match["teams"]["away"]["id"]

        # Initialize progressive stats if needed
        if home_id not in team_progressive:
            team_progressive[home_id] = init_progressive_stats()
        if away_id not in team_progressive:
            team_progressive[away_id] = init_progressive_stats()

        hs = team_progressive[home_id]
        aws = team_progressive[away_id]

        # ========== PROGRESSIVE FEATURES (70+) ==========
        features = build_progressive_features(
            hs, aws, home_id, away_id, match, h2h_stats, team_progressive
        )

        # ========== SEASONAL STATS FEATURES (100+) ==========
        # Get stats for previous season (what we'd know before this match)
        prev_season = season - 1
        season_stats = team_stats_by_season.get(prev_season, {})

        home_seasonal = extract_seasonal_features(season_stats.get(home_id))
        away_seasonal = extract_seasonal_features(season_stats.get(away_id))

        # Add prefixed seasonal features for both teams
        for key, val in home_seasonal.items():
            features[f"home_{key}"] = val
        for key, val in away_seasonal.items():
            features[f"away_{key}"] = val

        # ========== DERIVED CROSS-FEATURES ==========
        features["seasonal_attack_vs_defense"] = home_seasonal.get(
            "stat_goals_for_home_avg", 1.3
        ) - away_seasonal.get("stat_goals_against_away_avg", 1.0)
        features["seasonal_defense_vs_attack"] = home_seasonal.get(
            "stat_goals_against_home_avg", 1.0
        ) - away_seasonal.get("stat_goals_for_away_avg", 1.0)
        features["seasonal_form_diff"] = home_seasonal.get(
            "stat_form_win_pct", 0.4
        ) - away_seasonal.get("stat_form_win_pct", 0.4)
        features["seasonal_clean_sheet_diff"] = home_seasonal.get(
            "stat_clean_sheet_home_rate", 0.3
        ) - away_seasonal.get("stat_clean_sheet_away_rate", 0.2)

        X.append(features)

        # ========== GET OUTCOME AND UPDATE STATS ==========
        goals_home = match["goals"]["home"] or 0
        goals_away = match["goals"]["away"] or 0
        goals_home + goals_away

        if goals_home > goals_away:
            outcome = 0  # Home win
        elif goals_home < goals_away:
            outcome = 2  # Away win
        else:
            outcome = 1  # Draw

        y.append(outcome)

        # Update progressive stats
        update_progressive_stats(hs, aws, goals_home, goals_away, h2h_stats, home_id, away_id)

    print(f"\nFeatures per match: {len(X[0]) if X else 0}")
    return X, y


def build_progressive_features(hs, aws, home_id, away_id, match, h2h_stats, team_progressive):
    """Build features from progressive match-by-match tracking"""

    home_form = hs["form"][-10:] if hs["form"] else []
    away_form = aws["form"][-10:] if aws["form"] else []
    home_form_5 = hs["form"][-5:] if hs["form"] else []
    away_form_5 = aws["form"][-5:] if aws["form"] else []

    home_played = max(hs["played"], 1)
    away_played = max(aws["played"], 1)
    home_home_played = max(hs["home_played"], 1)
    away_away_played = max(aws["away_played"], 1)

    # Points per game
    home_ppg = hs["points"] / home_played
    away_ppg = aws["points"] / away_played
    home_ppg_home = (hs["home_wins"] * 3 + hs["home_draws"]) / home_home_played
    away_ppg_away = (aws["away_wins"] * 3 + aws["away_draws"]) / away_away_played

    # Goal averages
    home_gf_avg = hs["gf"] / home_played
    home_ga_avg = hs["ga"] / home_played
    away_gf_avg = aws["gf"] / away_played
    away_ga_avg = aws["ga"] / away_played

    # Venue-specific
    home_gf_home_avg = hs["gf_home"] / home_home_played
    home_ga_home_avg = hs["ga_home"] / home_home_played
    away_gf_away_avg = aws["gf_away"] / away_away_played
    away_ga_away_avg = aws["ga_away"] / away_away_played

    # Goal difference
    home_gd = hs["gf"] - hs["ga"]
    away_gd = aws["gf"] - aws["ga"]

    # Win rates
    home_win_rate = (hs["home_wins"] + hs["away_wins"]) / home_played
    away_win_rate = (aws["home_wins"] + aws["away_wins"]) / away_played
    home_home_win_rate = hs["home_wins"] / home_home_played
    away_away_win_rate = aws["away_wins"] / away_away_played

    # Clean sheet rates
    home_cs_rate = hs["clean_sheets"] / home_played
    away_cs_rate = aws["clean_sheets"] / away_played

    # Recent goals
    home_recent_gf = sum(hs["goals_scored_history"][-5:]) if hs["goals_scored_history"] else 0
    away_recent_gf = sum(aws["goals_scored_history"][-5:]) if aws["goals_scored_history"] else 0

    # H2H
    h2h_key = tuple(sorted([home_id, away_id]))
    if h2h_key not in h2h_stats:
        h2h_stats[h2h_key] = {"home_wins": 0, "away_wins": 0, "draws": 0, "total": 0}
    h2h = h2h_stats[h2h_key]

    # League position estimate
    all_points = [(tid, ts["points"]) for tid, ts in team_progressive.items() if ts["played"] > 0]
    all_points.sort(key=lambda x: -x[1])
    home_pos = next((i + 1 for i, (tid, _) in enumerate(all_points) if tid == home_id), 10)
    away_pos = next((i + 1 for i, (tid, _) in enumerate(all_points) if tid == away_id), 10)

    return {
        # Team IDs (for categorical encoding)
        "home_id": home_id,
        "away_id": away_id,
        # League position
        "home_league_pos": home_pos,
        "away_league_pos": away_pos,
        "position_diff": home_pos - away_pos,
        # Points
        "home_league_points": hs["points"],
        "away_league_points": aws["points"],
        "points_diff": hs["points"] - aws["points"],
        "home_ppg": round(home_ppg, 3),
        "away_ppg": round(away_ppg, 3),
        "home_ppg_home": round(home_ppg_home, 3),
        "away_ppg_away": round(away_ppg_away, 3),
        # Form (last 10)
        "home_points_last10": sum(home_form) if home_form else 15,
        "away_points_last10": sum(away_form) if away_form else 15,
        "home_wins_last10": sum(1 for p in home_form if p == 3),
        "away_wins_last10": sum(1 for p in away_form if p == 3),
        "home_draws_last10": sum(1 for p in home_form if p == 1),
        "away_draws_last10": sum(1 for p in away_form if p == 1),
        "home_losses_last10": sum(1 for p in home_form if p == 0),
        "away_losses_last10": sum(1 for p in away_form if p == 0),
        # Form (last 5)
        "home_form_last5": sum(home_form_5) if home_form_5 else 7,
        "away_form_last5": sum(away_form_5) if away_form_5 else 7,
        "home_wins_last5": sum(1 for p in home_form_5 if p == 3),
        "away_wins_last5": sum(1 for p in away_form_5 if p == 3),
        # Goals
        "home_goals_for_avg": round(home_gf_avg, 3),
        "away_goals_for_avg": round(away_gf_avg, 3),
        "home_goals_against_avg": round(home_ga_avg, 3),
        "away_goals_against_avg": round(away_ga_avg, 3),
        "home_gf_home_avg": round(home_gf_home_avg, 3),
        "home_ga_home_avg": round(home_ga_home_avg, 3),
        "away_gf_away_avg": round(away_gf_away_avg, 3),
        "away_ga_away_avg": round(away_ga_away_avg, 3),
        # Goal difference
        "home_gd": home_gd,
        "away_gd": away_gd,
        "home_gd_per_game": round(home_gd / home_played, 3),
        "away_gd_per_game": round(away_gd / away_played, 3),
        # Recent goals
        "home_goals_for_last5": home_recent_gf,
        "away_goals_for_last5": away_recent_gf,
        # Win rates
        "home_win_rate": round(home_win_rate, 3),
        "away_win_rate": round(away_win_rate, 3),
        "home_home_win_rate": round(home_home_win_rate, 3),
        "away_away_win_rate": round(away_away_win_rate, 3),
        # Clean sheets
        "home_clean_sheet_rate": round(home_cs_rate, 3),
        "away_clean_sheet_rate": round(away_cs_rate, 3),
        # Failed to score
        "home_fts_rate": round(hs["failed_to_score"] / home_played, 3),
        "away_fts_rate": round(aws["failed_to_score"] / away_played, 3),
        # BTTS and Over 2.5
        "home_btts_rate": round(hs["btts_count"] / home_played, 3),
        "away_btts_rate": round(aws["btts_count"] / away_played, 3),
        "home_over25_rate": round(hs["over25_count"] / home_played, 3),
        "away_over25_rate": round(aws["over25_count"] / away_played, 3),
        # Streaks
        "home_win_streak": hs["win_streak"],
        "away_win_streak": aws["win_streak"],
        "home_loss_streak": hs["loss_streak"],
        "away_loss_streak": aws["loss_streak"],
        "home_unbeaten_streak": hs["unbeaten_streak"],
        "away_unbeaten_streak": aws["unbeaten_streak"],
        # H2H
        "h2h_home_wins": h2h["home_wins"] if home_id < away_id else h2h["away_wins"],
        "h2h_away_wins": h2h["away_wins"] if home_id < away_id else h2h["home_wins"],
        "h2h_draws": h2h["draws"],
        "h2h_total_matches": h2h["total"],
        # Match context
        "home_total_matches": home_played,
        "away_total_matches": away_played,
    }


def update_progressive_stats(hs, aws, goals_home, goals_away, h2h_stats, home_id, away_id):
    """Update progressive stats after a match"""
    total_goals = goals_home + goals_away

    if goals_home > goals_away:
        # Home win
        hs["points"] += 3
        hs["form"].append(3)
        aws["form"].append(0)
        hs["home_wins"] += 1
        aws["away_losses"] += 1
        hs["win_streak"] += 1
        hs["loss_streak"] = 0
        hs["unbeaten_streak"] += 1
        hs["winless_streak"] = 0
        aws["win_streak"] = 0
        aws["loss_streak"] += 1
        aws["unbeaten_streak"] = 0
        aws["winless_streak"] += 1
    elif goals_home < goals_away:
        # Away win
        aws["points"] += 3
        hs["form"].append(0)
        aws["form"].append(3)
        hs["home_losses"] += 1
        aws["away_wins"] += 1
        hs["win_streak"] = 0
        hs["loss_streak"] += 1
        hs["unbeaten_streak"] = 0
        hs["winless_streak"] += 1
        aws["win_streak"] += 1
        aws["loss_streak"] = 0
        aws["unbeaten_streak"] += 1
        aws["winless_streak"] = 0
    else:
        # Draw
        hs["points"] += 1
        aws["points"] += 1
        hs["form"].append(1)
        aws["form"].append(1)
        hs["home_draws"] += 1
        aws["away_draws"] += 1
        hs["win_streak"] = 0
        aws["win_streak"] = 0
        hs["unbeaten_streak"] += 1
        aws["unbeaten_streak"] += 1
        hs["winless_streak"] += 1
        aws["winless_streak"] += 1

    # Update goals
    hs["gf"] += goals_home
    hs["ga"] += goals_away
    aws["gf"] += goals_away
    aws["ga"] += goals_home
    hs["gf_home"] += goals_home
    hs["ga_home"] += goals_away
    aws["gf_away"] += goals_away
    aws["ga_away"] += goals_home

    # Update history
    hs["goals_scored_history"].append(goals_home)
    hs["goals_conceded_history"].append(goals_away)
    aws["goals_scored_history"].append(goals_away)
    aws["goals_conceded_history"].append(goals_home)

    # Update played
    hs["played"] += 1
    aws["played"] += 1
    hs["home_played"] += 1
    aws["away_played"] += 1

    # Clean sheets
    if goals_away == 0:
        hs["clean_sheets"] += 1
        hs["clean_sheets_home"] += 1
    if goals_home == 0:
        aws["clean_sheets"] += 1
        aws["clean_sheets_away"] += 1

    # Failed to score
    if goals_home == 0:
        hs["failed_to_score"] += 1
        hs["failed_to_score_home"] += 1
    if goals_away == 0:
        aws["failed_to_score"] += 1
        aws["failed_to_score_away"] += 1

    # BTTS and over 2.5
    if goals_home > 0 and goals_away > 0:
        hs["btts_count"] += 1
        aws["btts_count"] += 1
    if total_goals > 2:
        hs["over25_count"] += 1
        aws["over25_count"] += 1

    # H2H
    h2h_key = tuple(sorted([home_id, away_id]))
    if h2h_key not in h2h_stats:
        h2h_stats[h2h_key] = {"home_wins": 0, "away_wins": 0, "draws": 0, "total": 0}
    h2h = h2h_stats[h2h_key]

    if goals_home > goals_away:
        if home_id < away_id:
            h2h["home_wins"] += 1
        else:
            h2h["away_wins"] += 1
    elif goals_home < goals_away:
        if away_id < home_id:
            h2h["home_wins"] += 1
        else:
            h2h["away_wins"] += 1
    else:
        h2h["draws"] += 1
    h2h["total"] += 1


def train_all_models(X, y):
    """Train all 11 models with maximum features - PARALLEL VERSION"""
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.preprocessing import StandardScaler

    print("\n" + "=" * 70)
    print("TRAINING ALL 11 MODELS WITH MAXIMUM FEATURES (PARALLEL)")
    print("=" * 70)

    start_time = time.time()

    # Vectorize features
    vec = DictVectorizer(sparse=False)
    X_vec = vec.fit_transform(X)
    feature_names = vec.get_feature_names_out()

    print(f"\nTotal features after vectorization: {len(feature_names)}")
    print(f"Training samples: {len(y)}")

    # Class distribution
    from collections import Counter

    dist = Counter(y)
    print(f"Class distribution: Home={dist[0]}, Draw={dist[1]}, Away={dist[2]}")

    # Scale features
    scaler = StandardScaler()
    scaler.fit_transform(X_vec)
    y_np = np.array(y)

    # Create models directory
    os.makedirs(MODELS_DIR, exist_ok=True)

    # Save vectorizer, scaler, and feature names
    with open(os.path.join(MODELS_DIR, "feature_vectorizer.pkl"), "wb") as f:
        pickle.dump(vec, f)
    with open(os.path.join(MODELS_DIR, "feature_scaler.pkl"), "wb") as f:
        pickle.dump(scaler, f)
    with open(os.path.join(MODELS_DIR, "feature_names.pkl"), "wb") as f:
        pickle.dump(list(feature_names), f)

    print(f"\nSaved feature vectorizer ({len(feature_names)} features)")
    print(f"Saved feature scaler")

    # Prepare feature subsets for specialized models
    form_features = extract_subset_features(X, "form")
    form_vec = DictVectorizer(sparse=False)
    X_form = form_vec.fit_transform(form_features)

    trend_features = extract_subset_features(X, "trend")
    trend_vec = DictVectorizer(sparse=False)
    X_trend = trend_vec.fit_transform(trend_features)

    context_features = extract_subset_features(X, "context")
    context_vec = DictVectorizer(sparse=False)
    X_context = context_vec.fit_transform(context_features)

    rate_features = extract_subset_features(X, "rate")
    rate_vec = DictVectorizer(sparse=False)
    X_rate = rate_vec.fit_transform(rate_features)

    elo_features = extract_subset_features(X, "elo")
    elo_vec = DictVectorizer(sparse=False)
    X_elo = elo_vec.fit_transform(elo_features)

    # Save all vectorizers
    vectorizers = {
        "transformer": form_vec,
        "lstm": trend_vec,
        "gnn": context_vec,
        "bayesian": rate_vec,
        "elo": elo_vec,
        "gbdt": vec,
        "catboost": vec,
    }
    for name, v in vectorizers.items():
        with open(os.path.join(MODELS_DIR, f"{name}_vectorizer.pkl"), "wb") as f:
            pickle.dump(v, f)

    print("\n" + "-" * 50)
    print("Training models in parallel...")

    # Define training tasks
    training_tasks = [
        ("GBDT", "gbdt", X_vec, y_np, vec),
        ("CatBoost", "catboost", X_vec, y_np, vec),
        ("Transformer", "transformer", X_form, y_np, form_vec),
        ("LSTM", "lstm", X_trend, y_np, trend_vec),
        ("GNN", "gnn", X_context, y_np, context_vec),
        ("Bayesian", "bayesian", X_rate, y_np, rate_vec),
        ("Elo", "elo", X_elo, y_np, elo_vec),
    ]

    # Train models in parallel using ThreadPoolExecutor
    trained_models = {}
    max_workers = min(4, len(training_tasks))  # Limit parallelism for memory

    print(f"Using {max_workers} parallel workers")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_name = {}

        for name, model_type, X_train, y_train, vectorizer in training_tasks:
            future = executor.submit(
                _train_single_model, name, model_type, X_train, y_train, vectorizer
            )
            future_to_name[future] = name

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                model_type, model, train_time = future.result()
                trained_models[model_type] = model
                print(f"   ✓ {name} trained in {train_time:.1f}s with {X_train.shape[1]} features")
            except Exception as e:
                logger.error(f"Failed to train {name}: {e}")
                raise

    # Sequential training for models that need special handling
    print("\nTraining sequential models...")

    # 8. Poisson Model
    print("   Training Poisson Model...")
    from ml_engine.poisson_model import PoissonModel

    poisson = PoissonModel()
    poisson.train(X, y)
    poisson.save(os.path.join(MODELS_DIR, "poisson_model.pkl"))
    trained_models["poisson"] = poisson
    print(f"   ✓ Poisson trained with goal scoring features")

    # 9. Monte Carlo Model
    print("   Training Monte Carlo Model...")
    from ml_engine.monte_carlo import MonteCarloSimulator

    mc = MonteCarloSimulator()
    mc.build_from_matches(X)
    mc.save(os.path.join(MODELS_DIR, "monte_carlo_model.pkl"))
    trained_models["mc"] = mc
    print(f"   ✓ Monte Carlo configured")

    # 10. Calibration
    print("   Training Calibration...")
    from ml_engine.calibration import ProbabilityCalibrator

    calibrator = ProbabilityCalibrator()
    gbdt = trained_models["gbdt"]
    gbdt_probs = gbdt.predict_proba(X_vec)
    calibrator.train(gbdt_probs, y_np)
    calibrator.save(os.path.join(MODELS_DIR, "calibrator.pkl"))
    print(f"   ✓ Calibrator trained")

    # 11. Meta Model (requires all other models to be trained first)
    print("   Training Meta Model...")
    meta_X = collect_meta_features(
        X,
        X_vec,
        X_form,
        X_trend,
        X_context,
        X_rate,
        X_elo,
        trained_models["gbdt"],
        trained_models["catboost"],
        trained_models["transformer"],
        trained_models["lstm"],
        trained_models["gnn"],
        trained_models["bayesian"],
        trained_models["elo"],
        trained_models["poisson"],
        y_np,
    )
    train_meta_model(meta_X, y_np)
    print(f"   ✓ Meta model trained with {meta_X.shape[1]} stacked features")

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"✅ ALL 11 MODELS TRAINED SUCCESSFULLY in {elapsed:.1f}s")
    print("=" * 70)


def _train_single_model(
    name: str, model_type: str, X_train: np.ndarray, y_train: np.ndarray, vectorizer
) -> Tuple[str, Any, float]:
    """
    Train a single model (used for parallel training).
    Returns: (model_type, trained_model, training_time)
    """
    start = time.time()

    if model_type == "gbdt":
        from ml_engine.gbdt_model import GBDTModel

        model = GBDTModel()
        model.train(X_train, y_train)
        model.save(os.path.join(MODELS_DIR, "gbdt_model.pkl"))

    elif model_type == "catboost":
        from ml_engine.catboost_model import CatBoostModel

        model = CatBoostModel()
        model.train(X_train, y_train)
        model.save(os.path.join(MODELS_DIR, "catboost_model.pkl"))

    elif model_type == "transformer":
        from ml_engine.transformer_model import TransformerSequenceModel

        model = TransformerSequenceModel()
        model.train(X_train, y_train)
        model.save(os.path.join(MODELS_DIR, "transformer_model.pkl"))

    elif model_type == "lstm":
        from ml_engine.lstm_model import LSTMSequenceModel

        model = LSTMSequenceModel()
        model.train(X_train, y_train)
        model.save(os.path.join(MODELS_DIR, "lstm_model.pkl"))

    elif model_type == "gnn":
        from ml_engine.gnn_model import GNNModel

        model = GNNModel()
        model.train(X_train, y_train)
        model.save(os.path.join(MODELS_DIR, "gnn_model.pkl"))

    elif model_type == "bayesian":
        from ml_engine.bayesian_model import BayesianModel

        model = BayesianModel()
        model.train(X_train, y_train)
        model.save(os.path.join(MODELS_DIR, "bayesian_model.pkl"))

    elif model_type == "elo":
        from ml_engine.elo_model import EloGlickoModel

        model = EloGlickoModel()
        model.train(X_train, y_train)
        model.save(os.path.join(MODELS_DIR, "elo_model.pkl"))
    else:
        raise ValueError(f"Unknown model type: {model_type}")

    elapsed = time.time() - start
    return model_type, model, elapsed


def extract_subset_features(X, subset_type):
    """Extract specific feature subsets for specialized models"""
    result = []

    for feat in X:
        subset = {}

        if subset_type == "form":
            # Form and momentum features
            keys = [
                k
                for k in feat.keys()
                if any(
                    x in k.lower()
                    for x in ["form", "last5", "last10", "streak", "momentum", "ppg", "recent"]
                )
            ]
            for k in keys:
                subset[k] = feat[k]

        elif subset_type == "trend":
            # Trend features (goals, GD, rates over time)
            keys = [
                k
                for k in feat.keys()
                if any(
                    x in k.lower()
                    for x in ["goals", "gd", "gf", "ga", "last5", "last10", "history", "avg"]
                )
            ]
            for k in keys:
                subset[k] = feat[k]

        elif subset_type == "context":
            # League context features
            keys = [
                k
                for k in feat.keys()
                if any(
                    x in k.lower()
                    for x in ["pos", "points", "league", "played", "total", "h2h", "matches"]
                )
            ]
            for k in keys:
                subset[k] = feat[k]

        elif subset_type == "rate":
            # Rate-based features
            keys = [
                k
                for k in feat.keys()
                if any(
                    x in k.lower()
                    for x in [
                        "rate",
                        "pct",
                        "avg",
                        "per_game",
                        "clean_sheet",
                        "fts",
                        "btts",
                        "over",
                    ]
                )
            ]
            for k in keys:
                subset[k] = feat[k]

        elif subset_type == "elo":
            # Elo-relevant features
            keys = [
                k
                for k in feat.keys()
                if any(
                    x in k.lower()
                    for x in ["home_id", "away_id", "pos", "points", "win_rate", "ppg", "diff"]
                )
            ]
            for k in keys:
                subset[k] = feat[k]

        result.append(subset)

    return result


def collect_meta_features(
    X,
    X_vec,
    X_form,
    X_trend,
    X_context,
    X_rate,
    X_elo,
    gbdt,
    catboost,
    transformer,
    lstm,
    gnn,
    bayesian,
    elo,
    poisson,
    y,
):
    """Collect predictions from all base models for meta-model training"""

    n_samples = len(y)
    meta_features = []

    # Get probabilities from each model
    gbdt_probs = gbdt.predict_proba(X_vec)
    cat_probs = catboost.predict_proba(X_vec)
    trans_probs = transformer.predict_proba(X_form)
    lstm_probs = lstm.predict_proba(X_trend)
    gnn_probs = gnn.predict_proba(X_context)
    bayes_probs = bayesian.predict_proba(X_rate)
    elo_probs = elo.predict_proba(X_elo)
    poisson_probs = np.array([poisson.predict_match_proba(x) for x in X])

    # Stack all probabilities
    for i in range(n_samples):
        row = np.concatenate(
            [
                gbdt_probs[i],
                cat_probs[i],
                trans_probs[i],
                lstm_probs[i],
                gnn_probs[i],
                bayes_probs[i],
                elo_probs[i],
                poisson_probs[i],
                # Add confidence metrics
                [np.max(gbdt_probs[i]) - np.min(gbdt_probs[i])],  # GBDT confidence spread
                [np.std([gbdt_probs[i][0], cat_probs[i][0], trans_probs[i][0]])],  # Model agreement
            ]
        )
        meta_features.append(row)

    return np.array(meta_features)


def train_meta_model(meta_X, y):
    """Train the meta-model (stacking ensemble)"""
    from sklearn.linear_model import LogisticRegression

    meta_model = LogisticRegression(
        multi_class="multinomial", max_iter=1000, C=0.5, random_state=42
    )
    meta_model.fit(meta_X, y)

    with open(os.path.join(MODELS_DIR, "meta_model.pkl"), "wb") as f:
        pickle.dump(meta_model, f)

    # Cross-validation score
    from sklearn.model_selection import cross_val_score

    scores = cross_val_score(meta_model, meta_X, y, cv=5, scoring="accuracy")
    print(f"   Meta-model CV accuracy: {scores.mean():.4f} (+/- {scores.std() * 2:.4f})")


def main():
    print("=" * 70)
    print("🚀 MAXIMUM FEATURE TRAINING PIPELINE")
    print("=" * 70)

    # Load team stats
    print("\n📊 Loading team seasonal statistics...")
    team_stats = load_team_stats()

    # Load matches
    print("\n⚽ Loading match history...")
    matches = load_all_matches()
    print(f"  Loaded {len(matches)} matches")

    # Build features
    X, y = build_features_and_labels(matches, team_stats)

    # Train all models
    train_all_models(X, y)

    # Summary
    print("\n📁 Trained models saved to:", MODELS_DIR)
    for f in sorted(os.listdir(MODELS_DIR)):
        size = os.path.getsize(os.path.join(MODELS_DIR, f))
        print(f"  {f}: {size/1024:.1f} KB")


if __name__ == "__main__":
    main()
