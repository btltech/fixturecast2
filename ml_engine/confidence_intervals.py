import numpy as np


def calculate_confidence_intervals(prediction, model_breakdown):
    """
    Calculate 95% confidence intervals for predictions based on model variance.

    Returns confidence intervals for each outcome (home/draw/away).
    Higher model disagreement = wider confidence intervals.
    """
    # Collect probabilities from all models
    model_probs = []

    for model_name, preds in model_breakdown.items():
        if isinstance(preds, dict) and "home_win" in preds:
            model_probs.append(
                [preds.get("home_win", 0), preds.get("draw", 0), preds.get("away_win", 0)]
            )

    if len(model_probs) < 2:
        # Not enough models to calculate variance
        return {
            "home_win_ci": (prediction["home_win_prob"], prediction["home_win_prob"]),
            "draw_ci": (prediction["draw_prob"], prediction["draw_prob"]),
            "away_win_ci": (prediction["away_win_prob"], prediction["away_win_prob"]),
            "confidence_level": "insufficient_data",
        }

    model_probs = np.array(model_probs)

    # Calculate standard deviation across models for each outcome
    std = np.std(model_probs, axis=0)

    # Calculate 95% confidence interval (±1.96 * std)
    # But respect probability bounds [0, 1]
    ci_multiplier = 1.96

    home_lower = max(0.0, prediction["home_win_prob"] - ci_multiplier * std[0])
    home_upper = min(1.0, prediction["home_win_prob"] + ci_multiplier * std[0])

    draw_lower = max(0.0, prediction["draw_prob"] - ci_multiplier * std[1])
    draw_upper = min(1.0, prediction["draw_prob"] + ci_multiplier * std[1])

    away_lower = max(0.0, prediction["away_win_prob"] - ci_multiplier * std[2])
    away_upper = min(1.0, prediction["away_win_prob"] + ci_multiplier * std[2])

    # Calculate average interval width (uncertainty measure)
    avg_width = (
        (home_upper - home_lower) + (draw_upper - draw_lower) + (away_upper - away_lower)
    ) / 3

    # Classify confidence level based on average width
    if avg_width < 0.10:
        confidence_level = "very_high"  # Models strongly agree
    elif avg_width < 0.20:
        confidence_level = "high"
    elif avg_width < 0.30:
        confidence_level = "medium"
    else:
        confidence_level = "low"  # Models disagree significantly

    return {
        "home_win_ci": (round(home_lower, 4), round(home_upper, 4)),
        "draw_ci": (round(draw_lower, 4), round(draw_upper, 4)),
        "away_win_ci": (round(away_lower, 4), round(away_upper, 4)),
        "confidence_level": confidence_level,
        "avg_interval_width": round(avg_width, 4),
        "model_agreement": round(1.0 - min(1.0, avg_width / 0.3), 4),  # 0-1 scale
    }


def format_ci_display(ci_data, prob):
    """
    Format confidence interval for display.

    Example: "74.8% (70.2% - 79.4%)"
    """
    lower, upper = ci_data
    return f"{prob*100:.1f}% ({lower*100:.1f}% - {upper*100:.1f}%)"
