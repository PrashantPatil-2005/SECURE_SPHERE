import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '@/lib/api';
import {
  clearAuthTokens,
  decodeJwt,
  persistAuthTokens,
  readRefreshToken,
  readToken,
  tokenExpSeconds,
  writeToken,
} from '@/lib/jwt';
import { hasPermission, normalizeRole, permissionsForRole } from '@/lib/rbac';

const AuthContext = createContext(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const refreshTimer = useRef(null);

  const applySession = useCallback((data, remember = true) => {
    if (data?.access_token || data?.token) {
      persistAuthTokens(data, remember);
    }
    const u = data?.user;
    if (u) {
      const role = normalizeRole(u.role);
      setUser({
        ...u,
        role,
        permissions: u.permissions || permissionsForRole(role),
      });
    }
  }, []);

  const clearSession = useCallback(() => {
    clearAuthTokens();
    setUser(null);
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
  }, []);

  const refreshSession = useCallback(async () => {
    const rt = readRefreshToken();
    if (!rt) return false;
    try {
      const res = await api.refreshToken(rt);
      if (res?.access_token || res?.token) {
        applySession(res, !!localStorage.getItem('securisphere_refresh'));
        writeToken(res.access_token || res.token);
        return true;
      }
    } catch {
      /* fall through */
    }
    return false;
  }, [applySession]);

  const login = useCallback(async (username, password, remember = false) => {
    const data = await api.login(username, password);
    if (!data?.success && data?.status !== 'success') {
      throw new Error(data?.message || 'Login failed');
    }
    applySession(data, remember);
    return data;
  }, [applySession]);

  const logout = useCallback(async () => {
    try { await api.logout(); } catch { /* ignore */ }
    clearSession();
  }, [clearSession]);

  const bootstrap = useCallback(async () => {
    const token = readToken();
    if (!token) {
      setLoading(false);
      return;
    }
    try {
      const res = await api.me();
      if (res?.user) {
        const role = normalizeRole(res.user.role);
        setUser({
          ...res.user,
          role,
          permissions: res.user.permissions || permissionsForRole(role),
        });
      } else {
        const ok = await refreshSession();
        if (!ok) clearSession();
      }
    } catch {
      const ok = await refreshSession();
      if (!ok) clearSession();
    } finally {
      setLoading(false);
    }
  }, [clearSession, refreshSession]);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  useEffect(() => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    const token = readToken();
    if (!token || !user) return undefined;

    const exp = tokenExpSeconds(token);
    if (!exp) return undefined;

    const msUntilRefresh = Math.max(0, (exp - 120) * 1000 - Date.now());
    refreshTimer.current = setTimeout(() => {
      refreshSession();
    }, msUntilRefresh);

    return () => {
      if (refreshTimer.current) clearTimeout(refreshTimer.current);
    };
  }, [user, refreshSession]);

  const value = useMemo(() => ({
    user,
    role: user?.role ? normalizeRole(user.role) : null,
    permissions: user?.permissions || [],
    loading,
    isAuthenticated: !!user,
    login,
    logout,
    refreshSession,
    clearSession,
    hasPermission: (perm) => hasPermission(user?.role, perm, user?.permissions),
    hasRole: (...roles) => roles.map(normalizeRole).includes(normalizeRole(user?.role)),
  }), [user, loading, login, logout, refreshSession, clearSession]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
