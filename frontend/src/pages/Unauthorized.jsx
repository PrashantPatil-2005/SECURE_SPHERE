import { Link } from 'react-router-dom';
import { ShieldOff, ArrowLeft } from 'lucide-react';
import { useAuth } from '@/contexts/AuthProvider';

export default function Unauthorized() {
  const { role } = useAuth();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-base-950 px-6 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl border border-base-800 bg-base-900">
        <ShieldOff className="h-7 w-7 text-base-400" />
      </div>
      <h1 className="text-xl font-semibold text-base-100">Access denied</h1>
      <p className="mt-2 max-w-md text-sm text-base-500">
        Your role
        {' '}
        <span className="font-mono text-base-300">{role || 'unknown'}</span>
        {' '}
        does not have permission to view this page.
      </p>
      <div className="mt-6 flex gap-3">
        <Link
          to="/dashboard"
          className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-base-800 px-3 text-xs text-base-300 hover:text-base-100"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Dashboard
        </Link>
      </div>
    </div>
  );
}
