import json
from ml_engine.ensemble_predictor import EnsemblePredictor

# Load a sample match (use the first match from a season file)
with open('/Users/mobolaji/.gemini/antigravity/scratch/fixturecast/data/historical/season_2023.json') as f:
    matches = json.load(f)

match = matches[0]

# Build a minimal feature dict (the predictor will ignore missing stats)
features = {
    'home_id': match['teams']['home']['id'],
    'away_id': match['teams']['away']['id'],
    'home_name': match['teams']['home']['name'],
    'away_name': match['teams']['away']['name'],
    'home_league_points': 0,
    'away_league_points': 0,
    'home_league_pos': 10,
    'away_league_pos': 10,
    'home_points_last10': 0,
    'away_points_last10': 0,
    'home_goals_for_avg': 1.5,
    'away_goals_for_avg': 1.2,
    'home_goals_against_avg': 1.2,
    'away_goals_against_avg': 1.5,
    'home_wins_last10': 3,
    'away_wins_last10': 3,
    'home_draws_last10': 2,
    'away_draws_last10': 2,
    'home_form_last5': sum([3, 1, 0, 3, 0]),  # placeholder example
    'away_form_last5': sum([1, 0, 3, 3, 1]),  # placeholder example
}

predictor = EnsemblePredictor()
result = predictor.predict_fixture(features)

print('\n=== Prediction Summary ===')
print(f"Home win prob : {result['home_win_prob']:.2%}")
print(f"Draw prob     : {result['draw_prob']:.2%}")
print(f"Away win prob : {result['away_win_prob']:.2%}")
print(f"Most likely scoreline: {result['predicted_scoreline']}")
print(f"BTTS prob    : {result['btts_prob']:.2%}")
print(f"Over 2.5 prob: {result['over25_prob']:.2%}")
