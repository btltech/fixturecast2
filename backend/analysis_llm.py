
class AnalysisLLM:
    """
    AI Match Analyst.
    Generates dynamic insights and narratives based on prediction data.
    """
    
    def analyze(self, prediction, features):
        """
        Generate a natural language analysis of the match.
        """
        home_name = features.get('home_name', 'Home Team')
        away_name = features.get('away_name', 'Away Team')
        
        home_prob = prediction.get("home_win_prob", 0) * 100
        away_prob = prediction.get("away_win_prob", 0) * 100
        draw_prob = prediction.get("draw_prob", 0) * 100
        score = prediction.get("predicted_scoreline", "N/A")
        
        # Determine narrative
        if home_prob > 65:
            narrative = f"**{home_name}** enters this match as the clear favorite."
            reason = f"Their dominant form and home advantage give them a **{home_prob:.1f}%** chance of victory."
        elif away_prob > 65:
            narrative = f"**{away_name}** looks poised to dominate this fixture."
            reason = f"Despite playing away, their superior quality gives them a **{away_prob:.1f}%** win probability."
        elif abs(home_prob - away_prob) < 10:
            narrative = "This match is too close to call."
            reason = f"Both sides are evenly matched, with **{home_name}** at {home_prob:.1f}% and **{away_name}** at {away_prob:.1f}%."
        else:
            favorite = home_name if home_prob > away_prob else away_name
            narrative = f"**{favorite}** has the edge in this contest."
            reason = "Statistical models point to a slight advantage based on recent performance."

        # Key Factors
        factors = []
        
        # Form factor
        home_form = features.get('home_points_last10', 0)
        away_form = features.get('away_points_last10', 0)
        if home_form > away_form + 5:
            factors.append(f"**{home_name}** is in better form ({home_form} pts vs {away_form} pts in last 10).")
        elif away_form > home_form + 5:
            factors.append(f"**{away_name}** arrives in superior form ({away_form} pts vs {home_form} pts).")
            
        # H2H factor
        h2h_home = features.get('h2h_home_wins', 0)
        h2h_away = features.get('h2h_away_wins', 0)
        if h2h_home > h2h_away:
            factors.append(f"History favors **{home_name}** with {h2h_home} wins in recent meetings.")
        
        # Goals factor
        btts_prob = prediction.get('btts_prob', 0) * 100
        if btts_prob > 60:
            factors.append(f"High chance of goals from both sides (**{btts_prob:.1f}%** BTTS probability).")
        elif btts_prob < 40:
            factors.append("A tight, defensive battle is expected.")
            
        # Construct analysis
        factors_text = "\n".join([f"- {f}" for f in factors])
        
        analysis = f"""
### 🧠 AI Match Analysis

{narrative} {reason}

**Predicted Outcome:** {score}

**Key Insights:**
{factors_text}

*Confidence Level: {'High' if max(home_prob, away_prob) > 60 else 'Medium'}*
        """
        return analysis
