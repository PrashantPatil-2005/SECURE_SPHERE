import { useState, useCallback, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Login from '@/pages/Login';
import Signup from '@/pages/Signup';
import Attacker from '@/pages/Attacker';
import AuthenticatedApp from '@/components/shell/AuthenticatedApp';
import ErrorBoundary from '@/components/shell/ErrorBoundary';
import { ToastProvider } from '@/components/ui/Toaster';
import { hydrateDocumentThemeFromStorage } from '@/lib/themeDom';

function hasToken() {
  return !!(localStorage.getItem('securisphere_token') || sessionStorage.getItem('securisphere_token'));
}

function Shell() {
  const [authed, setAuthed] = useState(hasToken);
  const handleAuth = useCallback(() => setAuthed(true), []);
  const location = useLocation();

  useEffect(() => {
    if (!authed) hydrateDocumentThemeFromStorage();
  }, [authed]);

  if (authed) return <AuthenticatedApp onLogout={() => setAuthed(false)} />;

  if (location.pathname === '/signup') return <Signup onSignup={handleAuth} />;
  if (location.pathname === '/login' || location.pathname === '/') return <Login onLogin={handleAuth} />;
  return <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/attacker" element={<Attacker />} />
            <Route path="*" element={<Shell />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </ErrorBoundary>
  );
}
