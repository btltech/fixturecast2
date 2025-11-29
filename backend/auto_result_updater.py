"""
Auto Result Updater for FixtureCast Performance Monitoring.
Automatically fetches completed match results and updates prediction evaluations.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.api_client import ApiClient
from backend.database import PredictionDB, get_db

logger = logging.getLogger(__name__)


class AutoResultUpdater:
    """
    Automatically fetches match results and evaluates predictions.
    """

    def __init__(self, api_client: ApiClient = None):
        if api_client is None:
            import json

            config_path = os.path.join(os.path.dirname(__file__), "config.json")
            with open(config_path) as f:
                config = json.load(f)
            self.api_client = ApiClient(config)
        else:
            self.api_client = api_client

    def get_pending_fixtures(self) -> List[Dict]:
        """Get all fixtures that need result updates."""
        return PredictionDB.get_pending_results()

    def fetch_fixture_result(self, fixture_id: int) -> Dict:
        """Fetch the result of a specific fixture from API."""
        try:
            result = self.api_client.get_fixture_details(fixture_id)
            if result.get("response") and len(result["response"]) > 0:
                fixture = result["response"][0]
                return {
                    "fixture_id": fixture_id,
                    "status": fixture.get("fixture", {}).get("status", {}).get("short", ""),
                    "home_goals": fixture.get("goals", {}).get("home"),
                    "away_goals": fixture.get("goals", {}).get("away"),
                    "home_team": fixture.get("teams", {}).get("home", {}).get("name", ""),
                    "away_team": fixture.get("teams", {}).get("away", {}).get("name", ""),
                }
        except Exception as e:
            logger.error(f"Error fetching fixture {fixture_id}: {e}")
        return None

    def update_single_result(self, fixture_id: int) -> Dict:
        """Update result for a single fixture."""
        result = self.fetch_fixture_result(fixture_id)

        if result is None:
            return {"fixture_id": fixture_id, "status": "fetch_failed"}

        # Check if match is finished
        finished_statuses = ["FT", "AET", "PEN", "AWD", "WO"]
        if result["status"] not in finished_statuses:
            return {
                "fixture_id": fixture_id,
                "status": "not_finished",
                "match_status": result["status"],
            }

        # Record the result
        if result["home_goals"] is not None and result["away_goals"] is not None:
            evaluation = PredictionDB.record_result(
                fixture_id=fixture_id,
                home_goals=result["home_goals"],
                away_goals=result["away_goals"],
                status=result["status"],
            )

            if evaluation:
                return {
                    "fixture_id": fixture_id,
                    "status": "updated",
                    "home_team": result["home_team"],
                    "away_team": result["away_team"],
                    "score": f"{result['home_goals']}-{result['away_goals']}",
                    "evaluation": evaluation,
                }
            else:
                return {"fixture_id": fixture_id, "status": "no_prediction_found"}

        return {"fixture_id": fixture_id, "status": "no_score"}

    def update_all_pending(self, limit: int = 50) -> Dict:
        """Update results for all pending fixtures."""
        pending = self.get_pending_fixtures()

        if not pending:
            return {"status": "no_pending", "message": "No pending predictions to evaluate"}

        results = {"updated": [], "not_finished": [], "failed": [], "no_prediction": []}

        for fixture in pending[:limit]:
            result = self.update_single_result(fixture["fixture_id"])

            if result["status"] == "updated":
                results["updated"].append(result)
                logger.info(
                    f"✅ Updated: {result['home_team']} vs {result['away_team']} "
                    f"({result['score']}) - Correct: {result['evaluation']['outcome_correct']}"
                )
            elif result["status"] == "not_finished":
                results["not_finished"].append(result)
            elif result["status"] == "no_prediction_found":
                results["no_prediction"].append(result)
            else:
                results["failed"].append(result)

        return {
            "status": "complete",
            "processed": len(pending[:limit]),
            "updated_count": len(results["updated"]),
            "not_finished_count": len(results["not_finished"]),
            "failed_count": len(results["failed"]),
            "results": results,
        }

    def update_results_for_date(self, date: str, league_ids: List[int] = None) -> Dict:
        """Update results for all matches on a specific date."""
        if league_ids is None:
            # Default leagues
            league_ids = [39, 140, 135, 78, 61, 88, 94, 40, 141, 136, 79, 62, 2, 3]

        all_fixtures = []
        for league_id in league_ids:
            try:
                result = self.api_client.get_fixtures(league_id=league_id, date=date)
                if result.get("response"):
                    all_fixtures.extend(result["response"])
            except Exception as e:
                logger.warning(f"Error fetching fixtures for league {league_id}: {e}")

        updated = []
        for fixture in all_fixtures:
            fixture_id = fixture.get("fixture", {}).get("id")
            status = fixture.get("fixture", {}).get("status", {}).get("short", "")

            if status in ["FT", "AET", "PEN"]:
                home_goals = fixture.get("goals", {}).get("home")
                away_goals = fixture.get("goals", {}).get("away")

                if home_goals is not None and away_goals is not None:
                    evaluation = PredictionDB.record_result(
                        fixture_id=fixture_id,
                        home_goals=home_goals,
                        away_goals=away_goals,
                        status=status,
                    )

                    if evaluation:
                        updated.append(
                            {
                                "fixture_id": fixture_id,
                                "home": fixture.get("teams", {}).get("home", {}).get("name"),
                                "away": fixture.get("teams", {}).get("away", {}).get("name"),
                                "score": f"{home_goals}-{away_goals}",
                                "correct": evaluation["outcome_correct"],
                            }
                        )

        return {
            "date": date,
            "total_fixtures": len(all_fixtures),
            "updated": len(updated),
            "details": updated,
        }


def run_update():
    """Run the auto update process."""
    print("🔄 Starting Auto Result Updater...")
    print(f"   Time: {datetime.now().isoformat()}")

    updater = AutoResultUpdater()

    # Update pending predictions
    result = updater.update_all_pending(limit=100)

    print(f"\n📊 Update Summary:")
    print(f"   Processed: {result.get('processed', 0)}")
    print(f"   Updated: {result.get('updated_count', 0)}")
    print(f"   Not Finished: {result.get('not_finished_count', 0)}")
    print(f"   Failed: {result.get('failed_count', 0)}")

    # Show accuracy for updated matches
    if result.get("results", {}).get("updated"):
        correct = sum(1 for r in result["results"]["updated"] if r["evaluation"]["outcome_correct"])
        total = len(result["results"]["updated"])
        print(f"\n   Session Accuracy: {correct}/{total} ({correct/total*100:.1f}%)")

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_update()
