import { useState, useEffect, useCallback } from 'react';
import { NAV_SHELL_STORAGE_KEY, VALID_NAV_SHELLS, NAV_SHELL } from '@/components/nav/navConfig';

export function readNavShellInitial() {
  try {
    const v = localStorage.getItem(NAV_SHELL_STORAGE_KEY);
    if (VALID_NAV_SHELLS.includes(v)) return v;
  } catch {
    /* ignore */
  }
  return NAV_SHELL.SIDEBAR;
}

/**
 * Global navigation shell (sidebar / top / minimal).
 * Lifted in App so System settings and layout stay in sync.
 */
export function useNavShell() {
  const [shell, setShell] = useState(readNavShellInitial);

  useEffect(() => {
    try {
      localStorage.setItem(NAV_SHELL_STORAGE_KEY, shell);
    } catch {
      /* ignore */
    }
  }, [shell]);

  const setShellValidated = useCallback((next) => {
    setShell(VALID_NAV_SHELLS.includes(next) ? next : NAV_SHELL.SIDEBAR);
  }, []);

  return { shell, setShell: setShellValidated };
}
