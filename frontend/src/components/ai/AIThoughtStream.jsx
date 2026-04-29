import React, { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

export default function AIThoughtStream() {
  const [stream, setStream] = useState([]);
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    const fetchStream = async () => {
      try {
        const res = await fetch('/api/ai/stream');
        if (res.ok) {
          const data = await res.json();
          if (data.stream && data.stream.length > 0) {
            // Update stream if there is new data
            setStream(prev => {
              if (prev.length === 0 || prev[0].timestamp !== data.stream[0].timestamp) {
                // Flash typing indicator when new message comes in
                setIsTyping(true);
                setTimeout(() => setIsTyping(false), 2000);
                return data.stream;
              }
              return prev;
            });
          }
        }
      } catch (err) {
        console.error("Error fetching AI stream", err);
      }
    };

    fetchStream();
    const id = setInterval(fetchStream, 5000);
    return () => clearInterval(id);
  }, []);

  if (stream.length === 0) return null;

  const latest = stream[0];

  return (
    <div className="flex h-10 items-center justify-between border-b border-dashed border-base-800 bg-base-950 px-4">
      <div className="flex items-center gap-3 w-full">
        <span className="text-sm">🧠</span>
        <span className="text-xs font-semibold text-teal-500 uppercase tracking-wider shrink-0">
          AI Thought Stream
        </span>
        
        <div className="h-4 w-[1px] bg-base-800" />
        
        <div className="flex-1 truncate relative">
          <span className={cn(
            "text-sm font-mono transition-opacity duration-300",
            isTyping ? "opacity-0" : "opacity-100 text-teal-100"
          )}>
            &gt; {latest.commentary}
          </span>
          {isTyping && (
            <span className="absolute inset-0 flex items-center gap-1 text-teal-400">
              <span className="animate-pulse">_</span>
              <span className="text-xs font-mono opacity-50">analyzing recent events...</span>
            </span>
          )}
        </div>
        
        <span className="text-[10px] text-base-500 font-mono shrink-0">
          {new Date(latest.timestamp).toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
}
