/*
  Smart Transit theme engine
  - Supports: light | dark | auto (system preference)
  - Persists in localStorage: st.theme
  - Applies resolved theme to: html[data-theme="light"|"dark"]
*/

const STORAGE_KEY = 'st.theme'; // light | dark | auto

export function getSystemTheme() {
  if (typeof window === 'undefined' || !window.matchMedia) return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function normalizeThemePreference(value) {
  if (value === 'light' || value === 'dark' || value === 'auto') return value;
  return 'auto';
}

export function getThemePreference() {
  if (typeof window === 'undefined') return 'auto';
  return normalizeThemePreference(window.localStorage.getItem(STORAGE_KEY));
}

export function resolveTheme(pref) {
  const p = normalizeThemePreference(pref);
  return p === 'auto' ? getSystemTheme() : p;
}

export function applyResolvedTheme(theme) {
  if (typeof document === 'undefined') return;
  document.documentElement.dataset.theme = theme;
  document.documentElement.dispatchEvent(new CustomEvent('st:theme', { detail: { theme } }));
}

export function setThemePreference(pref) {
  if (typeof window === 'undefined') return;
  const normalized = normalizeThemePreference(pref);
  window.localStorage.setItem(STORAGE_KEY, normalized);
  applyResolvedTheme(resolveTheme(normalized));
}

export function initTheme() {
  const pref = getThemePreference();
  applyResolvedTheme(resolveTheme(pref));

  // When auto, live-update on OS theme change
  if (typeof window !== 'undefined' && window.matchMedia) {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      const p = getThemePreference();
      if (p === 'auto') applyResolvedTheme(resolveTheme(p));
    };
    if (mq.addEventListener) mq.addEventListener('change', handler);
    else if (mq.addListener) mq.addListener(handler);
  }
}
