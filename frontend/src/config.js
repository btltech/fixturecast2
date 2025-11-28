// API Configuration
// Uses environment variables if set, otherwise uses production URLs
const isDev =
  typeof window !== "undefined" &&
  (window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1");

export const API_URL = isDev
  ? "http://localhost:8001"
  : import.meta.env.VITE_API_URL ||
    "https://backend-api-production-7b7d.up.railway.app";

export const ML_API_URL = isDev
  ? "http://localhost:8000"
  : import.meta.env.VITE_ML_API_URL ||
    "https://ml-api-production-6cfc.up.railway.app";

// Export aliases for clarity
export const BACKEND_API_URL = API_URL;

// App URL for canonical links and OG tags
export const APP_URL = isDev
  ? "http://localhost:5173"
  : import.meta.env.VITE_APP_URL || "https://fixturecast.app";

export const API_ENDPOINTS = {
  // Backend API (port 8001)
  fixtures: `${API_URL}/api/fixtures`,
  standings: `${API_URL}/api/standings`,
  teams: `${API_URL}/api/teams`,
  team: (id) => `${API_URL}/api/team/${id}`,
  h2h: (homeId, awayId) => `${API_URL}/api/h2h/${homeId}/${awayId}`,
  live: `${API_URL}/api/live`,
  results: `${API_URL}/api/results`,

  // ML API (port 8000)
  prediction: (fixtureId) => `${ML_API_URL}/api/prediction/${fixtureId}`,
  health: `${ML_API_URL}/health`,
  feedback: `${ML_API_URL}/api/feedback`,
  performance: `${ML_API_URL}/api/feedback/performance`,
};
