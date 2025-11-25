// API Configuration
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001';
export const ML_API_URL = import.meta.env.VITE_ML_API_URL || 'http://localhost:8000';

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
  performance: `${ML_API_URL}/api/feedback/performance`
};
