import { useState, useMemo, useEffect, useCallback, useRef } from 'react';
import { NAV_ITEMS } from '@/components/nav/navConfig';

/**
 * @param {object} opts
 * @param {(tabId: string) => void} opts.onNavigate
 * @param {(message: string) => void} [opts.onToast] — optional feedback for filter/action stubs
 */
export function useCommandPalette({ onNavigate, onToast }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [highlight, setHighlight] = useState(0);
  const inputRef = useRef(null);

  const commands = useMemo(() => {
    const toast = (msg) => onToast?.(msg);

    const navigate = (id) => {
      onNavigate(id);
      setOpen(false);
      setQuery('');
      setHighlight(0);
    };

    const navCmds = NAV_ITEMS.map((item) => ({
      id: `go-${item.id}`,
      section: 'Navigate',
      label: `Go to ${item.label}`,
      detail: item.path,
      keywords: `${item.label} ${item.path} go tab`.toLowerCase(),
      run: () => navigate(item.id),
    }));

    const filterCmds = [
      {
        id: 'filter-critical',
        section: 'Filter',
        label: 'Filter · severity:critical',
        detail: 'Opens Events with critical focus (demo)',
        keywords: 'filter severity critical sev',
        run: () => {
          toast('Filter preset: severity:critical — refine in Events filters when available.');
          navigate('events');
        },
      },
      {
        id: 'filter-src',
        section: 'Filter',
        label: 'Filter · src:10.0.2.4',
        detail: 'Example source IP filter',
        keywords: 'filter src ip source 10.0.2.4',
        run: () => {
          toast('Filter preset: src:10.0.2.4');
          navigate('events');
        },
      },
    ];

    const actionCmds = [
      {
        id: 'replay-demo',
        section: 'Actions',
        label: 'Replay · inc_0c1f (demo)',
        detail: 'Jump to topology for replay workflows',
        keywords: 'replay incident kill chain',
        run: () => {
          toast('Opening topology for replay context.');
          navigate('topology');
        },
      },
      {
        id: 'block-ip',
        section: 'Actions',
        label: 'Block IP…',
        detail: 'Queue block workflow (integration stub)',
        keywords: 'block ip ban firewall',
        run: () => {
          const ip = window.prompt('IP address to block (demo stub):', '10.0.2.4');
          if (ip?.trim()) toast(`Action queued: block IP ${ip.trim()} (stub — wire to SOAR/playbooks).`);
          setOpen(false);
          setQuery('');
          setHighlight(0);
        },
      },
    ];

    return [...navCmds, ...filterCmds, ...actionCmds];
  }, [onNavigate, onToast]);

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
