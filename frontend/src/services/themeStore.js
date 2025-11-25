import { writable } from "svelte/store";

const STORAGE_KEY = "fixturecast_theme";
const DEFAULT_THEME = "dark";

function getInitialTheme() {
  if (typeof localStorage !== "undefined") {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored || DEFAULT_THEME;
  }
  return DEFAULT_THEME;
}

export const theme = writable(getInitialTheme());

export function toggleTheme() {
  theme.update((current) => {
    const newTheme = current === "dark" ? "light" : "dark";
    if (typeof localStorage !== "undefined") {
      localStorage.setItem(STORAGE_KEY, newTheme);
    }
    if (typeof document !== "undefined") {
      document.documentElement.setAttribute("data-theme", newTheme);
    }
    return newTheme;
  });
}

export function initTheme() {
  const currentTheme = getInitialTheme();
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", currentTheme);
  }
}
