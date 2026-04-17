import { useState } from 'react';
import { Check, AlertOctagon, VolumeX, Loader2, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import { cn } from '@/lib/utils';

const ACTIONS = [
  {
    key: 'acknowledged',
    label: 'Acknowledge',
    icon: Check,
    help: 'Mark as seen — under investigation.',
    tone: 'text-accent hover:text-accent-hover border-accent/25 hover:bg-accent/[0.06]',
  },
  {
    key: 'escalated',
    label: 'Escalate',
    icon: AlertOctagon,
    help: 'Escalate to oncall / senior analyst.',
    tone: 'text-red-300 hover:text-red-200 border-red-500/30 hover:bg-red-500/10',
  },
  {
    key: 'suppressed',
    label: 'Suppress',
    icon: VolumeX,
    help: 'False positive — suppress IP for 30 min.',
    tone: 'text-base-300 hover:text-base-100 border-white/10 hover:bg-white/[0.06]',
  },
];

export default function IncidentActions({ incidentId, currentStatus, onChange }) {
  const [selected, setSelected] = useState(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async () => {
    if (!selected) return;
    setBusy(true);
    setError('');
    try {
      const res = await api.updateIncidentStatus(incidentId, selected, note.trim());
      if (res?.status === 'success') {
        onChange?.(selected, note.trim());
        setSelected(null);
        setNote('');
      } else {
        setError(res?.message || 'Update failed');
      }
    } catch (e) {
      setError('Network error');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-1.5 flex-wrap">
        {ACTIONS.map(a => {
          const Icon = a.icon;
          const active = currentStatus === a.key;
          const chosen = selected === a.key;
          return (
            <button
              key={a.key}
              type="button"
              onClick={() => setSelected(chosen ? null : a.key)}
              disabled={busy}
              title={a.help}
              className={cn(
                'inline-flex items-center gap-1.5 h-7 px-2.5 rounded-md text-[11px] font-medium border transition-colors',
                a.tone,
                chosen && 'ring-2 ring-accent/40',
                active && 'bg-white/[0.04]',
              )}
            >
              <Icon className="w-3 h-3" />
              {a.label}
              {active && <span className="text-[9px] opacity-70">• current</span>}
            </button>
          );
        })}
      </div>

      {selected && (
        <div className="flex flex-col gap-2 p-2.5 rounded-lg bg-base-900/60 border border-white/[0.06]">
          <textarea
            value={note}
            onChange={e => setNote(e.target.value)}
            placeholder={`Optional note for ${selected}…`}
            rows={2}
            className="w-full text-[11px] text-base-200 bg-base-950 border border-white/[0.06] rounded-md px-2 py-1.5 outline-none focus:border-accent/50 resize-none"
          />
          <div className="flex items-center gap-2">
            <Button
              variant="primary"
              size="sm"
              onClick={submit}
              disabled={busy}
            >
              {busy ? <Loader2 className="w-3 h-3 animate-spin" /> : <Check className="w-3 h-3" />}
              Confirm {selected}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { setSelected(null); setNote(''); setError(''); }}
              disabled={busy}
            >
              <X className="w-3 h-3" /> Cancel
            </Button>
            {error && <span className="text-[11px] text-red-400">{error}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
