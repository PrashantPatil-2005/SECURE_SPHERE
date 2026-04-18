import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Download } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { filterEvents } from './filterEvents';
import { normalizeEvent } from './normalizeEvent';
import { exportEventsCsv } from './exportEventsCsv';
import { buildCanonicalQuery } from './buildCanonicalQuery';
import QueryBar from './QueryBar';
import EventFilters from './EventFilters';
import EventStatsBar from './EventStatsBar';
import EventTable from './EventTable';
import TimelineRibbon from './TimelineRibbon';

const MODE_KEY = 'securisphere_events_mode';

const anim = { initial: { opacity: 0, y: 10 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.22 } };

function isTypingTarget(el) {
  if (!el || !(el instanceof HTMLElement)) return false;
  const tag = el.tagName;
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return true;
  if (el.getAttribute('contenteditable') === 'true') return true;
  return false;
}

/**
 * SecuriSphere events console — dense table (default) or timeline + table.
 *
 * @param {{ events?: Record<string, unknown>[] }} props
 */
export default function EventsPage({ events = [] }) {
  const [mode, setMode] = useState(() => {
    try {
      const s = sessionStorage.getItem(MODE_KEY);
      if (s === 'table' || s === 'timeline') return s;
    } catch {
      /* ignore */
    }
    return 'table';
  });

  const [search, setSearch] = useState('');
  const [layer, setLayer] = useState('all');
  const [severity, setSeverity] = useState('all');
  const [timePreset, setTimePreset] = useState('all');
  const [srcIp, setSrcIp] = useState('all');
  const [timeRange, setTimeRange] = useState(null);
  const [ribbonBin, setRibbonBin] = useState(null);

  const [expandedId, setExpandedId] = useState(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [autoScrollTop, setAutoScrollTop] = useState(true);

  const queryRef = useRef(null);
  const rowRefs = useRef([]);
  const prevLenRef = useRef(events.length);

  useEffect(() => {
    try {
      sessionStorage.setItem(MODE_KEY, mode);
    } catch {
      /* ignore */
    }
  }, [mode]);

  const filterState = useMemo(
    () => ({
      search,
      layer,
      severity,
      timePreset,
      srcIp,
      timeRange,
    }),
    [search, layer, severity, timePreset, srcIp, timeRange]
  );

  const histogramEvents = useMemo(
    () => filterEvents(events, { ...filterState, timeRange: null }),
    [events, filterState]
  );

  const tableEvents = useMemo(() => filterEvents(events, filterState), [events, filterState]);

  const rows = useMemo(() => tableEvents.map((e, i) => normalizeEvent(e, i)), [tableEvents]);

  const canonical = useMemo(() => buildCanonicalQuery(filterState), [filterState]);

  useEffect(() => {
    setSelectedIndex((i) => {
      const max = Math.max(0, rows.length - 1);
      return Math.min(i, max);
    });
  }, [rows.length]);

  useEffect(() => {
    if (events.length > prevLenRef.current && autoScrollTop) {
      rowRefs.current[0]?.scrollIntoView({ block: 'start' });
    }
    prevLenRef.current = events.length;
  }, [events, autoScrollTop]);

  const onRibbonSelect = useCallback(({ start, end, binIndex }) => {
    setTimeRange({ start, end });
    setRibbonBin(binIndex);
  }, []);

  const clearRibbon = useCallback(() => {
    setTimeRange(null);
    setRibbonBin(null);
  }, []);

  const onLayer = useCallback((v) => {
    setLayer(v);
    setTimeRange(null);
    setRibbonBin(null);
  }, []);

  const onSeverity = useCallback((v) => {
    setSeverity(v);
    setTimeRange(null);
    setRibbonBin(null);
  }, []);

  const onTimePreset = useCallback((v) => {
    setTimePreset(v);
    setTimeRange(null);
    setRibbonBin(null);
  }, []);

  const onSrcIp = useCallback((v) => {
    setSrcIp(v);
    setTimeRange(null);
    setRibbonBin(null);
  }, []);

  const onRowClick = useCallback(
    (index, id) => {
      setSelectedIndex(index);
      setExpandedId((ex) => (ex === id ? null : id));
    },
    []
  );

  useEffect(() => {
    const onKey = (e) => {
      if (isTypingTarget(e.target)) {
        if (e.key === 'Escape') e.target.blur?.();
        return;
      }
      if (e.key === 'j' || e.key === 'J') {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(rows.length - 1, i + 1));
      }
      if (e.key === 'k' || e.key === 'K') {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(0, i - 1));
      }
      if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        queryRef.current?.focus();
      }
      if (e.key === 'Enter') {
        const row = rows[selectedIndex];
        if (!row) return;
        e.preventDefault();
        setExpandedId((ex) => (ex === row.id ? null : row.id));
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [rows, selectedIndex]);

  useEffect(() => {
    rowRefs.current[selectedIndex]?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  return (
    <motion.div {...anim} className="space-y-4 text-base-200">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-base-100">Security events</h1>
          <p className="text-xs text-base-500">Filter-first log analysis · keyboard: j/k · / · ↵</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-lg border border-base-800 bg-base-900 p-0.5 font-mono text-[10px]">
            <ModeBtn active={mode === 'table'} onClick={() => setMode('table')} label="Table" />
            <ModeBtn active={mode === 'timeline'} onClick={() => setMode('timeline')} label="Timeline" />
          </div>
          <Button
            variant="secondary"
            size="sm"
            className="border-base-800 bg-base-900 font-mono text-xs"
            onClick={() => exportEventsCsv(tableEvents)}
          >
            <Download className="h-3 w-3" /> CSV
          </Button>
        </div>
      </div>

      <QueryBar
        ref={queryRef}
        value={search}
        onChange={setSearch}
        canonicalQuery={canonical}
      />

      <div className="rounded-lg border border-base-800 bg-base-900 p-3">
        <EventFilters
          layer={layer}
          severity={severity}
          timePreset={timePreset}
          srcIp={srcIp}
          onLayer={onLayer}
          onSeverity={onSeverity}
          onTimePreset={onTimePreset}
          onSrcIp={onSrcIp}
          hasCustomTimeRange={!!timeRange}
          onClearTimeRange={clearRibbon}
        />
        <div className="mt-3">
          <EventStatsBar events={events} filteredEvents={tableEvents} />
        </div>
        <label className="mt-2 flex cursor-pointer items-center gap-2 font-mono text-[10px] text-base-500">
          <input
            type="checkbox"
            checked={autoScrollTop}
            onChange={(e) => setAutoScrollTop(e.target.checked)}
            className="h-3 w-3 accent-base-500"
          />
          Pin to newest on live updates
        </label>
      </div>

      {mode === 'timeline' && (
        <TimelineRibbon
          events={histogramEvents}
          activeBin={ribbonBin}
          onSelectBin={onRibbonSelect}
        />
      )}

      <div className="overflow-hidden rounded-lg border border-base-800 bg-base-900">
        <div className="border-b border-base-800 px-4 py-2 font-mono text-[10px] text-base-500">
          {mode === 'table' ? 'Dense table' : 'Filtered list (timeline window applies when set)'}
        </div>
        <EventTable
          rows={rows}
          expandedId={expandedId}
          selectedIndex={selectedIndex}
          rowRefs={rowRefs}
          onRowClick={onRowClick}
        />
      </div>

      <p className="font-mono text-[10px] text-base-600">
        <kbd className="rounded border border-base-700 px-1">j</kbd> /{' '}
        <kbd className="rounded border border-base-700 px-1">k</kbd> move ·{' '}
        <kbd className="rounded border border-base-700 px-1">/</kbd> search ·{' '}
        <kbd className="rounded border border-base-700 px-1">Enter</kbd> expand
      </p>
    </motion.div>
  );
}

function ModeBtn({ active, onClick, label }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-md px-2.5 py-1 transition-colors ${
        active ? 'bg-base-950 text-base-100 ring-1 ring-base-700' : 'text-base-500 hover:text-base-300'
      }`}
    >
      {label}
    </button>
  );
}
