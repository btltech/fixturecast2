"""
Database module for FixtureCast Performance Monitoring.
Uses SQLite for simplicity - can be upgraded to PostgreSQL later.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Database path
DB_PATH = os.environ.get(
    "FIXTURECAST_DB_PATH", os.path.join(os.path.dirname(__file__), "data", "fixturecast.db")
)

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_db_connection():
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize the database schema."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Predictions table - stores all predictions made
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fixture_id INTEGER UNIQUE NOT NULL,
                home_team TEXT NOT NULL,
                away_team TEXT NOT NULL,
                home_team_id INTEGER,
                away_team_id INTEGER,
                league_id INTEGER NOT NULL,
                league_name TEXT,
                match_date TIMESTAMP NOT NULL,

                -- Prediction probabilities
                home_win_prob REAL NOT NULL,
                draw_prob REAL NOT NULL,
                away_win_prob REAL NOT NULL,
                predicted_outcome TEXT NOT NULL,
                confidence REAL NOT NULL,
                confidence_level TEXT NOT NULL,

                -- Additional predictions
                predicted_scoreline TEXT,
                btts_prob REAL,
                over25_prob REAL,

                -- Model breakdown (JSON)
                model_breakdown TEXT,

                -- Result tracking
                result_home_goals INTEGER,
                result_away_goals INTEGER,
                actual_outcome TEXT,
                match_status TEXT,

                -- Evaluation
                outcome_correct INTEGER,
                brier_score REAL,
                btts_correct INTEGER,
                over25_correct INTEGER,
                exact_score INTEGER,

                -- Timestamps
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                result_recorded_at TIMESTAMP,
                evaluated INTEGER DEFAULT 0
            )
        """
        )

        # Model performance table - tracks each model's accuracy
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS model_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                fixture_id INTEGER NOT NULL,
                predicted_outcome TEXT NOT NULL,
                actual_outcome TEXT,
                is_correct INTEGER,
                home_prob REAL,
                draw_prob REAL,
                away_prob REAL,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (fixture_id) REFERENCES predictions (fixture_id)
            )
        """
        )

        # Daily metrics table - aggregated daily stats
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE UNIQUE NOT NULL,
                total_predictions INTEGER DEFAULT 0,
                correct_predictions INTEGER DEFAULT 0,
                accuracy REAL DEFAULT 0,
                avg_confidence REAL DEFAULT 0,
                avg_brier_score REAL DEFAULT 0,
                high_conf_correct INTEGER DEFAULT 0,
                high_conf_total INTEGER DEFAULT 0,
                medium_conf_correct INTEGER DEFAULT 0,
                medium_conf_total INTEGER DEFAULT 0,
                low_conf_correct INTEGER DEFAULT 0,
                low_conf_total INTEGER DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # League performance table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS league_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                league_id INTEGER NOT NULL,
                league_name TEXT,
                period TEXT NOT NULL,  -- 'all_time', 'monthly', 'weekly'
                period_start DATE,
                total_predictions INTEGER DEFAULT 0,
                correct_predictions INTEGER DEFAULT 0,
                accuracy REAL DEFAULT 0,
                avg_brier_score REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(league_id, period, period_start)
            )
        """
        )

        # API request logs - for monitoring
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS api_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                status_code INTEGER,
                response_time_ms REAL,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Create indexes for common queries
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_predictions_fixture ON predictions(fixture_id)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(match_date)")
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_predictions_league ON predictions(league_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_predictions_evaluated ON predictions(evaluated)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_model_perf_model ON model_performance(model_name)"
        )
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_daily_metrics_date ON daily_metrics(date)")

        print(f"✅ Database initialized at {DB_PATH}")


class PredictionDB:
    """Database operations for predictions and metrics."""

    @staticmethod
    def log_prediction(
        fixture_id: int,
        home_team: str,
        away_team: str,
        league_id: int,
        match_date: str,
        prediction: Dict,
        model_breakdown: Optional[Dict] = None,
        home_team_id: int = None,
        away_team_id: int = None,
        league_name: str = None,
    ) -> bool:
        """Log a new prediction to the database."""
        try:
            # Determine predicted outcome
            home_prob = prediction.get("home_win_prob", 0)
            draw_prob = prediction.get("draw_prob", 0)
            away_prob = prediction.get("away_win_prob", 0)

            if home_prob >= draw_prob and home_prob >= away_prob:
                predicted_outcome = "home"
            elif away_prob >= draw_prob:
                predicted_outcome = "away"
            else:
                predicted_outcome = "draw"

            # Calculate confidence level
            max_prob = max(home_prob, draw_prob, away_prob)
            if max_prob >= 0.65:
                confidence_level = "high"
            elif max_prob >= 0.45:
                confidence_level = "medium"
            else:
                confidence_level = "low"

            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO predictions (
                        fixture_id, home_team, away_team, home_team_id, away_team_id,
                        league_id, league_name, match_date,
                        home_win_prob, draw_prob, away_win_prob,
                        predicted_outcome, confidence, confidence_level,
                        predicted_scoreline, btts_prob, over25_prob,
                        model_breakdown
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        fixture_id,
                        home_team,
                        away_team,
                        home_team_id,
                        away_team_id,
                        league_id,
                        league_name,
                        match_date,
                        home_prob,
                        draw_prob,
                        away_prob,
                        predicted_outcome,
                        max_prob,
                        confidence_level,
                        prediction.get("predicted_scoreline"),
                        prediction.get("btts_prob"),
                        prediction.get("over25_prob"),
                        json.dumps(model_breakdown) if model_breakdown else None,
                    ),
                )

                # Log individual model predictions
                if model_breakdown:
                    for model_name, model_pred in model_breakdown.items():
                        m_home = model_pred.get("home_win", 0)
                        m_draw = model_pred.get("draw", 0)
                        m_away = model_pred.get("away_win", 0)

                        if m_home >= m_draw and m_home >= m_away:
                            m_outcome = "home"
                        elif m_away >= m_draw:
                            m_outcome = "away"
                        else:
                            m_outcome = "draw"

                        cursor.execute(
                            """
                            INSERT INTO model_performance (
                                model_name, fixture_id, predicted_outcome,
                                home_prob, draw_prob, away_prob
                            ) VALUES (?, ?, ?, ?, ?, ?)
                        """,
                            (model_name, fixture_id, m_outcome, m_home, m_draw, m_away),
                        )

            return True
        except Exception as e:
            print(f"Error logging prediction: {e}")
            return False

    @staticmethod
    def record_result(
        fixture_id: int, home_goals: int, away_goals: int, status: str = "FT"
    ) -> Optional[Dict]:
        """Record match result and evaluate prediction."""
        try:
            # Determine actual outcome
            if home_goals > away_goals:
                actual_outcome = "home"
            elif away_goals > home_goals:
                actual_outcome = "away"
            else:
                actual_outcome = "draw"

            with get_db() as conn:
                cursor = conn.cursor()

                # Get the prediction
                cursor.execute("SELECT * FROM predictions WHERE fixture_id = ?", (fixture_id,))
                row = cursor.fetchone()

                if not row:
                    return None

                pred = dict(row)

                # Calculate evaluation metrics
                outcome_correct = 1 if pred["predicted_outcome"] == actual_outcome else 0

                # Brier score
                actual_probs = {"home": 0, "draw": 0, "away": 0}
                actual_probs[actual_outcome] = 1
                brier_score = (
                    (pred["home_win_prob"] - actual_probs["home"]) ** 2
                    + (
                        pred["draw_win_prob"]
                        if "draw_win_prob" in pred
                        else pred["draw_prob"] - actual_probs["draw"]
                    )
                    ** 2
                    + (pred["away_win_prob"] - actual_probs["away"]) ** 2
                ) / 3

                # BTTS evaluation
                btts_actual = home_goals > 0 and away_goals > 0
                btts_correct = 1 if ((pred.get("btts_prob", 0.5) >= 0.5) == btts_actual) else 0

                # Over 2.5 evaluation
                over25_actual = (home_goals + away_goals) > 2.5
                over25_correct = (
                    1 if ((pred.get("over25_prob", 0.5) >= 0.5) == over25_actual) else 0
                )

                # Exact score
                exact_score = 0
                if pred.get("predicted_scoreline"):
                    try:
                        pred_home, pred_away = map(int, pred["predicted_scoreline"].split("-"))
                        exact_score = (
                            1 if (pred_home == home_goals and pred_away == away_goals) else 0
                        )
                    except (ValueError, AttributeError):
                        pass

                # Update prediction record
                cursor.execute(
                    """
                    UPDATE predictions SET
                        result_home_goals = ?,
                        result_away_goals = ?,
                        actual_outcome = ?,
                        match_status = ?,
                        outcome_correct = ?,
                        brier_score = ?,
                        btts_correct = ?,
                        over25_correct = ?,
                        exact_score = ?,
                        result_recorded_at = ?,
                        evaluated = 1
                    WHERE fixture_id = ?
                """,
                    (
                        home_goals,
                        away_goals,
                        actual_outcome,
                        status,
                        outcome_correct,
                        brier_score,
                        btts_correct,
                        over25_correct,
                        exact_score,
                        datetime.now().isoformat(),
                        fixture_id,
                    ),
                )

                # Update model performance records
                cursor.execute(
                    """
                    UPDATE model_performance SET
                        actual_outcome = ?,
                        is_correct = CASE WHEN predicted_outcome = ? THEN 1 ELSE 0 END
                    WHERE fixture_id = ?
                """,
                    (actual_outcome, actual_outcome, fixture_id),
                )

                # Update daily metrics
                match_date = (
                    pred["match_date"][:10]
                    if pred["match_date"]
                    else datetime.now().strftime("%Y-%m-%d")
                )
                PredictionDB._update_daily_metrics(cursor, match_date)

                return {
                    "fixture_id": fixture_id,
                    "outcome_correct": bool(outcome_correct),
                    "brier_score": brier_score,
                    "btts_correct": bool(btts_correct),
                    "over25_correct": bool(over25_correct),
                    "exact_score": bool(exact_score),
                    "predicted": pred["predicted_outcome"],
                    "actual": actual_outcome,
                }

        except Exception as e:
            print(f"Error recording result: {e}")
            return None

    @staticmethod
    def _update_daily_metrics(cursor, date: str):
        """Update aggregated daily metrics."""
        # Get stats for this date
        cursor.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(outcome_correct) as correct,
                AVG(confidence) as avg_conf,
                AVG(brier_score) as avg_brier,
                SUM(CASE WHEN confidence_level = 'high' AND outcome_correct = 1 THEN 1 ELSE 0 END) as high_correct,
                SUM(CASE WHEN confidence_level = 'high' THEN 1 ELSE 0 END) as high_total,
                SUM(CASE WHEN confidence_level = 'medium' AND outcome_correct = 1 THEN 1 ELSE 0 END) as med_correct,
                SUM(CASE WHEN confidence_level = 'medium' THEN 1 ELSE 0 END) as med_total,
                SUM(CASE WHEN confidence_level = 'low' AND outcome_correct = 1 THEN 1 ELSE 0 END) as low_correct,
                SUM(CASE WHEN confidence_level = 'low' THEN 1 ELSE 0 END) as low_total
            FROM predictions
            WHERE DATE(match_date) = ? AND evaluated = 1
        """,
            (date,),
        )

        stats = cursor.fetchone()
        if stats and stats["total"] > 0:
            accuracy = (stats["correct"] or 0) / stats["total"]
            cursor.execute(
                """
                INSERT OR REPLACE INTO daily_metrics (
                    date, total_predictions, correct_predictions, accuracy,
                    avg_confidence, avg_brier_score,
                    high_conf_correct, high_conf_total,
                    medium_conf_correct, medium_conf_total,
                    low_conf_correct, low_conf_total,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    date,
                    stats["total"],
                    stats["correct"] or 0,
                    accuracy,
                    stats["avg_conf"] or 0,
                    stats["avg_brier"] or 0,
                    stats["high_correct"] or 0,
                    stats["high_total"] or 0,
                    stats["med_correct"] or 0,
                    stats["med_total"] or 0,
                    stats["low_correct"] or 0,
                    stats["low_total"] or 0,
                    datetime.now().isoformat(),
                ),
            )

    @staticmethod
    def get_pending_results() -> List[Dict]:
        """Get predictions that haven't been evaluated yet."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT fixture_id, home_team, away_team, league_id, match_date
                FROM predictions
                WHERE evaluated = 0 AND match_date < datetime('now')
                ORDER BY match_date ASC
                LIMIT 100
            """
            )
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_metrics_summary(days: int = 7) -> Dict:
        """Get performance metrics summary for the last N days."""
        with get_db() as conn:
            cursor = conn.cursor()

            cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

            # Overall stats
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(outcome_correct) as correct,
                    AVG(confidence) as avg_conf,
                    MIN(confidence) as min_conf,
                    MAX(confidence) as max_conf,
                    AVG(brier_score) as avg_brier
                FROM predictions
                WHERE evaluated = 1 AND match_date >= ?
            """,
                (cutoff,),
            )

            stats = dict(cursor.fetchone())

            if stats["total"] == 0:
                return {
                    "period_days": days,
                    "total_predictions": 0,
                    "accuracy": 0,
                    "message": "No evaluated predictions in this period",
                }

            # By confidence level
            cursor.execute(
                """
                SELECT
                    confidence_level,
                    COUNT(*) as total,
                    SUM(outcome_correct) as correct
                FROM predictions
                WHERE evaluated = 1 AND match_date >= ?
                GROUP BY confidence_level
            """,
                (cutoff,),
            )

            by_confidence = {}
            for row in cursor.fetchall():
                by_confidence[row["confidence_level"]] = {
                    "total": row["total"],
                    "correct": row["correct"] or 0,
                    "accuracy": (row["correct"] or 0) / row["total"] if row["total"] > 0 else 0,
                }

            # Model comparison
            cursor.execute(
                """
                SELECT
                    model_name,
                    COUNT(*) as total,
                    SUM(is_correct) as correct
                FROM model_performance mp
                JOIN predictions p ON mp.fixture_id = p.fixture_id
                WHERE p.evaluated = 1 AND p.match_date >= ?
                GROUP BY model_name
                ORDER BY SUM(is_correct) * 1.0 / COUNT(*) DESC
            """,
                (cutoff,),
            )

            model_comparison = {}
            for row in cursor.fetchall():
                model_comparison[row["model_name"]] = {
                    "total": row["total"],
                    "correct": row["correct"] or 0,
                    "accuracy": (row["correct"] or 0) / row["total"] if row["total"] > 0 else 0,
                }

            # By league
            cursor.execute(
                """
                SELECT
                    league_id,
                    league_name,
                    COUNT(*) as total,
                    SUM(outcome_correct) as correct,
                    AVG(brier_score) as avg_brier
                FROM predictions
                WHERE evaluated = 1 AND match_date >= ?
                GROUP BY league_id
                ORDER BY COUNT(*) DESC
            """,
                (cutoff,),
            )

            by_league = {}
            for row in cursor.fetchall():
                by_league[str(row["league_id"])] = {
                    "name": row["league_name"],
                    "total": row["total"],
                    "correct": row["correct"] or 0,
                    "accuracy": (row["correct"] or 0) / row["total"] if row["total"] > 0 else 0,
                    "avg_brier": row["avg_brier"] or 0,
                }

            return {
                "period_days": days,
                "total_predictions": stats["total"],
                "correct_predictions": stats["correct"] or 0,
                "accuracy": (stats["correct"] or 0) / stats["total"],
                "avg_confidence": stats["avg_conf"] or 0,
                "min_confidence": stats["min_conf"] or 0,
                "max_confidence": stats["max_conf"] or 0,
                "avg_brier_score": stats["avg_brier"] or 0,
                "by_confidence": by_confidence,
                "model_comparison": model_comparison,
                "by_league": by_league,
                "last_updated": datetime.now().isoformat(),
            }

    @staticmethod
    def get_all_time_stats() -> Dict:
        """Get all-time performance statistics."""
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(outcome_correct) as correct,
                    AVG(brier_score) as avg_brier,
                    SUM(btts_correct) as btts_correct,
                    SUM(CASE WHEN btts_prob IS NOT NULL THEN 1 ELSE 0 END) as btts_total,
                    SUM(over25_correct) as over25_correct,
                    SUM(CASE WHEN over25_prob IS NOT NULL THEN 1 ELSE 0 END) as over25_total,
                    SUM(exact_score) as exact_scores
                FROM predictions
                WHERE evaluated = 1
            """
            )

            stats = dict(cursor.fetchone())

            if stats["total"] == 0:
                return {
                    "total_predictions": 0,
                    "accuracy": 0,
                    "message": "No evaluated predictions yet",
                }

            return {
                "total_predictions": stats["total"],
                "correct_predictions": stats["correct"] or 0,
                "accuracy": (stats["correct"] or 0) / stats["total"],
                "avg_brier_score": stats["avg_brier"] or 0,
                "btts_accuracy": (
                    (stats["btts_correct"] or 0) / stats["btts_total"] if stats["btts_total"] else 0
                ),
                "over25_accuracy": (
                    (stats["over25_correct"] or 0) / stats["over25_total"]
                    if stats["over25_total"]
                    else 0
                ),
                "exact_score_count": stats["exact_scores"] or 0,
                "exact_score_rate": (stats["exact_scores"] or 0) / stats["total"],
            }

    @staticmethod
    def get_daily_trend(days: int = 30) -> List[Dict]:
        """Get daily accuracy trend."""
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    date,
                    total_predictions,
                    correct_predictions,
                    accuracy,
                    avg_confidence,
                    avg_brier_score
                FROM daily_metrics
                WHERE date >= date('now', ? || ' days')
                ORDER BY date ASC
            """,
                (f"-{days}",),
            )

            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def get_recent_predictions(limit: int = 50) -> List[Dict]:
        """Get recent predictions with their evaluations."""
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    fixture_id, home_team, away_team, league_name, match_date,
                    home_win_prob, draw_prob, away_win_prob,
                    predicted_outcome, confidence, confidence_level,
                    predicted_scoreline, btts_prob, over25_prob,
                    result_home_goals, result_away_goals, actual_outcome,
                    outcome_correct, brier_score, btts_correct, over25_correct,
                    evaluated
                FROM predictions
                ORDER BY match_date DESC
                LIMIT ?
            """,
                (limit,),
            )

            return [dict(row) for row in cursor.fetchall()]


# Initialize database on module load
init_database()
