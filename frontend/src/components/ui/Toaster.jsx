import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { CheckCircle2, AlertTriangle, XCircle, Info, X } from 'lucide-react';
import { cn } from '@/lib/utils';

const ToastContext = createContext(null);

const VARIANT = {
  success: { Icon: CheckCircle2, ring: 'border-emerald-500/40', text: 'text-emerald-300', iconColor: 'text-emerald-400' },
  error:   { Icon: XCircle,      ring: 'border-red-500/40',     text: 'text-red-200',     iconColor: 'text-red-400' },
  warning: { Icon: AlertTriangle,ring: 'border-amber-500/40',   text: 'text-amber-200',   iconColor: 'text-amber-400' },
  info:    { Icon: Info,         ring: 'border-cyan-500/40',    text: 'text-cyan-200',    iconColor: 'text-cyan-400' },
};

const DEFAULT_DURATION = 4000;
const MAX_VISIBLE = 4;

let _idCounter = 0;
const nextId = () => `t-${Date.now()}-${++_idCounter}`;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timersRef = useRef(new Map());

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const push = useCallback((toast) => {
    const id = toast.id || nextId();
    const duration = toast.duration ?? DEFAULT_DURATION;
    setToasts((prev) => [...prev, { ...toast, id, variant: toast.variant || 'info' }].slice(-MAX_VISIBLE * 2));
    if (duration > 0) {
      const timer = setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
        timersRef.current.delete(id);
      }, duration);
      timersRef.current.set(id, timer);
    }
    return id;
  }, []);

  const api = {
    push,
    dismiss,
    success: (title, opts = {}) => push({ ...opts, title, variant: 'success' }),
    error:   (title, opts = {}) => push({ ...opts, title, variant: 'error' }),
    warning: (title, opts = {}) => push({ ...opts, title, variant: 'warning' }),
    info:    (title, opts = {}) => push({ ...opts, title, variant: 'info' }),
  };

  useEffect(() => () => {
    for (const t of timersRef.current.values()) clearTimeout(t);
    timersRef.current.clear();
  }, []);

  const visible = toasts.slice(-MAX_VISIBLE);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div
        role="region"
        aria-label="Toast notifications"
        aria-live="polite"
        aria-relevant="additions"
        className="pointer-events-none fixed bottom-4 right-4 z-[1700] flex w-[340px] flex-col gap-2"
      >
        <AnimatePresence initial={false}>
          {visible.map((t) => {
            const v = VARIANT[t.variant] || VARIANT.info;
            const Icon = v.Icon;
            return (
              <motion.div
                key={t.id}
                layout
                initial={{ opacity: 0, x: 60, scale: 0.96 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 60, scale: 0.96 }}
                transition={{ duration: 0.22, ease: 'easeOut' }}
                className={cn(
                  'pointer-events-auto rounded-lg border bg-base-900/95 backdrop-blur px-3 py-2.5 shadow-xl',
                  v.ring
                )}
              >
                <div className="flex items-start gap-2">
                  <Icon className={cn('mt-0.5 h-4 w-4 shrink-0', v.iconColor)} />
                  <div className="min-w-0 flex-1">
                    <div className={cn('text-xs font-semibold', v.text)}>{t.title}</div>
                    {t.description && (
                      <div className="mt-0.5 text-[11px] text-base-400 break-words">{t.description}</div>
                    )}
                    {t.action && (
                      <button
                        onClick={() => { t.action.onClick?.(); api.dismiss(t.id); }}
                        className="mt-1.5 text-[11px] font-semibold text-accent hover:text-accent-hover transition-colors"
                      >
                        {t.action.label}
                      </button>
                    )}
                  </div>
                  <button
                    onClick={() => api.dismiss(t.id)}
                    className="-mr-0.5 -mt-0.5 rounded p-0.5 text-base-500 hover:bg-white/5 hover:text-base-300 transition-colors"
                    aria-label="Dismiss"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
  return ctx;
}
