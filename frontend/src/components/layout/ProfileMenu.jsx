import { useEffect, useRef, useState } from 'react';
import { User, Settings, LogOut, Server } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function ProfileMenu({ initial = 'A', label = 'Profile', onNavigate, onLogout }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onEsc = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onEsc);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onEsc);
    };
  }, [open]);

  const go = (path) => {
    setOpen(false);
    onNavigate?.(path);
  };

  const items = [
    { icon: User, label: 'Profile', path: '/settings?tab=profile' },
    { icon: Settings, label: 'Settings', path: '/settings' },
    { icon: Server, label: 'System status', path: '/system' },
  ];

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        title={label}
        aria-label={`${label} menu`}
        aria-haspopup="menu"
        aria-expanded={open}
        className={cn(
          'ml-1 flex h-7 w-7 cursor-pointer items-center justify-center rounded-md',
          'bg-gradient-to-br from-accent to-base-700 text-xs font-bold text-white',
          'ring-offset-2 ring-offset-base-900 hover:ring-2 hover:ring-accent/30',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/60',
          open && 'ring-2 ring-accent/50'
        )}
      >
        <span aria-hidden="true">{initial}</span>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-9 z-50 w-52 origin-top-right animate-scale-in rounded-lg border border-base-800 bg-base-900/95 py-1 shadow-2xl backdrop-blur-xl"
        >
          <div className="border-b border-dashed border-base-800 px-3 py-2">
            <div className="text-xs font-semibold text-base-200">{label}</div>
            <div className="type-eyebrow mt-0.5 font-mono">SecuriSphere SOC</div>
          </div>

          <div className="py-1">
            {items.map((it) => {
              const Icon = it.icon;
              return (
                <button
                  key={it.path}
                  type="button"
                  role="menuitem"
                  onClick={() => go(it.path)}
                  className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-base-300 hover:bg-base-800/60 hover:text-base-100"
                >
                  <Icon className="h-3.5 w-3.5 text-base-500" />
                  {it.label}
                </button>
              );
            })}
          </div>

          {onLogout && (
            <div className="border-t border-dashed border-base-800 py-1">
              <button
                type="button"
                role="menuitem"
                onClick={() => { setOpen(false); onLogout(); }}
                className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-red-300 hover:bg-red-500/10 hover:text-red-200"
              >
                <LogOut className="h-3.5 w-3.5" />
                Sign out
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
