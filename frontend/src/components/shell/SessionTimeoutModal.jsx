import { useEffect, useState } from 'react';
import { Clock, LogOut, RefreshCw } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/button';
import { useSessionTimeout } from '@/hooks/useSessionTimeout';
import { api } from '@/lib/api';
import { writeToken } from '@/lib/jwt';
import { useToast } from '@/components/ui/Toaster';

function fmt(secs) {
  const s = Math.max(0, Math.floor(secs));
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, '0')}`;
}

export default function SessionTimeoutModal({ onLogout }) {
  const { secondsLeft, showWarning, expired, refreshExp } = useSessionTimeout({ warningSeconds: 60 });
  const [refreshing, setRefreshing] = useState(false);
  const toast = useToast();

  useEffect(() => {
    if (expired) onLogout?.();
  }, [expired, onLogout]);

  const handleStay = async () => {
    setRefreshing(true);
    try {
      const res = await api.refreshToken();
      if (res?.token) {
        writeToken(res.token);
        refreshExp();
        toast.success('Session extended');
      } else {
        toast.error(res?.message || 'Could not refresh session');
      }
    } catch {
      toast.error('Could not refresh session');
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <Modal
      open={showWarning}
      onClose={() => { /* sticky — must choose */ }}
      title="Session expiring"
      description="Your session is about to time out."
      size="sm"
      showClose={false}
      closeOnBackdrop={false}
      closeOnEsc={false}
      footer={
        <div className="flex items-center justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onLogout} className="gap-1.5 text-red-300 hover:text-red-200">
            <LogOut className="h-3.5 w-3.5" /> Sign out
          </Button>
          <Button variant="primary" size="sm" onClick={handleStay} disabled={refreshing} className="gap-1.5">
            <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Extending…' : 'Stay signed in'}
          </Button>
        </div>
      }
    >
      <div className="flex items-center gap-3 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
        <Clock className="h-5 w-5 text-amber-300" />
        <div className="min-w-0">
          <div className="text-[12px] text-base-200">
            Token expires in <span className="font-mono font-semibold text-amber-200 tabular-nums">{fmt(secondsLeft || 0)}</span>
          </div>
          <div className="mt-0.5 text-[11px] text-base-500">
            Stay signed in to issue a fresh token, or sign out now.
          </div>
        </div>
      </div>
    </Modal>
  );
}
