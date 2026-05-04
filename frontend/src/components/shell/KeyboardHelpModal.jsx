import { useEffect, useState } from 'react';
import { Keyboard } from 'lucide-react';
import { Modal } from '@/components/ui/Modal';

const SECTIONS = [
  {
    title: 'Global',
    items: [
      { keys: ['⌘', 'K'], label: 'Open command palette' },
      { keys: ['?'], label: 'This shortcut cheatsheet' },
      { keys: ['Esc'], label: 'Close palette / drawer / modal' },
    ],
  },
  {
    title: 'Navigation',
    items: [
      { keys: ['1'], label: 'Go to Dashboard' },
    ],
  },
  {
    title: 'Preferences',
    items: [
      { keys: ['T'], label: 'Toggle tweaks panel' },
      { keys: ['D'], label: 'Toggle density (comfy ⇄ compact)' },
      { keys: ['A'], label: 'Toggle annotations' },
    ],
  },
  {
    title: 'Palette (when open)',
    items: [
      { keys: ['↑', '↓'], label: 'Navigate results' },
      { keys: ['Enter'], label: 'Run highlighted command' },
    ],
  },
];

function isTypingTarget(el) {
  if (!el || !(el instanceof Element)) return false;
  const tag = el.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (el.getAttribute('contenteditable') === 'true') return true;
  return false;
}

export default function KeyboardHelpModal() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onKey = (e) => {
      if (e.defaultPrevented) return;
      if (isTypingTarget(e.target)) return;
      if (e.key === '?' || (e.shiftKey && e.key === '/')) {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <Modal
      open={open}
      onClose={() => setOpen(false)}
      title="Keyboard shortcuts"
      description="Press ? anytime to toggle this view."
      size="md"
    >
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        {SECTIONS.map((s) => (
          <div key={s.title}>
            <div className="mb-2 flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-base-500">
              <Keyboard className="h-3 w-3" />
              {s.title}
            </div>
            <ul className="space-y-1.5">
              {s.items.map((it, i) => (
                <li key={i} className="flex items-center justify-between gap-3">
                  <span className="text-[12px] text-base-300">{it.label}</span>
                  <span className="flex shrink-0 items-center gap-1">
                    {it.keys.map((k, j) => (
                      <kbd
                        key={j}
                        className="inline-flex h-5 min-w-5 items-center justify-center rounded border border-base-700 bg-base-800/80 px-1.5 font-mono text-[10px] font-semibold text-base-200"
                      >
                        {k}
                      </kbd>
                    ))}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </Modal>
  );
}
