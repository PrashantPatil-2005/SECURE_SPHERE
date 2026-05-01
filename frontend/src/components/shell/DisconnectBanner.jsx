import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { WifiOff, RefreshCw } from 'lucide-react';

const VISIBLE_AFTER_MS = 8000;

export default function DisconnectBanner({ connected, onReconnect }) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    if (connected) {
      setShow(false);
      return undefined;
    }
    const id = setTimeout(() => setShow(true), VISIBLE_AFTER_MS);
    return () => clearTimeout(id);
  }, [connected]);

  return (
    <AnimatePresence>
      {show && !connected && (
        <motion.div
          role="status"
          aria-live="polite"
          initial={{ y: -40, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -40, opacity: 0 }}
          transition={{ duration: 0.22, ease: 'easeOut' }}
          className="pointer-events-auto fixed left-1/2 top-3 z-[1600] -translate-x-1/2 transform"
        >
          <div className="flex items-center gap-2 rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1.5 shadow-lg backdrop-blur-md">
            <WifiOff className="h-3.5 w-3.5 text-amber-300" />
            <span className="text-[11px] font-medium text-amber-200">
              Live feed disconnected — falling back to polling
            </span>
            {onReconnect && (
              <button
                type="button"
                onClick={onReconnect}
                className="ml-1 inline-flex items-center gap-1 rounded-full bg-amber-500/20 px-2 py-0.5 text-[10px] font-semibold text-amber-100 hover:bg-amber-500/30"
              >
                <RefreshCw className="h-3 w-3" /> Retry
              </button>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
