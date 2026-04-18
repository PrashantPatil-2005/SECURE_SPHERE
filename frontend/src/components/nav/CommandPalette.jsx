import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { Search } from 'lucide-react';
import { cn } from '@/lib/utils';

/**
 * @param {{
 *   open: boolean;
 *   onClose: () => void;
 *   query: string;
 *   onQueryChange: (q: string) => void;
 *   filtered: Array<{ id: string; section: string; label: string; detail?: string }>;
 *   highlight: number;
 *   onHighlightChange: (n: number) => void;
 *   inputRef: React.RefObject<HTMLInputElement | null>;
 *   onInputKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
 *   runIndex: (i: number) => void;
 * }} props
 */
export default function CommandPalette({
  open,
  onClose,
  query,
  onQueryChange,
  filtered,
  highlight,
  onHighlightChange,
  inputRef,
  onInputKeyDown,
  runIndex,
}) {
  const backdropRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => {
      if (e.target === backdropRef.current) onClose();
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open, onClose]);

  if (!open) return null;

  const body = (
    <div className="fixed inset-0 z-[200] flex items-start justify-center pt-[12vh] px-4">
      <div
        ref={backdropRef}
        className="absolute inset-0 bg-base-950/70 backdrop-blur-[2px] transition-colors duration-200"
        aria-hidden
      />
      <div
        role="dialog"
        aria-modal
        aria-label="Command palette"
        className="relative z-[1] w-full max-w-lg overflow-hidden rounded-lg border border-base-800 bg-base-950 shadow-2xl transition-colors duration-200"
      >
        <div className="flex items-center gap-2 border-b border-base-800 px-3 py-2">
          <Search className="h-4 w-4 shrink-0 text-base-600" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={onInputKeyDown}
            placeholder="Search commands…"
            className="min-w-0 flex-1 bg-transparent font-mono text-sm text-base-200 outline-none placeholder:text-base-600"
            autoComplete="off"
            spellCheck={false}
          />
          <kbd className="hidden shrink-0 rounded border border-base-800 px-1.5 py-0.5 font-mono text-[10px] text-base-500 sm:inline">
            esc
          </kbd>
        </div>

        <ul className="max-h-[min(50vh,360px)] overflow-y-auto p-1">
          {filtered.length === 0 ? (
            <li className="px-3 py-6 text-center font-mono text-xs text-base-600">No matches</li>
          ) : (
            filtered.map((cmd, i) => (
              <li key={cmd.id}>
                <button
                  type="button"
                  onMouseEnter={() => onHighlightChange(i)}
                  onClick={() => runIndex(i)}
                  className={cn(
                    'flex w-full flex-col items-start gap-0.5 rounded-md px-2 py-2 text-left transition-colors',
                    i === highlight ? 'bg-accent/15 text-base-100' : 'text-base-400 hover:bg-base-900/80'
                  )}
                >
                  <span className="font-mono text-[10px] uppercase tracking-wider text-base-600">{cmd.section}</span>
                  <span className="font-mono text-sm">{cmd.label}</span>
                  {cmd.detail && (
                    <span className="truncate font-mono text-[11px] text-base-600">{cmd.detail}</span>
                  )}
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );

  return createPortal(body, document.body);
}
