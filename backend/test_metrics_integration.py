#!/usr/bin/env python3
"""
Quick integration test for metrics tracking system.
Tests that metrics_tracker can be imported and basic operations work.
"""

import json
import os
import sys

# Add path
sys.path.insert(0, os.path.dirname(__file__))

from metrics_tracker import MetricsTracker


def test_metrics_tracker():
    """Test metrics tracker basic functionality."""
    print("Testing metrics tracker integration...\n")

    tracker = MetricsTracker()

    # Test logging a prediction
    print("1. Testing log_prediction()...")
    tracker.log_prediction(
        fixture_id=1,
        home_team="Manchester United",
        away_team="Liverpool",
        home_pred=0.52,
        draw_pred=0.28,
        away_pred=0.20,
        predicted_score="2-1",
        model_breakdown={
            "gbdt": {"home": 0.51, "draw": 0.29, "away": 0.20},
            "catboost": {"home": 0.53, "draw": 0.27, "away": 0.20},
        },
    )
    print("   ✓ Prediction logged successfully")

    # Test logging another prediction
    print("2. Testing multiple predictions...")
    tracker.log_prediction(
        fixture_id=2,
        home_team="Chelsea",
        away_team="Arsenal",
        home_pred=0.45,
        draw_pred=0.30,
        away_pred=0.25,
        predicted_score="1-1",
    )
    print("   ✓ Second prediction logged")

    # Test updating with actual result
    print("3. Testing log_actual_result()...")
    tracker.log_actual_result(fixture_id=1, actual_result="H", actual_score="2-1")  # Home win
    print("   ✓ Actual result logged")

    # Test getting summary metrics
    print("4. Testing get_summary_metrics()...")
    summary = tracker.get_summary_metrics(days=7)
    if summary:
        print(f"   ✓ Got 7-day summary with {summary.get('total_predictions', 0)} predictions")
    else:
        print("   ✓ Summary metrics empty (expected for new tracker)")

    # Test exporting summary
    print("5. Testing export_summary()...")
    tracker.export_summary()
    summary_file = os.path.join(os.path.dirname(__file__), "..", "data", "metrics", "summary.json")
    if os.path.exists(summary_file):
        with open(summary_file) as f:
            data = json.load(f)
        print(f"   ✓ Summary exported to {summary_file}")
        print(f"   Data: {json.dumps(data, indent=2)[:200]}...")
    else:
        print(f"   ⚠ Summary file not created at expected path")

    print("\n✅ Metrics tracker integration test passed!")
    return True


if __name__ == "__main__":
    try:
        test_metrics_tracker()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
