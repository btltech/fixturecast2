// Centralized season helper for the app.
// Defaults to VITE_SEASON when provided, otherwise infers based on calendar.
export function getCurrentSeason() {
  const envSeason = Number(import.meta.env.VITE_SEASON);
  if (!Number.isNaN(envSeason) && envSeason > 1900) {
    return envSeason;
  }

  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth(); // 0-based

  // European seasons are labeled by the starting year (e.g., 2025 for 2025/26).
  // Season ticks over in mid-summer: Aug 2025 -> season 2025, Jan 2026 -> still 2025.
  return month >= 6 ? year : year - 1;
}
