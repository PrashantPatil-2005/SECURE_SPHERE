import { Fragment } from 'react';
import { motion } from 'framer-motion';
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';
import EventRow from './EventRow';

/**
 * Dense SOC log table — sticky header, mono body, sortable columns.
 *
 * @param {{
 *   rows: Array<Record<string, unknown>>;
 *   expandedId: string | null;
 *   selectedIndex: number;
 *   rowRefs?: React.MutableRefObject<(HTMLTableRowElement | null)[]>;
 *   onRowClick: (index: number, id: string) => void;
 *   sortBy?: string;
 *   sortDir?: 'asc' | 'desc';
 *   onSort?: (key: string) => void;
 * }} props
 */
export default function EventTable({
  rows,
  expandedId,
  selectedIndex,
  rowRefs,
  onRowClick,
  sortBy,
  sortDir,
  onSort,
}) {
  return (
    <div className="max-h-[min(70vh,720px)] overflow-auto">
      <table className="w-full table-fixed text-sm font-mono">
        <thead className="sticky top-0 z-10 border-b border-base-800 bg-base-900 text-left text-xs uppercase tracking-wide text-base-400">
          <tr>
            <SortableTh width="100px" sortKey="time" sortBy={sortBy} sortDir={sortDir} onSort={onSort} className="pl-3">
              Time
            </SortableTh>
            <SortableTh width="40px" sortKey="severity" sortBy={sortBy} sortDir={sortDir} onSort={onSort}>
              Sev
            </SortableTh>
            <SortableTh width="72px" sortKey="layer" sortBy={sortBy} sortDir={sortDir} onSort={onSort}>
              Layer
            </SortableTh>
            <th className="py-2 pr-2">Event</th>
            <SortableTh width="120px" sortKey="service" sortBy={sortBy} sortDir={sortDir} onSort={onSort}>
              Service
            </SortableTh>
            <SortableTh width="120px" sortKey="src" sortBy={sortBy} sortDir={sortDir} onSort={onSort}>
              Src
            </SortableTh>
            <th className="w-[140px] py-2 pr-2">Target</th>
            <th className="w-[72px] py-2 pr-3">MITRE</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-base-800 text-base-300">
          {rows.length === 0 ? (
            <tr>
              <td colSpan={8} className="py-16 text-center text-xs text-base-600">
                No events match filters
              </td>
            </tr>
          ) : (
            rows.map((row, i) => (
              <Fragment key={row.id}>
                <EventRow
                  ref={(el) => {
                    if (rowRefs) {
                      rowRefs.current[i] = el;
                    }
                  }}
                  row={row}
                  selected={selectedIndex === i}
                  correlated={row.src === '10.0.2.4'}
                  flash={i === 0}
                  onClick={() => onRowClick(i, row.id)}
                />
                {expandedId === row.id && (
                  <tr>
                    <td colSpan={8} className="border-b border-base-800 bg-base-950 p-0">
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.12 }}
                      >
                        <pre className="m-3 max-h-64 overflow-auto rounded-lg border border-base-800 p-3 text-[11px] leading-relaxed text-base-500">
                          {JSON.stringify(row.raw, null, 2)}
                        </pre>
                      </motion.div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

function SortableTh({ width, sortKey, sortBy, sortDir, onSort, children, className = '' }) {
  const active = sortBy === sortKey;
  const Icon = !active ? ArrowUpDown : sortDir === 'asc' ? ArrowUp : ArrowDown;
  const handle = () => onSort?.(sortKey);
  return (
    <th style={{ width }} className={`py-2 pr-2 ${className}`}>
      <button
        type="button"
        onClick={handle}
        aria-label={`Sort by ${sortKey}`}
        aria-sort={active ? (sortDir === 'asc' ? 'ascending' : 'descending') : 'none'}
        className={`inline-flex items-center gap-1 rounded px-1 -mx-1 hover:text-base-200 ${
          active ? 'text-base-100' : ''
        }`}
      >
        {children}
        <Icon className="h-3 w-3 opacity-60" />
      </button>
    </th>
  );
}
