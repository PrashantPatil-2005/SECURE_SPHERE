import { useState, useCallback, useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import Login from '@/pages/Login';
import AuthenticatedApp from '@/components/shell/AuthenticatedApp';
import { hydrateDocumentThemeFromStorage } from '@/lib/themeDom';

export default function App() {
  const [authed, setAuthed] = useState(() =>
    !!(localStorage.getItem('securisphere_token') || sessionStorage.getItem('securisphere_token'))
  );
  const handleLogin = useCallback(() => setAuthed(true), []);

  /** Login / logged-out: apply saved theme to `<html>` (Zustand may not be mounted). */
  useEffect(() => {
    if (!authed) {
      hydrateDocumentThemeFromStorage();
    }
  }, [authed]);

  return (
    <BrowserRouter>
      {!authed ? <Login onLogin={handleLogin} /> : <AuthenticatedApp />}
    </BrowserRouter>
  );
}
