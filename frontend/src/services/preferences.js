// Lightweight localStorage-backed preferences for user selections.
// Keys: league (number), season (number), oddsFormat ('decimal' | 'fractional' | 'american')

const STORAGE_KEY = "fixturecast_prefs";

function isBrowser() {
  return typeof window !== "undefined" && typeof localStorage !== "undefined";
}

function loadPrefs() {
  if (!isBrowser()) return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch (e) {
    console.warn("Unable to load prefs", e);
    return {};
  }
}

function savePrefs(nextPrefs) {
  if (!isBrowser()) return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextPrefs));
  } catch (e) {
    console.warn("Unable to save prefs", e);
  }
}

export function getSavedLeague(fallback = 39) {
  const prefs = loadPrefs();
  return Number.isFinite(prefs.league) ? prefs.league : fallback;
}

export function saveLeague(leagueId) {
  const prefs = loadPrefs();
  prefs.league = leagueId;
  savePrefs(prefs);
}

export function getSavedSeason(fallback) {
  const prefs = loadPrefs();
  return Number.isFinite(prefs.season) ? prefs.season : fallback;
}

export function saveSeason(season) {
  const prefs = loadPrefs();
  prefs.season = season;
  savePrefs(prefs);
}

export function getSavedOddsFormat(fallback = "decimal") {
  const prefs = loadPrefs();
  return prefs.oddsFormat || fallback;
}

export function saveOddsFormat(format) {
  const prefs = loadPrefs();
  prefs.oddsFormat = format;
  savePrefs(prefs);
}
