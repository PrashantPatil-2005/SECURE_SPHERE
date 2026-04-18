import { Fragment } from 'react';
import { motion } from 'framer-motion';
import EventRow from './EventRow';

/**
 * Dense SOC log table — sticky header, mono body.
 *
 * @param {{
 *   rows: Array<Record<string, unknown>>;
 *   expandedId: string | null;
 *   selectedIndex: number;
 *   rowRefs?: React.MutableRefObject<(HTMLTableRowElement | null)[]>;
 *   onRowClick: (index: number, id: string) => void;
 * }} props
 */
export default function EventTable({ rows, expandedId, selectedIndex, rowRefs, onRowClick }) {
  return (
    <div className="max-h-[min(70vh,720px)] overflow-auto">
      <table className="w-full table-fixed text-sm font-mono">
        <thead className="sticky top-0 z-10 border-b border-base-800 bg-base-900 text-left text-xs uppercase tracking-wide text-base-400">
          <tr>
            <th className="w-[100px] py-2 pl-3 pr-2">Time</th>
            <th className="w-10 py-2 pr-2">Sev</th>
            <th className="w-[72px] py-2 pr-2">Layer</th>
            <th className="py-2 pr-2">Event</th>
            <th className="w-[120px] py-2 pr-2">Service</th>
            <th className="w-[120px] py-2 pr-2">Src</th>
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
