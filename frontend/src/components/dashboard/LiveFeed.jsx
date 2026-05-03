import { useEffect, useRef, useState } from 'react';
import { Radio } from 'lucide-react';
import FeedItem from './FeedItem';

/**
 * @param {{
 *   events: Record<string, unknown>[];
 *   maxItems?: number;
 *   title?: string;
 * }} props
 */
export default function LiveFeed({ events = [], maxItems = 25, title = 'Live event feed' }) {
  const [autoScroll, setAutoScroll] = useState(true);
  const feedRef = useRef(null);

  useEffect(() => {
    if (autoScroll && feedRef.current) feedRef.current.scrollTop = 0;
  }, [events, autoScroll]);

  const slice = events.slice(0, maxItems);

  return (
    <section className="flex min-h-0 flex-col rounded-[10px] border border-base-800 bg-base-900">
      <div className="flex items-center justify-between border-b border-base-800 px-3.5 py-2.5">
        <div className="flex items-center gap-2">
          <Radio className="h-3.5 w-3.5 text-base-500" />
          <h3 className="text-[12px] font-semibold tracking-wide text-base-200">{title}</h3>
          <span
            className="dot-pulse inline-block h-1.5 w-1.5 rounded-full"
            style={{ background: 'var(--sev-critical)', '--dot-color': 'rgba(239,68,68,0.6)' }}
          />
        </div>
        <label className="flex cursor-pointer items-center gap-1.5 text-[10px] text-base-500">
          <input
            type="checkbox"
            checked={autoScroll}
            onChange={(e) => setAutoScroll(e.target.checked)}
            className="h-3 w-3 accent-base-400"
          />
          Auto
        </label>
      </div>
      <div ref={feedRef} className="max-h-[min(52vh,420px)] min-h-[200px] overflow-y-auto p-2">
        {slice.length > 0 ? (
          slice.map((ev, i) => (
            <FeedItem key={safeKey(ev, i)} event={ev} flash={i === 0} />
          ))
        ) : (
          <div className="flex flex-col items-center justify-center gap-2 py-14 text-xs text-base-500">
            <Radio className="h-6 w-6 opacity-30" />
            No events yet
          </div>
        )}
      </div>
    </section>
  );
}

function safeKey(ev, i) {
  const id = ev?.event_id;
  return id != null ? String(id) : `ev-${i}`;
}
