import { useState, useCallback, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Login from '@/pages/Login';
import Attacker from '@/pages/Attacker';
import AuthenticatedApp from '@/components/shell/AuthenticatedApp';
import { hydrateDocumentThemeFromStorage } from '@/lib/themeDom';

function Shell() {
  const [authed, setAuthed] = useState(() =>
    !!(localStorage.getItem('securisphere_token') || sessionStorage.getItem('securisphere_token'))
  );
  const handleLogin = useCallback(() => setAuthed(true), []);

  useEffect(() => {
    if (!authed) hydrateDocumentThemeFromStorage();
  }, [authed]);

  return !authed ? <Login onLogin={handleLogin} /> : <AuthenticatedApp />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/attacker" element={<Attacker />} />
        <Route path="*" element={<Shell />} />
      </Routes>
    </BrowserRouter>
  );
}
