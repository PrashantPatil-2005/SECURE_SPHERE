import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthProvider';
import { readToken } from '@/lib/jwt';
import { Spinner } from '@/components/ui/Spinner';

/**
 * Requires authentication. Optional role / permission gate.
 * @param {{ children: import('react').ReactNode, roles?: string[], permission?: string }} props
 */
export default function ProtectedRoute({ children, roles, permission }) {
  const { user, loading, hasPermission, role } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center">
        <Spinner />
      </div>
    );
  }

  if (!readToken() || !user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (roles?.length && !roles.map((r) => r.toLowerCase()).includes(String(role))) {
    return <Navigate to="/unauthorized" replace />;
  }

  if (permission && !hasPermission(permission)) {
    return <Navigate to="/unauthorized" replace />;
  }

  return children;
}
