// API Configuration for FixtureCast
// Automatically uses production URLs when deployed, localhost when developing

const isDev = typeof window !== 'undefined' && 
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

// ML Prediction API (Python FastAPI)
// Update ML_API_URL with your deployed Railway/Render URL
export const ML_API_URL = isDev 
  ? 'http://localhost:8000'
  : (import.meta.env.VITE_ML_API_URL || 'https://fixturecast-ml.onrender.com');

// Backend Data API (Football data)
// Update BACKEND_API_URL with your deployed backend URL
export const BACKEND_API_URL = isDev
  ? 'http://localhost:8001'
  : (import.meta.env.VITE_BACKEND_API_URL || 'https://fixturecast-backend.onrender.com');

// Export a helper to get full API URLs
export const getMLApiUrl = (path) => `${ML_API_URL}${path}`;
export const getBackendApiUrl = (path) => `${BACKEND_API_URL}${path}`;

console.log(`🔧 API Mode: ${isDev ? 'Development' : 'Production'}`);
console.log(`🤖 ML API: ${ML_API_URL}`);
console.log(`📊 Backend API: ${BACKEND_API_URL}`);
