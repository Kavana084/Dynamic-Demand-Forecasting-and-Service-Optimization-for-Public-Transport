/*
  Smart Transit UI Preferences
  - Density: standard | compact | comfortable
  - Stored in localStorage: st.density
  - Applied to: html[data-density="compact"|"comfortable"] (standard removes attribute)
*/

const STORAGE_KEY = 'st.density';

export function normalizeDensity(value) {
  if (value === 'compact' || value === 'comfortable' || value === 'standard') return value;
  return 'standard';
}

export function getDensityPreference() {
  if (typeof window === 'undefined') return 'standard';
  return normalizeDensity(window.localStorage.getItem(STORAGE_KEY));
}

export function applyDensity(pref) {
  if (typeof document === 'undefined') return;
  const p = normalizeDensity(pref);
  if (p === 'standard') {
    delete document.documentElement.dataset.density;
  } else {
    document.documentElement.dataset.density = p;
  }
  document.documentElement.dispatchEvent(new CustomEvent('st:density', { detail: { density: p } }));
}

export function setDensityPreference(pref) {
  if (typeof window === 'undefined') return;
  const p = normalizeDensity(pref);
  window.localStorage.setItem(STORAGE_KEY, p);
  applyDensity(p);
}

export function initPreferences() {
  applyDensity(getDensityPreference());
}

