
class AnalysisLLM:
    """
    AI Match Analyst.
    Generates dynamic insights and narratives based on prediction data.
    Uses an 8-model ensemble for comprehensive match analysis.
    """
    
    def analyze(self, prediction, features):
        """
        Generate a polished natural language analysis of the match.
        Returns markdown-formatted analysis with clear sections.
        """
        home_name = features.get('home_name', 'Home Team')
        away_name = features.get('away_name', 'Away Team')
        
        home_prob = prediction.get("home_win_prob", 0) * 100
        away_prob = prediction.get("away_win_prob", 0) * 100
        draw_prob = prediction.get("draw_prob", 0) * 100
        score = prediction.get("predicted_scoreline", "N/A")
        btts_prob = prediction.get('btts_prob', 0) * 100
        # Handle both field names for over 2.5 probability
        over25_prob = (prediction.get('over25_prob') or prediction.get('over_2_5_prob') or 0) * 100
        
        # Determine confidence level and favorite
        max_prob = max(home_prob, away_prob, draw_prob)
        if max_prob > 70:
            confidence = "HIGH"
            confidence_emoji = "🟢"
        elif max_prob > 55:
            confidence = "MEDIUM"
            confidence_emoji = "🟡"
        else:
            confidence = "LOW"
            confidence_emoji = "🔴"
        
        # Determine favorite
        if home_prob > away_prob and home_prob > draw_prob:
            favorite = home_name
            favorite_prob = home_prob
        elif away_prob > home_prob and away_prob > draw_prob:
            favorite = away_name
            favorite_prob = away_prob
        else:
            favorite = "Draw"
            favorite_prob = draw_prob
        
        # Build deep analysis sections
        analysis_points = []
        
        # Model consensus - handle both field names
        model_breakdown = prediction.get('model_breakdown') or prediction.get('model_probabilities', {})
        if model_breakdown:
            models_favoring_home = 0
            models_favoring_away = 0
            for m, p in model_breakdown.items():
                # Handle both key styles: 'home'/'away' and 'home_win'/'away_win'
                home_p = p.get('home_win', p.get('home', 0))
                away_p = p.get('away_win', p.get('away', 0))
                draw_p = p.get('draw', 0)
                if home_p > away_p and home_p > draw_p:
                    models_favoring_home += 1
                elif away_p > home_p and away_p > draw_p:
                    models_favoring_away += 1
            
            total_models = len(model_breakdown)
            if total_models > 0:
                if models_favoring_home >= total_models * 0.6:
                    analysis_points.append(f"⚖️ **Model Consensus:** {models_favoring_home} of {total_models} models back {home_name} — solid agreement supports the prediction.")
                elif models_favoring_away >= total_models * 0.6:
                    analysis_points.append(f"⚖️ **Model Consensus:** {models_favoring_away} of {total_models} models back {away_name} — solid agreement supports the prediction.")
                else:
                    analysis_points.append(f"⚖️ **Model Consensus:** Models are split ({models_favoring_home} for {home_name}, {models_favoring_away} for {away_name}) — prediction carries higher uncertainty.")
        
        # Elo & League combined
        home_elo = features.get('home_elo', 0)
        away_elo = features.get('away_elo', 0)
        home_rank = features.get('home_rank', 0)
        away_rank = features.get('away_rank', 0)
        if home_elo and away_elo:
            elo_diff = home_elo - away_elo
            if abs(elo_diff) > 50:
                stronger = home_name if elo_diff > 0 else away_name
                elo_text = f"📈 **Elo & League:** {home_name} ({home_elo:.0f}) vs {away_name} ({away_elo:.0f}) — {abs(elo_diff):.0f}-point gap"
                if home_rank and away_rank:
                    elo_text += f", also reflected in the table ({self._ordinal(home_rank)} vs {self._ordinal(away_rank)})."
                else:
                    elo_text += f" in favor of {stronger}."
                analysis_points.append(elo_text)
        
        # H2H
        h2h_home = features.get('h2h_home_wins', 0)
        h2h_away = features.get('h2h_away_wins', 0)
        h2h_draws = features.get('h2h_draws', 0)
        h2h_total = h2h_home + h2h_away + h2h_draws
        if h2h_total > 0:
            if h2h_draws >= h2h_total * 0.4:
                analysis_points.append(f"📊 **H2H:** {h2h_draws} draws in last {h2h_total} meetings — slight draw tendency worth noting.")
            elif h2h_home > h2h_away:
                analysis_points.append(f"📊 **H2H:** {home_name} leads {h2h_home}-{h2h_away} in recent meetings — history on their side.")
            elif h2h_away > h2h_home:
                analysis_points.append(f"📊 **H2H:** {away_name} leads {h2h_away}-{h2h_home} in recent meetings — history favors the visitors.")
        
        # Tactical matchup - handle missing data gracefully
        home_goals_for = features.get('home_goals_for_avg', 0) or 1.2  # Use league avg as fallback
        home_goals_against = features.get('home_goals_against_avg', 0) or 1.2
        away_goals_for = features.get('away_goals_for_avg', 0) or 1.2
        away_goals_against = features.get('away_goals_against_avg', 0) or 1.2
        
        # Only show tactical if we have real data for at least home team
        if features.get('home_goals_for_avg', 0) > 0:
            home_style = "attack-minded" if home_goals_for > 1.5 else "balanced" if home_goals_for > 1.0 else "defensive"
            away_style = "attack-minded" if away_goals_for > 1.5 else "balanced" if away_goals_for > 1.0 else "defensive"
            # Only include away style if we have their data
            if features.get('away_goals_for_avg', 0) > 0:
                analysis_points.append(
                    f"⚔️ **Tactical Matchup:** {home_name} ({home_style}, {home_goals_for:.1f} GF / {home_goals_against:.1f} GA) "
                    f"vs {away_name} ({away_style}, {away_goals_for:.1f} GF / {away_goals_against:.1f} GA)."
                )
            else:
                analysis_points.append(
                    f"⚔️ **Tactical Matchup:** {home_name} ({home_style}, {home_goals_for:.1f} GF / {home_goals_against:.1f} GA). "
                    f"{away_name} data limited (newly promoted/new to league)."
                )
        
        # Form
        home_form = features.get('home_points_last10', 0)
        away_form = features.get('away_points_last10', 0)
        home_wins_last10 = features.get('home_wins_last10', 0)
        away_wins_last10 = features.get('away_wins_last10', 0)
        home_form_last5 = features.get('home_form_last5', features.get('home_points_last5', 0))
        away_form_last5 = features.get('away_form_last5', features.get('away_points_last5', 0))
        
        if home_form or away_form:
            form_diff = home_form - away_form
            if abs(form_diff) > 5:
                if form_diff > 0:
                    analysis_points.append(
                        f"📈 **Form:** {home_name} flying ({home_wins_last10}W/10, {home_form_last5:.0f}pts last 5). "
                        f"{away_name} struggling ({away_wins_last10}W, {away_form_last5:.0f}pts). Momentum heavily favors hosts."
                    )
                else:
                    analysis_points.append(
                        f"📈 **Form:** {away_name} in great form ({away_wins_last10}W/10, {away_form_last5:.0f}pts last 5). "
                        f"{home_name} struggling ({home_wins_last10}W, {home_form_last5:.0f}pts). Visitors have momentum."
                    )
            else:
                analysis_points.append(f"📈 **Form:** Both sides in similar form — no clear momentum advantage.")
        
        # ========== NEW ENHANCED INSIGHTS ==========
        
        # Top Scorer Analysis
        home_top_scorer = features.get('home_top_scorer_name')
        home_top_goals = features.get('home_top_scorer_goals', 0)
        away_top_scorer = features.get('away_top_scorer_name')
        away_top_goals = features.get('away_top_scorer_goals', 0)
        home_dependency = features.get('home_top_scorer_dependency', 0)
        away_dependency = features.get('away_top_scorer_dependency', 0)
        
        if home_top_scorer and home_top_goals >= 5:
            dependency_note = " — high dependency risk" if home_dependency > 0.4 else ""
            analysis_points.append(
                f"⚽ **Key Player:** {home_name}'s {home_top_scorer} has {home_top_goals} goals this season{dependency_note}."
            )
        if away_top_scorer and away_top_goals >= 5:
            dependency_note = " — high dependency risk" if away_dependency > 0.4 else ""
            analysis_points.append(
                f"⚽ **Key Player:** {away_name}'s {away_top_scorer} has {away_top_goals} goals this season{dependency_note}."
            )
        
        # Coach Analysis (new manager effect)
        home_coach_name = features.get('home_coach_name')
        away_coach_name = features.get('away_coach_name')
        home_coach_is_new = features.get('home_coach_is_new', False)
        away_coach_is_new = features.get('away_coach_is_new', False)
        
        if home_coach_is_new and home_coach_name:
            analysis_points.append(
                f"🆕 **New Manager:** {home_name} under new coach {home_coach_name} — potential bounce effect or teething issues."
            )
        if away_coach_is_new and away_coach_name:
            analysis_points.append(
                f"🆕 **New Manager:** {away_name} under new coach {away_coach_name} — potential bounce effect or teething issues."
            )
        
        # Discipline Analysis
        home_red_cards = features.get('home_red_cards_last5', 0)
        away_red_cards = features.get('away_red_cards_last5', 0)
        home_cards_per_game = features.get('home_cards_per_game', 0)
        away_cards_per_game = features.get('away_cards_per_game', 0)
        
        if home_red_cards >= 2 or away_red_cards >= 2:
            hot_team = home_name if home_red_cards > away_red_cards else away_name
            red_count = max(home_red_cards, away_red_cards)
            analysis_points.append(
                f"🟥 **Discipline Warning:** {hot_team} has {red_count} red cards in last 5 — could be vulnerable to another."
            )
        
        # Goal Timing Patterns
        home_late_goals = features.get('home_late_goals_pct', 0)
        away_late_goals = features.get('away_late_goals_pct', 0)
        home_conceded_late = features.get('home_conceded_late_pct', 0)
        away_conceded_late = features.get('away_conceded_late_pct', 0)
        
        if home_late_goals > 0.3 or away_late_goals > 0.3:
            late_scorer = home_name if home_late_goals > away_late_goals else away_name
            late_pct = max(home_late_goals, away_late_goals) * 100
            analysis_points.append(
                f"⏱️ **Late Drama:** {late_scorer} scores {late_pct:.0f}% of their goals after 75' — could be a late game to watch."
            )
        
        if home_conceded_late > 0.35 or away_conceded_late > 0.35:
            vulnerable_team = home_name if home_conceded_late > away_conceded_late else away_name
            late_concede_pct = max(home_conceded_late, away_conceded_late) * 100
            analysis_points.append(
                f"⚠️ **Late Vulnerability:** {vulnerable_team} concedes {late_concede_pct:.0f}% of goals after 75' — fitness or concentration issues."
            )
        
        # BTTS and Over 2.5 insight
        btts_text = "Yes" if btts_prob > 50 else "No"
        btts_insight = "goals likely from both ends" if btts_prob > 60 else "goals likely one-sided" if btts_prob < 40 else "could go either way"
        
        over25_text = "Likely" if over25_prob > 55 else "Unlikely" if over25_prob < 45 else "Borderline"
        over25_insight = "open, high-scoring affair expected" if over25_prob > 60 else "tight game expected" if over25_prob < 40 else "could be close either way"
        
        # Build verdict
        if confidence == "HIGH":
            risk_text = "Low risk"
            bet_suggestion = f"Straight {favorite} win looks solid."
        elif confidence == "MEDIUM":
            risk_text = "Medium risk"
            bet_suggestion = "'Draw No Bet' limits downside if the underdog steals a point."
        else:
            risk_text = "High risk"
            bet_suggestion = "Consider smaller stakes or alternative markets (BTTS, corners, etc.)."
        
        # Assemble analysis points
        analysis_section = "\n\n".join(analysis_points) if analysis_points else "No detailed analysis available for this fixture."
        
        analysis = f"""## {home_name} vs {away_name}
{confidence_emoji} **{confidence} CONFIDENCE** · {favorite} favored ({favorite_prob:.0f}%)

---

### 📊 Prediction Summary

| Outcome | Probability |
|---------|-------------|
| {home_name} Win | {home_prob:.1f}% |
| Draw | {draw_prob:.1f}% |
| {away_name} Win | {away_prob:.1f}% |

**Predicted Score:** {score}  
**Both teams to score:** {btts_text} ({btts_prob:.0f}%) — {btts_insight}  
**Over 2.5 goals:** {over25_text} ({over25_prob:.0f}%) — {over25_insight}

---

### 🔍 Deep Analysis

{analysis_section}

---

### 🎯 Our Verdict

{favorite} {'are' if favorite != 'Draw' else 'is'} {'clear favorites' if favorite_prob > 60 else 'slight favorites' if favorite_prob > 50 else 'in a tight contest'} but {'this is no certainty' if confidence != 'HIGH' else 'the data strongly supports this'}. **{risk_text}** — {bet_suggestion}

---

*Analysis by FixtureCast AI — 8-model ensemble (GBDT 22%, Elo 22%, GNN 18%, LSTM 14%, Bayesian 10%, Transformer 8%, CatBoost 6%)*"""
        
        return analysis
    
    def _ordinal(self, n):
        """Convert number to ordinal string (1st, 2nd, 3rd, etc.)."""
        if not n:
            return "N/A"
        n = int(n)
        suffix = ['th', 'st', 'nd', 'rd', 'th'][min(n % 10, 4)]
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        return f"{n}{suffix}"
