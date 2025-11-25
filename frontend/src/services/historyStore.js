import { writable } from "svelte/store";

const STORAGE_KEY = "fixturecast_prediction_history";
const MAX_HISTORY = 50;

function loadHistory() {
  if (typeof localStorage !== "undefined") {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? JSON.parse(stored) : [];
  }
  return [];
}

function saveHistory(history) {
  if (typeof localStorage !== "undefined") {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  }
}

export const predictionHistory = writable(loadHistory());

export function addToHistory(prediction) {
  predictionHistory.update((current) => {
    const filtered = current.filter((p) => p.fixture_id !== prediction.fixture_id);
    const updated = [
      {
        ...prediction,
        viewed_at: new Date().toISOString(),
      },
      ...filtered,
    ].slice(0, MAX_HISTORY);

    saveHistory(updated);
    return updated;
  });
}

export function clearHistory() {
  predictionHistory.set([]);
  saveHistory([]);
}
