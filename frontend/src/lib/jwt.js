function base64UrlDecode(str) {
  const pad = str.length % 4 === 0 ? '' : '='.repeat(4 - (str.length % 4));
  const b64 = (str + pad).replace(/-/g, '+').replace(/_/g, '/');
  try {
    return atob(b64);
  } catch {
    return '';
  }
}

export function decodeJwt(token) {
  if (!token || typeof token !== 'string') return null;
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  try {
    const json = base64UrlDecode(parts[1]);
    if (!json) return null;
    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function getTokenStorage() {
  try {
    if (localStorage.getItem('securisphere_token')) return localStorage;
    if (sessionStorage.getItem('securisphere_token')) return sessionStorage;
  } catch {
    /* ignore */
  }
  return null;
}

export function readToken() {
  try {
    return (
      localStorage.getItem('securisphere_token') ||
      sessionStorage.getItem('securisphere_token') ||
      ''
    );
  } catch {
    return '';
  }
}

export function writeToken(token) {
  const store = getTokenStorage() || localStorage;
  try {
    store.setItem('securisphere_token', token);
  } catch {
    /* ignore */
  }
}

export function readRefreshToken() {
  try {
    return (
      localStorage.getItem('securisphere_refresh') ||
      sessionStorage.getItem('securisphere_refresh') ||
      ''
    );
  } catch {
    return '';
  }
}

export function writeRefreshToken(token) {
  const store = getTokenStorage() || localStorage;
  try {
    if (token) store.setItem('securisphere_refresh', token);
    else store.removeItem('securisphere_refresh');
  } catch {
    /* ignore */
  }
}

export function clearAuthTokens() {
  try {
    localStorage.removeItem('securisphere_token');
    localStorage.removeItem('securisphere_refresh');
    sessionStorage.removeItem('securisphere_token');
    sessionStorage.removeItem('securisphere_refresh');
  } catch {
    /* ignore */
  }
}

export function persistAuthTokens({ access_token, token, refresh_token }, remember = true) {
  const store = remember ? localStorage : sessionStorage;
  const other = remember ? sessionStorage : localStorage;
  const access = access_token || token;
  try {
    if (access) store.setItem('securisphere_token', access);
    if (refresh_token) store.setItem('securisphere_refresh', refresh_token);
    other.removeItem('securisphere_token');
    other.removeItem('securisphere_refresh');
  } catch {
    /* ignore */
  }
}

export function tokenExpSeconds(token) {
  const payload = decodeJwt(token);
  if (!payload || typeof payload.exp !== 'number') return null;
  return payload.exp;
}
