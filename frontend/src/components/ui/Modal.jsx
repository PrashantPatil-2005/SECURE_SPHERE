import { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

const SIZE = {
  sm: 'max-w-[400px]',
  md: 'max-w-[520px]',
  lg: 'max-w-[720px]',
  xl: 'max-w-[960px]',
};

export function Modal({
  open,
  onClose,
  title,
  description,
  size = 'md',
  showClose = true,
  closeOnBackdrop = true,
  closeOnEsc = true,
  className,
  children,
  footer,
}) {
  const panelRef = useRef(null);
  const lastFocusedRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    lastFocusedRef.current = document.activeElement;
    const t = setTimeout(() => panelRef.current?.focus(), 30);
    document.body.style.overflow = 'hidden';
    return () => {
      clearTimeout(t);
      document.body.style.overflow = '';
      if (lastFocusedRef.current instanceof HTMLElement) {
        try { lastFocusedRef.current.focus(); } catch { /* ignore */ }
      }
    };
  }, [open]);

  useEffect(() => {
    if (!open || !closeOnEsc) return;
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, closeOnEsc, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          className="fixed inset-0 z-[1500] flex items-center justify-center bg-black/55 backdrop-blur-sm px-4"
          onClick={() => closeOnBackdrop && onClose?.()}
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? 'modal-title' : undefined}
          aria-describedby={description ? 'modal-desc' : undefined}
        >
          <motion.div
            ref={panelRef}
            tabIndex={-1}
            initial={{ scale: 0.92, opacity: 0, y: 8 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.34, 1.4, 0.64, 1] }}
            onClick={(e) => e.stopPropagation()}
            className={cn(
              'relative w-full rounded-2xl border border-base-800 bg-base-900 shadow-2xl outline-none',
              SIZE[size] || SIZE.md,
              className
            )}
          >
            {(title || showClose) && (
              <div className="flex items-start justify-between gap-3 border-b border-base-800 px-5 py-3">
                <div className="min-w-0">
                  {title && <h2 id="modal-title" className="text-sm font-semibold text-base-100">{title}</h2>}
                  {description && <p id="modal-desc" className="mt-0.5 text-xs text-base-500">{description}</p>}
                </div>
                {showClose && (
                  <button
                    onClick={() => onClose?.()}
                    className="-mr-1 -mt-0.5 rounded-md p-1 text-base-500 hover:bg-white/5 hover:text-base-200 transition-colors"
                    aria-label="Close"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            )}

            <div className="px-5 py-4">{children}</div>

            {footer && (
              <div className="flex items-center justify-end gap-2 border-t border-base-800 px-5 py-3">
                {footer}
              </div>
            )}
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export function ConfirmModal({ open, onClose, onConfirm, title, message, confirmLabel = 'Confirm', cancelLabel = 'Cancel', danger = false }) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={title}
      size="sm"
      footer={
        <>
          <button
            onClick={onClose}
            className="h-8 rounded-lg border border-base-800 bg-base-950/40 px-3 text-xs text-base-300 hover:bg-base-800 transition-colors"
          >
            {cancelLabel}
          </button>
          <button
            onClick={() => { onConfirm?.(); onClose?.(); }}
            className={cn(
              'h-8 rounded-lg px-3 text-xs font-semibold transition-colors',
              danger
                ? 'border border-red-500/40 bg-red-500/15 text-red-200 hover:bg-red-500/25'
                : 'bg-accent text-base-950 hover:bg-accent-hover'
            )}
          >
            {confirmLabel}
          </button>
        </>
      }
    >
      <p className="text-sm text-base-300">{message}</p>
    </Modal>
  );
}
