import { useCallback, useEffect, useState } from 'react';
import { UserPlus, Trash2, Shield } from 'lucide-react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/input';
import { api } from '@/lib/api';
import ProtectedRoute from '@/components/auth/ProtectedRoute';
import { cn } from '@/lib/utils';

const ROLES = ['admin', 'analyst', 'viewer'];

function UserManagementInner() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'viewer' });
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.listUsers();
      setUsers(res?.users || []);
    } catch (e) {
      setError(e.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const createUser = async (e) => {
    e.preventDefault();
    setSaving(true);
    setError('');
    try {
      await api.createUser(form);
      setForm({ username: '', email: '', password: '', role: 'viewer' });
      await load();
    } catch (e) {
      setError(e.message || 'Create failed');
    } finally {
      setSaving(false);
    }
  };

  const updateRole = async (id, role) => {
    try {
      await api.updateUser(id, { role });
      await load();
    } catch (e) {
      setError(e.message || 'Update failed');
    }
  };

  const deactivate = async (id) => {
    if (!window.confirm('Deactivate this user?')) return;
    try {
      await api.deleteUser(id);
      await load();
    } catch (e) {
      setError(e.message || 'Delete failed');
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4">
      <div className="flex items-center gap-3">
        <Shield className="h-5 w-5 text-accent" />
        <div>
          <h1 className="text-lg font-semibold text-base-100">User Management</h1>
          <p className="text-xs text-base-500">Admin-only — create accounts and assign RBAC roles</p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-base-800 bg-base-950/60 px-3 py-2 text-xs text-base-300">{error}</div>
      )}

      <Card>
        <CardHeader><span className="text-sm font-medium text-base-200">Create user</span></CardHeader>
        <CardContent>
          <form onSubmit={createUser} className="grid gap-3 md:grid-cols-2">
            <Input placeholder="Username" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
            <Input type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
            <Input type="password" placeholder="Password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
              className="h-10 rounded-lg border border-base-800 bg-base-900 px-3 text-sm text-base-100"
            >
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
            <div className="md:col-span-2">
              <Button type="submit" variant="primary" size="sm" disabled={saving} className="gap-1.5">
                <UserPlus className="h-3.5 w-3.5" />
                {saving ? 'Creating…' : 'Create user'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><span className="text-sm font-medium text-base-200">Users ({users.length})</span></CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <p className="p-4 text-xs text-base-500">Loading…</p>
          ) : (
            <div className="divide-y divide-base-800">
              {users.map((u) => (
                <div key={u.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <div className="font-mono text-sm text-base-100">{u.username}</div>
                    <div className="text-[11px] text-base-500">{u.email}</div>
                  </div>
                  <Badge variant={u.role === 'admin' ? 'critical' : u.role === 'analyst' ? 'high' : 'low'}>
                    {u.role}
                  </Badge>
                  <select
                    value={u.role}
                    onChange={(e) => updateRole(u.id, e.target.value)}
                    className={cn(
                      'h-8 rounded border border-base-800 bg-base-950 px-2 font-mono text-[11px] text-base-300',
                    )}
                  >
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                  <Button variant="ghost" size="icon" onClick={() => deactivate(u.id)} title="Deactivate">
                    <Trash2 className="h-3.5 w-3.5 text-base-500" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function UserManagement() {
  return (
    <ProtectedRoute roles={['admin']} permission="users.manage">
      <UserManagementInner />
    </ProtectedRoute>
  );
}
