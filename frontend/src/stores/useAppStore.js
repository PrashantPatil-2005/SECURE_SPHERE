import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { NAV_SHELL, NAV_SHELL_STORAGE_KEY, VALID_NAV_SHELLS } from '@/components/nav/navConfig';
import { applyThemeToDocument } from '@/lib/themeDom';

function sanitizeNav(v) {
  return VALID_NAV_SHELLS.includes(v) ? v : NAV_SHELL.SIDEBAR;
}

export const useAppStore = create(
  persist(
    (set, get) => ({
      theme: 'dark',
      density: 'comfy',
      ann: 'on',
      kc: 'timeline',
      nav: NAV_SHELL.SIDEBAR,
      tweaksOpen: false,

      setTheme: (theme) => {
        const t = theme === 'light' ? 'light' : 'dark';
        set({ theme: t });
        applyThemeToDocument(t);
      },
      toggleTheme: () => {
        const next = get().theme === 'dark' ? 'light' : 'dark';
        get().setTheme(next);
      },

      setDensity: (density) => set({ density: density === 'compact' ? 'compact' : 'comfy' }),
      toggleDensity: () =>
        set((s) => ({ density: s.density === 'compact' ? 'comfy' : 'compact' })),

      setAnn: (ann) => set({ ann: ann === 'on' ? 'on' : 'off' }),
      toggleAnn: () => set((s) => ({ ann: s.ann === 'on' ? 'off' : 'on' })),

      setKc: (kc) => set({ kc: typeof kc === 'string' ? kc : 'timeline' }),

      setNav: (nav) => {
        const n = sanitizeNav(nav);
        set({ nav: n });
        try {
          localStorage.setItem(NAV_SHELL_STORAGE_KEY, n);
        } catch {
          /* ignore */
        }
      },

      setTweaksOpen: (open) => set({ tweaksOpen: !!open }),
      toggleTweaks: () => set((s) => ({ tweaksOpen: !s.tweaksOpen })),
    }),
    {
      name: 'securisphere-app-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (s) => ({
        theme: s.theme,
        density: s.density,
        ann: s.ann,
        kc: s.kc,
        nav: s.nav,
      }),
      /** Persist rehydration uses internal `set` — never calls `setTheme`, so sync `<html>` here. */
      onRehydrateStorage: () => (state, error) => {
        if (!error && state?.theme) {
          applyThemeToDocument(state.theme);
        }
      },
    }
  )
);
