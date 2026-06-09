import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Login from '@/pages/Login';
import Unauthorized from '@/pages/Unauthorized';
import Attacker from '@/pages/Attacker';
import AuthenticatedApp from '@/components/shell/AuthenticatedApp';
import ErrorBoundary from '@/components/shell/ErrorBoundary';
import { ToastProvider } from '@/components/ui/Toaster';
import { AuthProvider, useAuth } from '@/contexts/AuthProvider';
import { hydrateDocumentThemeFromStorage } from '@/lib/themeDom';
import { readToken } from '@/lib/jwt';
import { Spinner } from '@/components/ui/Spinner';
import { useEffect } from 'react';

function Shell() {
  const { isAuthenticated, loading, user } = useAuth();
  const location = useLocation();

  useEffect(() => {
    if (!isAuthenticated) hydrateDocumentThemeFromStorage();
  }, [isAuthenticated]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-base-950">
        <Spinner />
      </div>
    );
  }

  if (user) {
    if (location.pathname === '/login' || location.pathname === '/') {
      return <Navigate to="/dashboard" replace />;
    }
    return <AuthenticatedApp />;
  }

  if (location.pathname === '/unauthorized') return <Unauthorized />;
  if (location.pathname === '/login' || location.pathname === '/' || !readToken()) {
    return <Login />;
  }

  return <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/attacker" element={<Attacker />} />
              <Route path="/unauthorized" element={<Unauthorized />} />
              <Route path="*" element={<Shell />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </ErrorBoundary>
  );
}
