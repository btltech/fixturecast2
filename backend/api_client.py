import json
import logging
import os
import time
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, Optional

import requests

# Optional Redis support
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis-based caching layer with automatic fallback to in-memory cache.
    Provides distributed caching for multi-instance deployments.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "fixturecast:",
    ):
        self.prefix = prefix
        self.fallback_cache: Dict[str, Any] = {}  # In-memory fallback
        self.redis_client: Optional[redis.Redis] = None

        if REDIS_AVAILABLE:
            try:
                redis_url = os.environ.get("REDIS_URL")
                if redis_url:
                    self.redis_client = redis.from_url(redis_url, decode_responses=True)
                else:
                    self.redis_client = redis.Redis(
                        host=os.environ.get("REDIS_HOST", host),
                        port=int(os.environ.get("REDIS_PORT", port)),
                        db=db,
                        password=password,
                        decode_responses=True,
                        socket_timeout=2,
                        socket_connect_timeout=2,
                    )
                # Test connection
                self.redis_client.ping()
                logger.info("✅ Redis cache connected successfully")
            except Exception as e:
                logger.warning(f"⚠️ Redis connection failed, using in-memory cache: {e}")
                self.redis_client = None
        else:
            logger.info("ℹ️ Redis not installed, using in-memory cache")

    def get(self, key: str) -> Optional[Any]:
        """Get a value from cache (Redis or fallback)."""
        full_key = f"{self.prefix}{key}"

        if self.redis_client:
            try:
                data = self.redis_client.get(full_key)
                if data:
                    return json.loads(data)
            except Exception as e:
                logger.debug(f"Redis get failed: {e}")

        # Fallback to in-memory
        if full_key in self.fallback_cache:
            item = self.fallback_cache[full_key]
            if time.time() < item.get("expires_at", 0):
                return item.get("data")
            else:
                del self.fallback_cache[full_key]

        return None

    def set(self, key: str, value: Any, ttl: int = 60) -> bool:
        """Set a value in cache with TTL."""
        full_key = f"{self.prefix}{key}"

        if self.redis_client:
            try:
                self.redis_client.setex(full_key, ttl, json.dumps(value))
                return True
            except Exception as e:
                logger.debug(f"Redis set failed: {e}")

        # Fallback to in-memory
        self.fallback_cache[full_key] = {"data": value, "expires_at": time.time() + ttl}
        return True

    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        full_key = f"{self.prefix}{key}"

        if self.redis_client:
            try:
                self.redis_client.delete(full_key)
            except Exception as e:
                logger.debug(f"Redis delete failed: {e}")

        if full_key in self.fallback_cache:
            del self.fallback_cache[full_key]

        return True

    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching a pattern."""
        full_pattern = f"{self.prefix}{pattern}"
        deleted = 0

        if self.redis_client:
            try:
                for key in self.redis_client.scan_iter(match=full_pattern):
                    self.redis_client.delete(key)
                    deleted += 1
            except Exception as e:
                logger.debug(f"Redis clear pattern failed: {e}")

        # Clear matching keys from fallback
        to_delete = [
            k for k in self.fallback_cache.keys() if k.startswith(full_pattern.replace("*", ""))
        ]
        for key in to_delete:
            del self.fallback_cache[key]
            deleted += 1

        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = {
            "redis_available": self.redis_client is not None,
            "fallback_size": len(self.fallback_cache),
        }

        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats["redis_keys"] = info.get("db0", {}).get("keys", 0)
                stats["redis_memory"] = info.get("used_memory_human", "N/A")
            except Exception:
                pass

        return stats


class ApiClient:
    """
    API-Football client with best practices:
    - Redis caching with in-memory fallback
    - Rate limiting with retry logic (429 handling)
    - Quota monitoring via /status endpoint
    - Exponential backoff on errors
    - Request throttling (respects 450/min Ultra plan limit)
    """

    def __init__(self, config):
        self.config = config
        self.api_key = os.environ.get("API_FOOTBALL_KEY", config.get("api_key"))
        self.base_url = config.get("api_base_url")
        self.allowed_leagues = set(config.get("allowed_competitions", []))

        # Competition metadata for type-aware predictions
        self.competition_metadata = config.get("competition_metadata", {})

        # Initialize Redis cache (falls back to in-memory if unavailable)
        self.cache = RedisCache()

        # Rate limiting - Ultra plan: 450 requests/minute
        self.rate_limit = 450
        self.rate_window = 60  # seconds
        self.request_times = []
        self.rate_lock = Lock()

        # Quota tracking
        self.quota_info = {
            "requests_today": 0,
            "requests_limit": 7500,  # Ultra plan daily limit
            "last_checked": None,
        }

        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 1  # Base delay in seconds

        # TTLs in seconds
        self.ttls = {
            "fixtures": 60,
            "standings": 300,
            "team_stats": 600,
            "squads": 3600,
            "injuries": 900,
            "odds": 60,
            "teams": 86400,  # Cache teams for a day
            "players": 3600,  # Cache player stats for 1 hour
            "events": 300,  # Cache fixture events for 5 min
            "statistics": 300,  # Cache fixture statistics for 5 min
            "coachs": 86400,  # Cache coach info for a day
            "sidelined": 3600,  # Cache sidelined players for 1 hour
            "rounds": 3600,  # Cache round info for 1 hour
            "status": 60,  # Cache status for 1 min
        }

    def get_competition_info(self, league_id):
        """
        Get competition metadata including type, format, and special rules.
        Returns dict with: type, format, two_leg_knockout, neutral_final, prestige_factor
        """
        league_str = str(league_id)
        if league_str in self.competition_metadata:
            return self.competition_metadata[league_str]

        # Default for unknown leagues
        return {
            "name": f"League {league_id}",
            "type": "domestic_league",
            "format": "league",
            "two_leg_knockout": False,
            "neutral_final": False,
            "prestige_factor": 1.0,
        }

    def get_fixture_round(self, fixture_id):
        """
        Get the round information for a fixture (e.g., 'Group A - 5', 'Round of 16', 'Final').
        Useful for determining knockout vs group stage.
        """
        result = self._call_api("fixtures", {"id": fixture_id}, "fixtures")
        if result and result.get("response"):
            fixture = result["response"][0]
            league_round = fixture.get("league", {}).get("round", "")
            return {
                "round": league_round,
                "is_knockout": self._is_knockout_round(league_round),
                "is_final": "final" in league_round.lower(),
                "is_group_stage": "group" in league_round.lower(),
            }
        return {"round": "", "is_knockout": False, "is_final": False, "is_group_stage": False}

    def _is_knockout_round(self, round_name):
        """Determine if a round is a knockout round based on its name."""
        knockout_keywords = [
            "round of",
            "quarter",
            "semi",
            "final",
            "knockout",
            "elimination",
            "playoff",
            "1/8",
            "1/4",
            "1/2",
        ]
        round_lower = round_name.lower()
        return any(kw in round_lower for kw in knockout_keywords)

    def _get_cache_key(self, endpoint, params):
        param_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        return f"{endpoint}:{param_str}"

    def _get_from_cache(self, key):
        """Get data from Redis/in-memory cache."""
        return self.cache.get(key)

    def _set_cache(self, key, data, ttl_type):
        """Set data in Redis/in-memory cache with appropriate TTL."""
        ttl = self.ttls.get(ttl_type, 60)
        self.cache.set(key, data, ttl)

    def _wait_for_rate_limit(self):
        """
        Rate limiting: Ensure we don't exceed 450 requests/minute (Ultra plan).
        Uses a sliding window approach.
        """
        with self.rate_lock:
            now = time.time()
            # Remove requests older than the rate window
            self.request_times = [t for t in self.request_times if now - t < self.rate_window]

            if len(self.request_times) >= self.rate_limit:
                # Calculate wait time
                oldest = self.request_times[0]
                wait_time = self.rate_window - (now - oldest) + 0.1
                if wait_time > 0:
                    print(f"API: Rate limit approaching, waiting {wait_time:.2f}s")
                    time.sleep(wait_time)

            self.request_times.append(time.time())

    def get_api_status(self):
        """
        Check API quota status. Call this to monitor usage.
        Returns: { requests_today, requests_limit, requests_remaining }
        """
        key = "status"
        cached = self._get_from_cache(key)
        if cached:
            return cached

        headers = {"x-rapidapi-host": "v3.football.api-sports.io", "x-rapidapi-key": self.api_key}
        try:
            response = requests.get(f"{self.base_url}/status", headers=headers)
            data = response.json()

            if data.get("response"):
                status = data["response"]
                self.quota_info = {
                    "requests_today": status.get("requests", {}).get("current", 0),
                    "requests_limit": status.get("requests", {}).get("limit_day", 7500),
                    "requests_remaining": status.get("requests", {}).get("limit_day", 7500)
                    - status.get("requests", {}).get("current", 0),
                    "last_checked": datetime.now().isoformat(),
                }
                self._set_cache(key, self.quota_info, "status")
                return self.quota_info
        except Exception as e:
            print(f"API: Failed to get status: {e}")

        return self.quota_info

    def _call_api(self, endpoint, params, ttl_type):
        print(f"API: Calling {endpoint} with params {params}")

        # League restriction check
        if "league" in params:
            if int(params["league"]) not in self.allowed_leagues:
                print(f"Blocked request to disallowed league: {params['league']}")
                return {"errors": ["League not allowed"]}

        key = self._get_cache_key(endpoint, params)
        cached = self._get_from_cache(key)
        if cached:
            print(f"API: Returning cached data for {key}")
            return cached

        # Rate limiting
        self._wait_for_rate_limit()

        # Real API Call with retry logic
        headers = {"x-rapidapi-host": "v3.football.api-sports.io", "x-rapidapi-key": self.api_key}

        last_error = None
        for attempt in range(self.max_retries):
            try:
                print(f"API: Making request to {self.base_url}/{endpoint} (attempt {attempt + 1})")
                response = requests.get(
                    f"{self.base_url}/{endpoint}", headers=headers, params=params, timeout=30
                )

                # Handle rate limiting (429)
                if response.status_code == 429:
                    retry_after = int(
                        response.headers.get("Retry-After", self.retry_delay * (2**attempt))
                    )
                    print(f"API: Rate limited (429), waiting {retry_after}s before retry")
                    time.sleep(retry_after)
                    continue

                # Handle server errors with retry
                if response.status_code >= 500:
                    wait_time = self.retry_delay * (2**attempt)  # Exponential backoff
                    print(f"API: Server error {response.status_code}, retrying in {wait_time}s")
                    time.sleep(wait_time)
                    continue

                data = response.json()

                if "errors" in data and data["errors"]:
                    print(f"API ERROR: {data['errors']}")
                else:
                    print(f"API: Success - {data.get('results', 0)} results")

                self._set_cache(key, data, ttl_type)
                return data

            except requests.exceptions.Timeout:
                last_error = "Request timeout"
                wait_time = self.retry_delay * (2**attempt)
                print(f"API: Timeout, retrying in {wait_time}s")
                time.sleep(wait_time)
            except requests.exceptions.ConnectionError as e:
                last_error = str(e)
                wait_time = self.retry_delay * (2**attempt)
                print(f"API: Connection error, retrying in {wait_time}s")
                time.sleep(wait_time)
            except Exception as e:
                last_error = str(e)
                print(f"API Error: {e}")
                break

        print(f"API: All retries failed for {endpoint}")
        return {"errors": [last_error or "Request failed after retries"]}

    # Public methods matching requirements
    def get_fixtures(self, league_id=None, season=None, date=None, next_n=None):
        """
        Get fixtures for a league.
        The 'next' parameter doesn't work well, so we use date ranges instead.
        If season is not provided, it will be automatically determined based on the current date.
        """
        # Auto-detect season if not provided
        if season is None:
            today = datetime.now()
            # Football seasons typically start in August
            # If we're before August, use previous year, otherwise use current year
            if today.month < 8:
                season = today.year - 1
            else:
                season = today.year

        params = {"season": season}
        if league_id:
            params["league"] = league_id

        if date:
            params["date"] = date
        elif next_n:
            # Convert next_n to a date range (today to N days from now)
            today = datetime.now()
            # Look ahead for next_n days to get upcoming fixtures
            from_date = today.strftime("%Y-%m-%d")
            to_date = (today + timedelta(days=next_n * 7)).strftime(
                "%Y-%m-%d"
            )  # Multiply by 7 to get enough fixtures
            params["from"] = from_date
            params["to"] = to_date
            params["status"] = "NS"  # Only get not started fixtures

        return self._call_api("fixtures", params, "fixtures")

    def get_fixture_details(self, fixture_id):
        return self._call_api("fixtures", {"id": fixture_id}, "fixtures")

    def get_teams(self, league_id=None, season=2025, team_id=None):
        if team_id:
            # If fetching by ID, we don't need other params
            return self._call_api("teams", {"id": team_id}, "teams")

        params = {"season": season}
        if league_id:
            params["league"] = league_id
        return self._call_api("teams", params, "teams")

    def get_team_stats(self, team_id, league_id, season=2025):
        return self._call_api(
            "teams/statistics",
            {"team": team_id, "league": league_id, "season": season},
            "team_stats",
        )

    def get_standings(self, league_id, season=2025):
        return self._call_api("standings", {"league": league_id, "season": season}, "standings")

    def get_h2h(self, team1_id, team2_id, last=10):
        """Get head-to-head matches between two teams"""
        response = self._call_api(
            "fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}", "last": last}, "fixtures"
        )

        # Process the response to add stats
        if response.get("response"):
            matches = response["response"]
            home_wins = sum(
                1
                for m in matches
                if m["teams"]["home"]["id"] == team1_id and m["goals"]["home"] > m["goals"]["away"]
            )
            away_wins = sum(
                1
                for m in matches
                if m["teams"]["away"]["id"] == team1_id and m["goals"]["away"] > m["goals"]["home"]
            )
            draws = sum(1 for m in matches if m["goals"]["home"] == m["goals"]["away"])

            return {
                "response": matches,
                "home_wins": home_wins,
                "away_wins": away_wins,
                "draws": draws,
                "total_meetings": len(matches),
                "recent_matches": matches[:5],
            }
        return response

    def get_live_fixtures(self):
        """Get currently live matches"""
        return self._call_api("fixtures", {"live": "all"}, "fixtures")

    def get_injuries(self, team_id, season=2025):
        return self._call_api("injuries", {"team": team_id, "season": season}, "injuries")

    def get_odds(self, fixture_id):
        return self._call_api("odds", {"fixture": fixture_id}, "odds")

    def get_last_fixtures(self, team_id=None, league=None, league_id=None, season=2025, last=10):
        """Get recent completed fixtures"""
        params = {"season": season, "last": last, "status": "FT"}
        if team_id:
            params["team"] = team_id
        if league or league_id:
            params["league"] = league or league_id
        return self._call_api("fixtures", params, "fixtures")

    def get_next_fixtures(self, team_id, league_id, season=2025, next_n=3):
        return self._call_api(
            "fixtures",
            {"team": team_id, "league": league_id, "season": season, "next": next_n},
            "fixtures",
        )

    # ========== NEW ENHANCED DATA ENDPOINTS ==========

    def get_players(self, team_id, season=2025):
        """
        Get all players for a team with their season statistics.
        Returns goals, assists, minutes played, cards, etc.
        """
        return self._call_api("players", {"team": team_id, "season": season}, "players")

    def get_fixture_events(self, fixture_id):
        """
        Get events for a specific fixture (goals, cards, substitutions).
        Useful for analyzing goal timing patterns and discipline.
        """
        return self._call_api("fixtures/events", {"fixture": fixture_id}, "events")

    def get_fixture_statistics(self, fixture_id):
        """
        Get detailed match statistics (shots, possession, xG if available).
        """
        return self._call_api("fixtures/statistics", {"fixture": fixture_id}, "statistics")

    def get_coach(self, team_id):
        """
        Get coach information including name, career history, and tenure at current club.
        """
        return self._call_api("coachs", {"team": team_id}, "coachs")

    def get_sidelined(self, team_id, season=2025):
        """
        Get detailed sidelined players (injuries + suspensions) with return dates.
        More detailed than basic injuries endpoint.
        """
        # Note: This may require the player ID, so we use injuries as fallback
        # If sidelined endpoint doesn't work well, injuries are already being fetched
        return self._call_api("sidelined", {"team": team_id}, "sidelined")

    def get_top_scorers(self, league_id, season=2025):
        """
        Get top scorers in a league - useful for context about key players.
        """
        return self._call_api(
            "players/topscorers", {"league": league_id, "season": season}, "players"
        )

    def get_top_assists(self, league_id, season=2025):
        """
        Get top assist providers in a league.
        """
        return self._call_api(
            "players/topassists", {"league": league_id, "season": season}, "players"
        )

    def get_recent_fixture_stats(self, fixture_ids):
        """
        Get statistics for multiple recent fixtures.
        Returns aggregated stats for analysis.
        """
        all_stats = []
        for fid in fixture_ids[:5]:  # Limit to last 5 to conserve API calls
            stats = self.get_fixture_statistics(fid)
            if stats.get("response"):
                all_stats.append({"fixture_id": fid, "stats": stats["response"]})
        return all_stats
