import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { navItemsForRole } from '@/components/nav/navConfig';
import { useAuth } from '@/contexts/AuthProvider';

/**
 * @param {object} opts
 * @param {(tabId: string) => void} opts.onNavigate
 * @param {Array<{id:string,section:string,label:string,detail?:string,keywords?:string,run:Function}>} [opts.extraCommands]
 */
export function useCommandPalette({ onNavigate, extraCommands = [] }) {
  const { role } = useAuth();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [highlight, setHighlight] = useState(0);
  const inputRef = useRef(null);

  const commands = useMemo(() => {
    const navigate = (id) => {
      onNavigate(id);
      setOpen(false);
      setQuery('');
      setHighlight(0);
    };

    const navCmds = navItemsForRole(role).map((item) => ({
      id: `go-${item.id}`,
      section: 'Navigate',
      label: `Go to ${item.label}`,
      detail: item.path,
      keywords: `${item.label} ${item.path} go tab`.toLowerCase(),
      run: () => navigate(item.id),
    }));

    // App-specific commands (filters, real actions like WAF block) are supplied
    // by the caller via extraCommands so the hook stays free of business logic.
    const wrapped = (extraCommands || []).map((c) => ({
      ...c,
      run: () => {
        try { c.run?.(); } finally {
          setOpen(false);
          setQuery('');
          setHighlight(0);
        }
      },
    }));

    return [...navCmds, ...wrapped];
  }, [onNavigate, extraCommands, role]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter(
      (c) =>
        c.label.toLowerCase().includes(q) ||
        (c.detail && c.detail.toLowerCase().includes(q)) ||
        (c.keywords && c.keywords.includes(q))
    );
  }, [commands, query]);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    if (open) {
      setHighlight(0);
      const t = requestAnimationFrame(() => inputRef.current?.focus());
      return () => cancelAnimationFrame(t);
    }
    setQuery('');
    setHighlight(0);
  }, [open]);

  useEffect(() => {
    setHighlight(0);
  }, [query]);

  useEffect(() => {
    setHighlight((h) => (filtered.length ? Math.min(h, filtered.length - 1) : 0));
  }, [filtered.length]);

  const runIndex = useCallback(
    (i) => {
      const cmd = filtered[i];
      if (cmd) cmd.run();
    },
    [filtered]
  );

  const onKeyDown = useCallback(
    (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        setOpen(false);
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setHighlight((h) => (filtered.length ? (h + 1) % filtered.length : 0));
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setHighlight((h) =>
          filtered.length ? (h - 1 + filtered.length) % filtered.length : 0
        );
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        runIndex(highlight);
      }
    },
    [filtered.length, highlight, runIndex]
  );

  return {
    open,
    setOpen,
    query,
    setQuery,
    highlight,
    setHighlight,
    filtered,
    inputRef,
    onKeyDown,
    runIndex,
  };
}
