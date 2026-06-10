import { useState, useRef, useEffect } from 'react';
import { Bot, X, Send } from 'lucide-react';
import { cn } from '@/lib/utils';

function authFetch(input, init = {}) {
  const t =
    localStorage.getItem('securisphere_token') ||
    sessionStorage.getItem('securisphere_token') ||
    '';
  const headers = new Headers(init.headers || {});
  if (t && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${t}`);
  return fetch(input, { ...init, headers });
}

const INITIAL_MESSAGE = {
  role: 'ai',
  content: 'Hello. I am the SecuriSphere AI Analyst. Ask me about active incidents, risk scores, or threat patterns.',
};

export default function AIChatPanel({ isOpen, onClose }) {
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const userMsg = input.trim();
    if (!userMsg) return;

    setMessages((prev) => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await authFetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, stream: false }),
      });

      if (response.status === 401) {
        setMessages((prev) => [
          ...prev,
          { role: 'ai', content: 'Session expired. Please log in again.', error: true },
        ]);
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const data = await response.json();
      setMessages((prev) => [...prev, { role: 'ai', content: data.response }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: 'ai', content: 'Error communicating with AI. Please try again.', error: true },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed top-16 right-0 z-50 flex h-[calc(100vh-4rem)] w-96 flex-col border-l border-base-800 bg-base-950 shadow-2xl">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-base-800 bg-base-900 px-4 py-3">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-base-100">
          <Bot className="h-4 w-4 text-accent" />
          AI Analyst
        </h3>
        <button
          onClick={onClose}
          className="rounded p-1 text-base-400 transition-colors hover:bg-base-800 hover:text-base-100"
          aria-label="Close AI chat"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 p-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={cn('flex', msg.role === 'user' ? 'justify-end' : 'justify-start')}
          >
            <div
              className={cn(
                'max-w-[85%] rounded-[10px] px-3 py-2 text-sm leading-relaxed',
                msg.role === 'user'
                  ? 'bg-accent text-white rounded-tr-none'
                  : msg.error
                  ? 'border border-red-500/30 bg-red-500/10 text-red-400 rounded-tl-none'
                  : 'border border-base-700 bg-base-900 text-base-200 rounded-tl-none'
              )}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {isTyping && (
          <div className="flex justify-start">
            <div className="flex items-center gap-1 rounded-[10px] rounded-tl-none border border-base-700 bg-base-900 px-3 py-2">
              <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent" />
              <span
                className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent"
                style={{ animationDelay: '0.15s' }}
              />
              <span
                className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent"
                style={{ animationDelay: '0.3s' }}
              />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-base-800 bg-base-900 p-3"
      >
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about active incidents..."
            disabled={isTyping}
            className="flex-1 rounded-lg border border-base-700 bg-base-950 px-3 py-2 text-sm text-base-100 placeholder-base-500 focus:border-accent focus:outline-none disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isTyping || !input.trim()}
            className="flex items-center gap-1 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hover disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </div>
      </form>
    </div>
  );
}
