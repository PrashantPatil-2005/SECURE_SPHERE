import { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

const SIDE = {
  right: { initial: { x: '100%' }, animate: { x: 0 }, exit: { x: '100%' }, position: 'right-0 top-0 h-full' },
  left:  { initial: { x: '-100%' }, animate: { x: 0 }, exit: { x: '-100%' }, position: 'left-0 top-0 h-full' },
};

const WIDTH = {
  sm: 'w-full max-w-sm',
  md: 'w-full max-w-md',
  lg: 'w-full max-w-lg',
  xl: 'w-full max-w-2xl',
};

export function Drawer({
  open,
  onClose,
  side = 'right',
  size = 'md',
  title,
  description,
  showClose = true,
  closeOnBackdrop = true,
  closeOnEsc = true,
  className,
  footer,
  children,
}) {
  const cfg = SIDE[side] || SIDE.right;

  useEffect(() => {
    if (!open) return;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = ''; };
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
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="fixed inset-0 z-[1400] bg-black/50 backdrop-blur-[2px]"
            onClick={() => closeOnBackdrop && onClose?.()}
          />
          <motion.aside
            initial={cfg.initial}
            animate={cfg.animate}
            exit={cfg.exit}
            transition={{ duration: 0.24, ease: [0.32, 0.72, 0.16, 1] }}
            className={cn(
              'fixed z-[1450] flex flex-col border-base-800 bg-base-950 shadow-2xl',
              cfg.position,
              side === 'right' ? 'border-l' : 'border-r',
              WIDTH[size] || WIDTH.md,
              className
            )}
            role="dialog"
            aria-modal="true"
            aria-labelledby={title ? 'drawer-title' : undefined}
            aria-describedby={description ? 'drawer-desc' : undefined}
          >
            {(title || showClose) && (
              <div className="flex items-start justify-between gap-3 border-b border-base-800 px-4 py-3">
                <div className="min-w-0">
                  {title && <h2 id="drawer-title" className="text-sm font-semibold text-base-100">{title}</h2>}
                  {description && <p id="drawer-desc" className="mt-0.5 text-xs text-base-500">{description}</p>}
                </div>
                {showClose && (
                  <button
                    onClick={() => onClose?.()}
                    className="-mr-1 rounded-md p-1 text-base-500 hover:bg-white/5 hover:text-base-200 transition-colors"
                    aria-label="Close"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            )}

            <div className="flex-1 overflow-y-auto p-4">{children}</div>

            {footer && (
              <div className="border-t border-base-800 px-4 py-3">{footer}</div>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
