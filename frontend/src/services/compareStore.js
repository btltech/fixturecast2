// Compare Store Service
// Manages fixtures selected for comparison
import { writable } from "svelte/store";

// Create the store
function createCompareStore() {
  const { subscribe, set, update } = writable({
    fixtures: [], // Array of fixture IDs (max 2)
    fixtureLeagues: {}, // Map fixtureId -> leagueId
    isOpen: false,
  });

  return {
    subscribe,

    // Add a fixture to compare (max 2)
    addFixture: (fixtureId, leagueId) => {
      update((state) => {
        const fixtureLeagues = { ...state.fixtureLeagues };
        if (leagueId) {
          fixtureLeagues[fixtureId] = leagueId;
        }

        if (state.fixtures.includes(fixtureId)) {
          // Already in compare, remove it
          const fixtures = state.fixtures.filter((id) => id !== fixtureId);
          delete fixtureLeagues[fixtureId];
          return {
            ...state,
            fixtures,
            fixtureLeagues,
          };
        }
        if (state.fixtures.length >= 2) {
          // Replace the first one
          const fixtures = [state.fixtures[1], fixtureId];
          delete fixtureLeagues[state.fixtures[0]];
          return {
            ...state,
            fixtures,
            fixtureLeagues,
          };
        }
        const fixtures = [...state.fixtures, fixtureId];
        return {
          ...state,
          fixtures,
          fixtureLeagues,
        };
      });
    },

    // Remove a fixture from compare
    removeFixture: (fixtureId) => {
      update((state) => {
        const fixtures = state.fixtures.filter((id) => id !== fixtureId);
        const fixtureLeagues = { ...state.fixtureLeagues };
        delete fixtureLeagues[fixtureId];
        return {
          ...state,
          fixtures,
          fixtureLeagues,
          isOpen: fixtures.length > 0 ? state.isOpen : false,
        };
      });
    },

    // Check if fixture is in compare list
    isInCompare: (fixtureId, fixtures) => {
      return fixtures.includes(fixtureId);
    },

    // Toggle compare panel
    togglePanel: () => {
      update((state) => ({
        ...state,
        isOpen: !state.isOpen,
      }));
    },

    // Open compare panel
    openPanel: () => {
      update((state) => ({
        ...state,
        isOpen: true,
      }));
    },

    // Close and clear
    close: () => {
      set({ fixtures: [], fixtureLeagues: {}, isOpen: false });
    },

    // Clear fixtures
    clear: () => {
      update((state) => ({
        ...state,
        fixtures: [],
        fixtureLeagues: {},
      }));
    },
  };
}

export const compareStore = createCompareStore();
