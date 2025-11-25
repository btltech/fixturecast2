
# FixtureCast ML System

AI-powered football prediction system with live data from API-Football, covering 14 competitions across Europe.

## Setup

1. **Install Dependencies**:
   ```bash
   npm install
   pip install -r requirements.txt
   cd frontend && npm install
   ```

2. **Configuration**:
   - Edit `backend/config.json` to set your API-Football Key.
   - The app runs in real mode using live API-Football data.

3. **Run**:
   - `npm run start`: Runs both Backend (port 8000) and Frontend (port 5173).
   - `npm run ml`: Runs the ML training script (mock).

## Architecture

- **ML Engine**: Python-based ensemble of 11 models (GBDT, CatBoost, Poisson, etc.).
- **Backend**: FastAPI with caching, league restrictions, and feature building.
- **Frontend**: Svelte + Tailwind CSS with premium aesthetics.

## Supported Competitions

### 7 Top Leagues (Tier 1)
1. **Premier League** (England) - ID: 39
2. **La Liga** (Spain) - ID: 140
3. **Serie A** (Italy) - ID: 135
4. **Bundesliga** (Germany) - ID: 78
5. **Ligue 1** (France) - ID: 61
6. **Eredivisie** (Netherlands) - ID: 88
7. **Primeira Liga** (Portugal) - ID: 94

### 2 Championship Leagues (Tier 2)
8. **Championship** (England) - ID: 40
9. **Segunda División** (Spain) - ID: 141

### 5 Division 2 & Other Competitions
10. **Serie B** (Italy) - ID: 136
11. **2. Bundesliga** (Germany) - ID: 79
12. **Ligue 2** (France) - ID: 62
13. **UEFA Champions League** - ID: 2
14. **UEFA Europa League** - ID: 3

---

**Total: 14 Competitions** organized across 3 tiers for comprehensive European football coverage.
