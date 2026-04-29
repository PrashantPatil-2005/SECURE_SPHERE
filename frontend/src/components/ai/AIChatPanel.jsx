import React, { useState, useRef, useEffect } from 'react';

export default function AIChatPanel({ isOpen, onClose }) {
  const [messages, setMessages] = useState([
    { role: 'ai', content: 'Hello. I am the SecuriSphere AI Analyst. How can I help you investigate today?' }
  ]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setIsTyping(true);

    try {
      const response = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg, stream: false })
      });

      if (!response.ok) throw new Error('Network response was not ok');
      const data = await response.json();
      
      setMessages(prev => [...prev, { role: 'ai', content: data.response }]);
    } catch (error) {
      console.error("Chat error:", error);
      setMessages(prev => [...prev, { role: 'ai', content: "Error communicating with the AI. Please try again later." }]);
    } finally {
      setIsTyping(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed top-16 right-0 w-96 h-[calc(100vh-4rem)] bg-slate-900 border-l border-slate-700 shadow-2xl flex flex-col z-50">
      <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800">
        <h3 className="text-lg font-semibold text-teal-400 flex items-center gap-2">
          <span className="text-xl">🤖</span> AI Analyst
        </h3>
        <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-lg p-3 ${
              msg.role === 'user' 
                ? 'bg-teal-600 text-white rounded-tr-none' 
                : 'bg-slate-800 text-slate-300 border border-slate-700 rounded-tl-none'
            }`}>
              <div className="whitespace-pre-wrap text-sm leading-relaxed">
                {msg.content}
              </div>
            </div>
          </div>
        ))}
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-slate-800 border border-slate-700 rounded-lg rounded-tl-none p-3 max-w-[85%] flex items-center gap-2">
              <span className="w-2 h-2 bg-teal-500 rounded-full animate-bounce"></span>
              <span className="w-2 h-2 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></span>
              <span className="w-2 h-2 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="p-4 border-t border-slate-700 bg-slate-800">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about active incidents..."
            className="flex-1 bg-slate-900 border border-slate-600 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-teal-500"
            disabled={isTyping}
          />
          <button 
            type="submit" 
            disabled={isTyping || !input.trim()}
            className="bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white px-4 py-2 rounded font-medium transition-colors"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
