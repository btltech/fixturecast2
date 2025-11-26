// ML Prediction API Client for FixtureCast
// Handles communication with the FastAPI ML prediction service

import { ML_API_URL } from "./apiConfig.js";

const API_BASE_URL = ML_API_URL;

export class MLPredictionClient {
  /**
   * Get prediction for a match
   * @param {Object} features - Match features
   * @returns {Promise<Object>} Prediction result
   */
  async getPrediction(features) {
    try {
      const response = await fetch(`${API_BASE_URL}/predict`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(features),
      });

      if (!response.ok) {
        throw new Error(`Prediction failed: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error("ML Prediction Error:", error);
      throw error;
    }
  }

  /**
   * Get health status of ML API
   * @returns {Promise<Object>} Health status
   */
  async getHealth() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      return await response.json();
    } catch (error) {
      console.error("Health check failed:", error);
      return { status: "unavailable" };
    }
  }

  /**
   * Get information about loaded models
   * @returns {Promise<Object>} Model info
   */
  async getModelsInfo() {
    try {
      const response = await fetch(`${API_BASE_URL}/models/info`);
      return await response.json();
    } catch (error) {
      console.error("Failed to get models info:", error);
      throw error;
    }
  }

  /**
   * Build feature object from match and team stats
   * @param {Object} match - Match data
   * @param {Object} homeStats - Home team statistics
   * @param {Object} awayStats - Away team statistics
   * @returns {Object} Features for ML prediction
   */
  buildFeatures(match, homeStats, awayStats) {
    return {
      home_id: match.teams.home.id,
      away_id: match.teams.away.id,
      home_name: match.teams.home.name,
      away_name: match.teams.away.name,

      // League standings
      home_league_points: homeStats?.league_points || 30,
      away_league_points: awayStats?.league_points || 30,
      home_league_pos: homeStats?.league_position || 10,
      away_league_pos: awayStats?.league_position || 10,

      // Recent form
      home_points_last10: homeStats?.points_last_10 || 15,
      away_points_last10: awayStats?.points_last_10 || 15,
      home_form_last5: homeStats?.form_last_5 || 7,
      away_form_last5: awayStats?.form_last_5 || 7,

      // Goals
      home_goals_for_avg: homeStats?.goals_for_avg || 1.3,
      away_goals_for_avg: awayStats?.goals_for_avg || 1.2,
      home_goals_against_avg: homeStats?.goals_against_avg || 1.2,
      away_goals_against_avg: awayStats?.goals_against_avg || 1.3,

      // Match results breakdown
      home_wins_last10: homeStats?.wins_last_10 || 5,
      away_wins_last10: awayStats?.wins_last_10 || 5,
      home_draws_last10: homeStats?.draws_last_10 || 3,
      away_draws_last10: awayStats?.draws_last_10 || 3,
      home_losses_last10: homeStats?.losses_last_10 || 2,
      away_losses_last10: awayStats?.losses_last_10 || 2,

      // Goals last 10
      home_goals_for_last10: homeStats?.goals_for_last_10 || 13,
      away_goals_for_last10: awayStats?.goals_for_last_10 || 12,
      home_goals_against_last10: homeStats?.goals_against_last_10 || 12,
      away_goals_against_last10: awayStats?.goals_against_last_10 || 13,

      // Head to head
      h2h_home_wins: match.h2h?.home_wins || 2,
      h2h_draws: match.h2h?.draws || 2,
      h2h_away_wins: match.h2h?.away_wins || 2,
      h2h_total_matches: match.h2h?.total || 6,

      // Defensive stats
      home_clean_sheets: homeStats?.clean_sheets || 3,
      away_clean_sheets: awayStats?.clean_sheets || 3,
      home_total_matches: homeStats?.matches_played || 20,
      away_total_matches: awayStats?.matches_played || 20,

      // Odds (if available)
      odds_home_win: match.odds?.home,
      odds_draw: match.odds?.draw,
      odds_away_win: match.odds?.away,
      odds_available: !!match.odds,
    };
  }
}

export const mlClient = new MLPredictionClient();
