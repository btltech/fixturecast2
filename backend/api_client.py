
import time
import requests
import json
import os
from datetime import datetime, timedelta

class ApiClient:
    def __init__(self, config):
        self.config = config
        self.api_key = os.environ.get("API_FOOTBALL_KEY", config.get("api_key"))
        self.base_url = config.get("api_base_url")
        self.allowed_leagues = set(config.get("allowed_competitions", []))
        
        # Competition metadata for type-aware predictions
        self.competition_metadata = config.get("competition_metadata", {})
        
        # Simple in-memory cache: { key: { "data": ..., "expires_at": ... } }
        self.cache = {}
        
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
            "prestige_factor": 1.0
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
            "round of", "quarter", "semi", "final", 
            "knockout", "elimination", "playoff", "1/8", "1/4", "1/2"
        ]
        round_lower = round_name.lower()
        return any(kw in round_lower for kw in knockout_keywords)

    def _get_cache_key(self, endpoint, params):
        param_str = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        return f"{endpoint}?{param_str}"

    def _get_from_cache(self, key):
        if key in self.cache:
            item = self.cache[key]
            if time.time() < item["expires_at"]:
                return item["data"]
            else:
                del self.cache[key]
        return None

    def _set_cache(self, key, data, ttl_type):
        ttl = self.ttls.get(ttl_type, 60)
        self.cache[key] = {
            "data": data,
            "expires_at": time.time() + ttl
        }

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
        
        # Real API Call
        headers = {
            'x-rapidapi-host': "v3.football.api-sports.io",
            'x-rapidapi-key': self.api_key
        }
        try:
            print(f"API: Making request to {self.base_url}/{endpoint}")
            response = requests.get(f"{self.base_url}/{endpoint}", headers=headers, params=params)
            data = response.json()
            
            if "errors" in data and data["errors"]:
                print(f"API ERROR: {data['errors']}")
            else:
                print(f"API: Success - {data.get('results', 0)} results")
            
            self._set_cache(key, data, ttl_type)
            return data
        except Exception as e:
            print(f"API Error: {e}")
            return {"errors": [str(e)]}

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
            to_date = (today + timedelta(days=next_n * 7)).strftime("%Y-%m-%d")  # Multiply by 7 to get enough fixtures
            params["from"] = from_date
            params["to"] = to_date
            params["status"] = "NS"  # Only get not started fixtures
        
        return self._call_api("fixtures", params, "fixtures")

    def get_fixture_details(self, fixture_id):
        return self._call_api("fixtures", {"id": fixture_id}, "fixtures")

    def get_teams(self, league_id, season=2025):
        return self._call_api("teams", {"league": league_id, "season": season}, "teams")

    def get_team_stats(self, team_id, league_id, season=2025):
        return self._call_api("teams/statistics", {"team": team_id, "league": league_id, "season": season}, "team_stats")

    def get_standings(self, league_id, season=2025):
        return self._call_api("standings", {"league": league_id, "season": season}, "standings")
    
    def get_h2h(self, team1_id, team2_id, last=10):
        """Get head-to-head matches between two teams"""
        response = self._call_api("fixtures/headtohead", {"h2h": f"{team1_id}-{team2_id}", "last": last}, "fixtures")
        
        # Process the response to add stats
        if response.get("response"):
            matches = response["response"]
            home_wins = sum(1 for m in matches if m["teams"]["home"]["id"] == team1_id and m["goals"]["home"] > m["goals"]["away"])
            away_wins = sum(1 for m in matches if m["teams"]["away"]["id"] == team1_id and m["goals"]["away"] > m["goals"]["home"])
            draws = sum(1 for m in matches if m["goals"]["home"] == m["goals"]["away"])
            
            return {
                "response": matches,
                "home_wins": home_wins,
                "away_wins": away_wins,
                "draws": draws,
                "total_meetings": len(matches),
                "recent_matches": matches[:5]
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
        return self._call_api("fixtures", {"team": team_id, "league": league_id, "season": season, "next": next_n}, "fixtures")

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
        return self._call_api("players/topscorers", {"league": league_id, "season": season}, "players")
    
    def get_top_assists(self, league_id, season=2025):
        """
        Get top assist providers in a league.
        """
        return self._call_api("players/topassists", {"league": league_id, "season": season}, "players")
    
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

