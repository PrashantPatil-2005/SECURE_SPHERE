import { useAppStore } from '@/stores/useAppStore';

/** Theme is owned by `useAppStore` (persisted). Wrapper div applies `dark` for Tailwind. */
export function useTheme() {
  const theme = useAppStore((s) => s.theme);
  const toggle = useAppStore((s) => s.toggleTheme);
  return { theme, toggle };
}
