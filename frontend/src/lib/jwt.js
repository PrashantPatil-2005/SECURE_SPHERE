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

export function tokenExpSeconds(token) {
  const payload = decodeJwt(token);
  if (!payload || typeof payload.exp !== 'number') return null;
  return payload.exp;
}
