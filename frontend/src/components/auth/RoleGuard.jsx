import { useAuth } from '@/contexts/AuthProvider';
import { hasPermission, hasRole } from '@/lib/rbac';

/**
 * Conditionally render children based on role or permission.
 * @param {{ children: import('react').ReactNode, roles?: string[], permission?: string, fallback?: import('react').ReactNode }} props
 */
export default function RoleGuard({ children, roles, permission, fallback = null }) {
  const { user } = useAuth();
  if (!user) return fallback;

  if (roles?.length && !hasRole(user.role, roles)) return fallback;
  if (permission && !hasPermission(user.role, permission, user.permissions)) return fallback;

  return children;
}
