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
    <section className="flex min-h-0 flex-col rounded-lg border border-base-800 bg-base-900">
      <div className="flex items-center justify-between border-b border-base-800 px-4 py-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-base-200">{title}</h3>
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-base-400 shadow-[0_0_6px_rgba(0,0,0,0.15)] dark:shadow-[0_0_8px_rgba(255,255,255,0.12)]" />
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
