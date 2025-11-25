import { writable } from "svelte/store";

// Local storage helpers
const STORAGE_KEY = "fixturecast_favorites";

function loadFavorites() {
  if (typeof localStorage !== "undefined") {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : { teams: [], fixtures: [] };
  }
  return { teams: [], fixtures: [] };
}

function saveFavorites(favorites) {
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites));
  }
}

// Store
export const favorites = writable(loadFavorites());

// Actions
export function toggleTeamFavorite(team) {
  favorites.update((current) => {
    const teams = current.teams || [];
    const index = teams.findIndex((t) => t.id === team.id);

    let newTeams;
    if (index >= 0) {
      newTeams = teams.filter((t) => t.id !== team.id);
    } else {
      newTeams = [...teams, { id: team.id, name: team.name, logo: team.logo }];
    }

    const updated = { ...current, teams: newTeams };
    saveFavorites(updated);
    return updated;
  });
}

export function toggleFixtureFavorite(fixture) {
  favorites.update((current) => {
    const fixtures = current.fixtures || [];
    const index = fixtures.findIndex((f) => f.id === fixture.id);

    let newFixtures;
    if (index >= 0) {
      newFixtures = fixtures.filter((f) => f.id !== fixture.id);
    } else {
      newFixtures = [
        ...fixtures,
        {
          id: fixture.id,
          home: fixture.home,
          away: fixture.away,
          date: fixture.date,
        },
      ];
    }

    const updated = { ...current, fixtures: newFixtures };
    saveFavorites(updated);
    return updated;
  });
}

export function isTeamFavorite(teamId, favs) {
  return favs.teams?.some((t) => t.id === teamId) || false;
}

export function isFixtureFavorite(fixtureId, favs) {
  return favs.fixtures?.some((f) => f.id === fixtureId) || false;
}
