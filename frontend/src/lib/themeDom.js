/** Canonical key for theme (per product spec). Also mirrored to `securisphere_theme` for older builds. */
export const THEME_STORAGE_KEY = 'theme';

const STORE_KEY = 'securisphere-app-store';
const LEGACY_THEME_KEY = 'securisphere_theme';

/**
 * @param {'dark' | 'light'} theme
 */
export function applyThemeToDocument(theme) {
  const root = document.documentElement;
  const t = theme === 'light' ? 'light' : 'dark';
  if (t === 'light') {
    root.classList.remove('dark');
  } else {
    root.classList.add('dark');
  }
  try {
    localStorage.setItem(THEME_STORAGE_KEY, t);
    localStorage.setItem(LEGACY_THEME_KEY, t);
  } catch {
    /* ignore */
  }
}

/**
 * @returns {'dark' | 'light' | null}
 */
export function readPersistedTheme() {
  try {
    const direct = localStorage.getItem(THEME_STORAGE_KEY);
    if (direct === 'dark' || direct === 'light') return direct;

    const raw = localStorage.getItem(STORE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      const t = parsed?.state?.theme ?? parsed?.theme;
      if (t === 'dark' || t === 'light') return t;
    }
    const legacy = localStorage.getItem(LEGACY_THEME_KEY);
    if (legacy === 'dark' || legacy === 'light') return legacy;
  } catch {
    /* ignore */
  }
  return null;
}

export function hydrateDocumentThemeFromStorage() {
  const t = readPersistedTheme();
  applyThemeToDocument(t ?? 'dark');
  return t;
}
