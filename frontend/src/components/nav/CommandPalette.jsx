import { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { cn } from '@/lib/utils';
import { Terminal } from 'lucide-react';

/**
 * Modal command surface — navigation, filters, actions (⌘K / Ctrl+K).
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
  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => {
      if (e.target.closest('[data-command-palette]')) return;
      onClose();
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open, onClose]);

  if (!open) return null;

  const body = (
    <div
      className="fixed inset-0 z-[200] flex items-start justify-center bg-black/50 px-3 pt-[12vh] backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-label="Command palette"
    >
      <div
        data-command-palette
        className={cn(
          'w-full max-w-lg overflow-hidden rounded-lg border border-white/[0.08] bg-base-900 shadow-[0_24px_80px_-20px_rgba(0,0,0,0.65)]'
        )}
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b border-dashed border-white/[0.08] px-3 py-2">
          <Terminal className="h-4 w-4 shrink-0 text-accent/80" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => onQueryChange(e.target.value)}
            onKeyDown={onInputKeyDown}
            placeholder="Go, filter, or act…"
            className="min-w-0 flex-1 bg-transparent font-mono text-sm text-base-100 outline-none placeholder:text-base-600"
            autoComplete="off"
            spellCheck={false}
          />
          <kbd className="hidden shrink-0 rounded border border-white/[0.08] bg-base-950 px-1.5 py-0.5 font-mono text-[10px] text-base-500 sm:inline">
            esc
          </kbd>
        </div>

        <div className="max-h-[min(50vh,320px)] overflow-y-auto py-2">
          {filtered.length === 0 ? (
            <div className="px-4 py-6 text-center font-mono text-xs text-base-500">No matches</div>
          ) : (
            filtered.map((cmd, idx) => {
              const showHeading =
                idx === 0 || filtered[idx - 1].section !== cmd.section;
              const active = idx === highlight;
              return (
                <div key={cmd.id}>
                  {showHeading && (
                    <div className="px-3 py-1 font-mono text-[10px] font-medium uppercase tracking-wider text-base-600">
                      {cmd.section}
                    </div>
                  )}
                  <button
                    type="button"
                    onMouseEnter={() => onHighlightChange(idx)}
                    onClick={() => runIndex(idx)}
                    className={cn(
                      'flex w-full flex-col items-start gap-0.5 px-3 py-2 text-left transition-colors',
                      active ? 'bg-accent/[0.12]' : 'hover:bg-white/[0.03]'
                    )}
                  >
                    <span className="text-[12px] text-base-200">{cmd.label}</span>
                    {cmd.detail && (
                      <span className="font-mono text-[10px] text-base-500">{cmd.detail}</span>
                    )}
                  </button>
                </div>
              );
            })
          )}
        </div>

        <div className="border-t border-dashed border-white/[0.06] px-3 py-1.5 font-mono text-[10px] text-base-600">
          ↑↓ navigate · ↵ run · ⌘K toggle
        </div>
      </div>
    </div>
  );

  return createPortal(body, document.body);
}
