#!/usr/bin/env python3
"""
Simple backend API server for FixtureCast.
Provides fixtures and teams data from API-Football.
Runs on port 8001 to avoid conflict with ML API (port 8000).
"""

import asyncio
import json
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add paths
sys.path.append(os.path.dirname(__file__))

from api_client import ApiClient
from fastapi.responses import Response
from og_image_generator import generate_default_og_image, generate_prediction_og_image

# Prometheus metrics (manual implementation for flexibility)
METRICS = {
    "requests_total": 0,
    "requests_by_endpoint": {},
    "request_latency_seconds": [],
    "errors_total": 0,
    "uptime_start": time.time(),
}

# Initialize API client (will be set in lifespan)
api_client = None

# Big teams with their importance ranking (lower = bigger team)
BIG_TEAMS = {
    # Premier League Top Teams
    50: {"name": "Manchester City", "rank": 1},
    40: {"name": "Liverpool", "rank": 2},
    42: {"name": "Arsenal", "rank": 3},
    49: {"name": "Chelsea", "rank": 4},
    33: {"name": "Manchester United", "rank": 5},
    47: {"name": "Tottenham", "rank": 6},
    34: {"name": "Newcastle", "rank": 10},
    66: {"name": "Aston Villa", "rank": 12},
    48: {"name": "West Ham", "rank": 15},
    # La Liga Top Teams
    541: {"name": "Real Madrid", "rank": 1},
    529: {"name": "Barcelona", "rank": 2},
    530: {"name": "Atletico Madrid", "rank": 7},
    # Serie A Top Teams
    489: {"name": "AC Milan", "rank": 8},
    496: {"name": "Juventus", "rank": 9},
    505: {"name": "Inter Milan", "rank": 6},
    492: {"name": "Napoli", "rank": 11},
    # Bundesliga Top Teams
    157: {"name": "Bayern Munich", "rank": 3},
    165: {"name": "Borussia Dortmund", "rank": 10},
    173: {"name": "RB Leipzig", "rank": 14},
    # Ligue 1 Top Teams
    85: {"name": "Paris Saint-Germain", "rank": 4},
    81: {"name": "Marseille", "rank": 18},
    80: {"name": "Lyon", "rank": 20},
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global api_client
    # Startup
    logger.info("🚀 Starting FixtureCast Backend API...")
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path) as f:
            config = json.load(f)
        api_client = ApiClient(config)
        logger.info("✅ API client initialized successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to initialize API client: {e}")
        raise

    yield  # Application runs here

    # Shutdown
    logger.info("🛑 Shutting down FixtureCast Backend API...")
    api_client = None


app = FastAPI(
    title="FixtureCast Backend API",
    description="Backend API for fixtures and teams data",
    version="2.0.0",
    lifespan=lifespan,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def track_metrics(request, call_next):
    """Middleware to track request metrics"""
    start_time = time.time()
    METRICS["requests_total"] += 1

    endpoint = request.url.path
    METRICS["requests_by_endpoint"][endpoint] = METRICS["requests_by_endpoint"].get(endpoint, 0) + 1

    try:
        response = await call_next(request)
        latency = time.time() - start_time
        METRICS["request_latency_seconds"].append(latency)
        # Keep only last 1000 latencies to prevent memory bloat
        if len(METRICS["request_latency_seconds"]) > 1000:
            METRICS["request_latency_seconds"] = METRICS["request_latency_seconds"][-1000:]
        return response
    except Exception:
        METRICS["errors_total"] += 1
        raise


logger.info("🚀 DEBUG: BACKEND_API MODULE LOADED")


@app.get("/")
async def root():
    return {"service": "FixtureCast Backend API", "version": "2.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring"""
    return {
        "status": "healthy",
        "service": "backend-api",
        "api_client_ready": api_client is not None,
        "uptime_seconds": time.time() - METRICS["uptime_start"],
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint.
    Returns metrics in Prometheus text exposition format.
    """
    uptime = time.time() - METRICS["uptime_start"]
    avg_latency = (
        sum(METRICS["request_latency_seconds"]) / len(METRICS["request_latency_seconds"])
        if METRICS["request_latency_seconds"]
        else 0
    )

    # Build Prometheus format output
    lines = [
        "# HELP backend_requests_total Total number of HTTP requests",
        "# TYPE backend_requests_total counter",
        f'backend_requests_total {METRICS["requests_total"]}',
        "",
        "# HELP backend_errors_total Total number of errors",
        "# TYPE backend_errors_total counter",
        f'backend_errors_total {METRICS["errors_total"]}',
        "",
        "# HELP backend_uptime_seconds Uptime in seconds",
        "# TYPE backend_uptime_seconds gauge",
        f"backend_uptime_seconds {uptime:.2f}",
        "",
        "# HELP backend_request_latency_avg_seconds Average request latency",
        "# TYPE backend_request_latency_avg_seconds gauge",
        f"backend_request_latency_avg_seconds {avg_latency:.4f}",
        "",
        "# HELP backend_api_client_ready API client initialization status",
        "# TYPE backend_api_client_ready gauge",
        f"backend_api_client_ready {1 if api_client else 0}",
    ]

    # Add per-endpoint metrics
    lines.append("")
    lines.append("# HELP backend_requests_by_endpoint Requests by endpoint")
    lines.append("# TYPE backend_requests_by_endpoint counter")
    for endpoint, count in METRICS["requests_by_endpoint"].items():
        # Escape endpoint for Prometheus label
        safe_endpoint = endpoint.replace('"', '\\"')
        lines.append(f'backend_requests_by_endpoint{{endpoint="{safe_endpoint}"}} {count}')

    from starlette.responses import PlainTextResponse

    return PlainTextResponse("\n".join(lines), media_type="text/plain")


@app.get("/api/fixtures")
async def get_fixtures(
    league: int = Query(39, description="League ID"),
    next: int = Query(20, description="Number of next fixtures"),
    season: int = Query(None, description="Season year (optional)"),
    today_only: bool = Query(False, description="Only show today's fixtures"),
):
    """Get upcoming fixtures for a league"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        if today_only:
            # Get fixtures for today only
            today = datetime.now().strftime("%Y-%m-%d")
            result = api_client.get_fixtures(league_id=league, season=season, date=today)
        else:
            result = api_client.get_fixtures(league_id=league, season=season, next_n=next)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/fixtures/today")
async def get_todays_fixtures():
    """
    Get all fixtures playing today across all supported leagues.
    Returns fixtures sorted by importance (big teams first).
    """
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        today = datetime.now().strftime("%Y-%m-%d")
        all_fixtures = []

        # Supported leagues
        leagues = [39, 140, 135, 78, 61, 88, 94, 40, 141, 136, 79, 62, 2, 3]

        # Fetch all leagues in parallel
        async def fetch_league(league_id):
            try:
                # Run synchronous API call in a thread
                return await asyncio.to_thread(
                    api_client.get_fixtures, league_id=league_id, date=today
                )
            except Exception as e:
                print(f"Error fetching fixtures for league {league_id}: {e}")
                return None

        results = await asyncio.gather(*[fetch_league(lid) for lid in leagues])

        for result in results:
            if result and result.get("response"):
                all_fixtures.extend(result["response"])

        # Calculate importance score for each fixture
        def calculate_importance(fixture):
            home_id = fixture["teams"]["home"]["id"]
            away_id = fixture["teams"]["away"]["id"]

            home_rank = BIG_TEAMS.get(home_id, {}).get("rank", 50)
            away_rank = BIG_TEAMS.get(away_id, {}).get("rank", 50)

            # Lower rank = bigger team = more important
            # If both teams are big, it's an even bigger match
            importance = 100 - min(home_rank, away_rank)

            # Bonus if both teams are in the big teams list
            if home_id in BIG_TEAMS and away_id in BIG_TEAMS:
                importance += 20

            return importance

        # Sort by importance (highest first)
        all_fixtures.sort(key=calculate_importance, reverse=True)

        # Mark the top fixture as "Match of the Day"
        match_of_the_day = all_fixtures[0] if all_fixtures else None

        return {
            "response": all_fixtures,
            "match_of_the_day": match_of_the_day,
            "total_matches": len(all_fixtures),
            "date": today,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/match-of-the-day")
async def get_match_of_the_day():
    """
    Get the biggest match playing today based on team importance.
    """
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        today = datetime.now().strftime("%Y-%m-%d")
        best_match = None
        best_importance = -1

        # Priority leagues (top 5 leagues first)
        priority_leagues = [39, 140, 135, 78, 61, 2, 3]  # Include UCL/UEL

        for league_id in priority_leagues:
            try:
                result = api_client.get_fixtures(league_id=league_id, date=today)
                if result.get("response"):
                    for fixture in result["response"]:
                        home_id = fixture["teams"]["home"]["id"]
                        away_id = fixture["teams"]["away"]["id"]

                        home_rank = BIG_TEAMS.get(home_id, {}).get("rank", 50)
                        away_rank = BIG_TEAMS.get(away_id, {}).get("rank", 50)

                        importance = 100 - min(home_rank, away_rank)
                        if home_id in BIG_TEAMS and away_id in BIG_TEAMS:
                            importance += 30  # Big clash bonus

                        if importance > best_importance:
                            best_importance = importance
                            best_match = fixture
            except Exception:
                continue

        if best_match:
            return {
                "match": best_match,
                "importance_score": best_importance,
                "is_big_clash": best_importance > 100,
                "date": today,
            }
        else:
            return {"match": None, "message": "No matches scheduled for today", "date": today}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/teams")
async def get_teams(
    league: int = Query(None, description="League ID"),
    season: int = Query(2025, description="Season year"),
    id: int = Query(None, description="Team ID"),
):
    """Get teams in a league or specific team details"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        # If neither league nor id is provided, default to PL
        if not league and not id:
            league = 39

        result = api_client.get_teams(league_id=league, season=season, team_id=id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team/{team_id}/stats")
async def get_team_stats(
    team_id: int,
    league: int = Query(39, description="League ID"),
    season: int = Query(2025, description="Season year"),
):
    """Get statistics for a specific team"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_team_stats(team_id, league, season)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team/{team_id}/fixtures")
def get_team_fixtures(
    team_id: int,
    league: int = Query(..., description="League ID"),
    season: int = Query(2025, description="Season year"),
    last: int = Query(10, description="Number of last fixtures"),
):
    """Get recent fixtures for a specific team"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_last_fixtures(
            team_id=team_id, league=league, season=season, last=last
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team/{team_id}/upcoming")
async def get_team_upcoming(
    team_id: int,
    league: int = Query(39, description="League ID"),
    season: int = Query(2025, description="Season year"),
    next: int = Query(3, description="Number of upcoming matches"),
):
    """Get upcoming fixtures for a specific team"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_next_fixtures(team_id, league, season, next)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team/{team_id}/injuries")
async def get_team_injuries(team_id: int, season: int = Query(2025, description="Season year")):
    """Get current injuries for a specific team"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_injuries(team_id, season)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team/{team_id}/squad")
async def get_team_squad(team_id: int, season: int = Query(2025, description="Season year")):
    """Get squad/players for a specific team"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_players(team_id, season)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/standings")
async def get_standings(
    league: int = Query(..., description="League ID"),
    season: int = Query(2025, description="Season year"),
):
    """Get league standings"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_standings(league, season)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/results")
async def get_results(
    league: int = Query(39, description="League ID"),
    last: int = Query(20, description="Number of last matches"),
    season: int = Query(2025, description="Season year"),
):
    """Get recent match results"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_last_fixtures(league=league, season=season, last=last)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/h2h/{team1_id}/{team2_id}")
async def get_h2h(
    team1_id: int, team2_id: int, last: int = Query(10, description="Number of recent meetings")
):
    """Get head-to-head statistics between two teams"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_h2h(team1_id, team2_id, last)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/live")
async def get_live_scores():
    """Get live match scores"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        result = api_client.get_live_fixtures()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/og-image/{fixture_id}")
async def get_og_image(fixture_id: int, league: int = Query(39)):
    """Generate Open Graph (OG) image for social media sharing"""
    if api_client is None:
        raise HTTPException(status_code=503, detail="API client not initialized")

    try:
        # Get fixture details
        fixture_data = api_client.get_fixture(fixture_id)
        if not fixture_data or "response" not in fixture_data or not fixture_data["response"]:
            # Return default image if fixture not found
            image_data = generate_default_og_image(
                title="FixtureCast", subtitle="AI Football Predictions"
            )
            return Response(content=image_data, media_type="image/png")

        fixture = fixture_data["response"][0]
        home_team = fixture.get("teams", {}).get("home", {}).get("name", "Home")
        away_team = fixture.get("teams", {}).get("away", {}).get("name", "Away")
        league_name = fixture.get("league", {}).get("name", "League")

        # Try to get prediction data from ML API
        prediction_data = None
        try:
            import requests

            ml_api_url = os.getenv("ML_API_URL", "http://localhost:8000")
            pred_response = requests.get(
                f"{ml_api_url}/api/prediction/{fixture_id}?league={league}", timeout=5
            )
            if pred_response.status_code == 200:
                pred_json = pred_response.json()
                prediction_data = pred_json.get("prediction")
        except Exception as e:
            logger.warning(f"Could not fetch prediction for OG image: {e}")

        # Generate image
        image_data = generate_prediction_og_image(
            fixture_id=fixture_id,
            home_team=home_team,
            away_team=away_team,
            prediction_data=prediction_data,
            league_name=league_name,
        )

        return Response(
            content=image_data,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Content-Disposition": f"inline; filename=prediction_{fixture_id}.png",
            },
        )

    except Exception as e:
        logger.error(f"Error generating OG image: {e}")
        # Return default image on error
        image_data = generate_default_og_image()
        return Response(content=image_data, media_type="image/png")


@app.get("/api/og-image/daily")
async def get_daily_og_image():
    """Generate OG image for daily fixtures page"""
    try:
        from datetime import date

        today_str = date.today().strftime("%B %d, %Y")
        image_data = generate_default_og_image(
            title="Today's Predictions", subtitle=f"AI Football Predictions - {today_str}"
        )
        return Response(
            content=image_data,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except Exception as e:
        logger.error(f"Error generating daily OG image: {e}")
        image_data = generate_default_og_image()
        return Response(content=image_data, media_type="image/png")


@app.get("/api/og-image/home")
async def get_home_og_image():
    """Generate OG image for homepage"""
    try:
        image_data = generate_default_og_image(
            title="FixtureCast", subtitle="AI-Powered Football Predictions"
        )
        return Response(
            content=image_data,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400"},  # Cache for 24 hours
        )
    except Exception as e:
        logger.error(f"Error generating home OG image: {e}")
        image_data = generate_default_og_image()
        return Response(content=image_data, media_type="image/png")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8001))
    print(f"Starting FixtureCast Backend API server on port {port}...")
    print(f" API docs will be available at http://localhost:{port}/docs")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
