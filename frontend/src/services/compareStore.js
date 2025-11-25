// Compare Store Service
// Manages fixtures selected for comparison
import { writable } from "svelte/store";

// Create the store
function createCompareStore() {
  const { subscribe, set, update } = writable({
    fixtures: [], // Array of fixture IDs (max 2)
    isOpen: false,
  });

  return {
    subscribe,
    
    // Add a fixture to compare (max 2)
    addFixture: (fixtureId) => {
      update(state => {
        if (state.fixtures.includes(fixtureId)) {
          // Already in compare, remove it
          return {
            ...state,
            fixtures: state.fixtures.filter(id => id !== fixtureId),
          };
        }
        if (state.fixtures.length >= 2) {
          // Replace the first one
          return {
            ...state,
            fixtures: [state.fixtures[1], fixtureId],
          };
        }
        return {
          ...state,
          fixtures: [...state.fixtures, fixtureId],
        };
      });
    },

    // Remove a fixture from compare
    removeFixture: (fixtureId) => {
      update(state => ({
        ...state,
        fixtures: state.fixtures.filter(id => id !== fixtureId),
        isOpen: state.fixtures.filter(id => id !== fixtureId).length > 0 ? state.isOpen : false,
      }));
    },

    // Check if fixture is in compare list
    isInCompare: (fixtureId, fixtures) => {
      return fixtures.includes(fixtureId);
    },

    // Toggle compare panel
    togglePanel: () => {
      update(state => ({
        ...state,
        isOpen: !state.isOpen,
      }));
    },

    // Open compare panel
    openPanel: () => {
      update(state => ({
        ...state,
        isOpen: true,
      }));
    },

    // Close and clear
    close: () => {
      set({ fixtures: [], isOpen: false });
    },

    // Clear fixtures
    clear: () => {
      update(state => ({
        ...state,
        fixtures: [],
      }));
    },
  };
}

export const compareStore = createCompareStore();
