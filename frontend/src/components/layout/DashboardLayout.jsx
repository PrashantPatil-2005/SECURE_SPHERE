import { useState, useEffect, useCallback, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { NAV_SHELL, pathForTab } from '@/components/nav/navConfig';
import SidebarNav from '@/components/nav/SidebarNav';
import TopNav from '@/components/nav/TopNav';
import CommandPalette from '@/components/nav/CommandPalette';
import AIChatPanel from '@/components/ai/AIChatPanel';
import AIThoughtStream from '@/components/ai/AIThoughtStream';
import { useCommandPalette } from '@/hooks/useCommandPalette';
import { CommandPaletteBridgeContext } from '@/contexts/CommandPaletteBridge';

function ChromeBar({ activeTab, connected, lastUpdate, shell, onOpenPalette }) {
  const path = pathForTab(activeTab);
  const [secondsAgo, setSecondsAgo] = useState(0);

  useEffect(() => {
    if (!lastUpdate) {
      setSecondsAgo(0);
      return;
    }
    const tick = () =>
      setSecondsAgo(Math.floor((Date.now() - new Date(lastUpdate).getTime()) / 1000));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [lastUpdate]);

  const staleness =
    secondsAgo < 10 ? 'text-base-400' : secondsAgo < 30 ? 'text-base-300' : 'text-base-200';

  return (
    <header
      className={cn(
        'flex h-12 shrink-0 items-center gap-3 border-b border-dashed border-base-800 bg-base-900/90 px-4 backdrop-blur-xl transition-colors duration-200'
      )}
    >
      <div className="flex min-w-0 items-baseline gap-2">
        <span className="shrink-0 text-sm font-bold tracking-tight text-base-100">SecuriSphere</span>
        <span className="truncate font-mono text-[11px] text-base-500">{path}</span>
      </div>

      {shell === NAV_SHELL.MINIMAL && (
        <button
          type="button"
          onClick={onOpenPalette}
          className="hidden min-w-0 flex-1 items-center gap-2 rounded border border-dashed border-base-800 bg-base-950/60 px-3 py-1.5 text-left font-mono text-[11px] text-base-500 transition-colors duration-200 hover:border-accent/25 hover:text-base-400 sm:flex"
        >
          <kbd className="flex items-center gap-0.5 rounded border border-base-700 bg-base-800/80 px-1.5 py-0.5 font-mono text-[10px] font-medium text-base-300 shadow-sm transition-colors group-hover:border-accent/40 group-hover:text-base-100">
            <span className="text-[11px] opacity-70">⌘</span>
            <span>K</span>
          </kbd>
          <span className="truncate">Command palette — navigate, filter, act</span>
        </button>
      )}

      <div className="flex-1" />

      {/* AI Analyst Button */}
      <button
        type="button"
        onClick={() => document.dispatchEvent(new CustomEvent('toggle-ai-chat'))}
        className="group flex h-8 shrink-0 items-center justify-center rounded-md border border-teal-800 bg-teal-950/50 px-3 transition-all duration-200 hover:border-teal-500 hover:bg-teal-900/80"
        title="AI Analyst Chat"
      >
        <span className="text-xs font-semibold text-teal-400 flex items-center gap-1">
          <span className="text-sm">🤖</span> AI Chat
        </span>
      </button>
      {/* 
      <button
        type="button"
        onClick={onOpenPalette}
        className="group flex h-8 shrink-0 items-center justify-center rounded-md border border-base-800 bg-base-950/50 px-2 transition-all duration-200 hover:border-accent/30 hover:bg-base-900"
        title="Command palette"
      >
        <kbd className="flex items-center gap-0.5 font-mono text-[10px] font-medium text-base-500 transition-colors group-hover:text-base-200">
          <span className="text-[11px] opacity-70">⌘</span>
          <span>K</span>
        </kbd>
      </button> */}

      <div className={cn('flex items-center gap-1.5 font-mono text-[10px] font-semibold uppercase', staleness)}>
        <span
          className={cn(
            'h-1.5 w-1.5 rounded-full',
            connected
              ? 'bg-base-400 shadow-[0_0_6px_rgba(0,0,0,0.12)] dark:shadow-[0_0_8px_rgba(255,255,255,0.1)]'
              : 'bg-base-600'
          )}
        />
        {connected ? 'live' : 'offline'}
        {lastUpdate && connected && (
          <span className="ml-1 normal-case text-base-500">
            {secondsAgo < 5 ? '· now' : `· ${secondsAgo}s`}
          </span>
        )}
      </div>
    </header>
  );
}

/**
 * Application shell: chrome bar + (sidebar | top | minimal) + toolbar + main + command palette.
 */
export default function DashboardLayout({
  shell,
  activeTab,
  onTabChange,
  badges,
  connected,
  lastUpdate,
  toolbar,
  statusBar,
  onProfileClick,
  children,
}) {
  const [tip, setTip] = useState('');
  const [isAiChatOpen, setIsAiChatOpen] = useState(false);

  useEffect(() => {
    const handleToggle = () => setIsAiChatOpen(prev => !prev);
    document.addEventListener('toggle-ai-chat', handleToggle);
    return () => document.removeEventListener('toggle-ai-chat', handleToggle);
  }, []);

  useEffect(() => {
    if (!tip) return;
    const t = setTimeout(() => setTip(''), 3200);
    return () => clearTimeout(t);
  }, [tip]);

  const onToast = useCallback((msg) => setTip(msg), []);

  const palette = useCommandPalette({
    onNavigate: onTabChange,
    onToast,
  });

  const openPalette = useCallback(() => palette.setOpen(true), [palette.setOpen]);

  const paletteBridge = useMemo(
    () => ({ openPalette: () => palette.setOpen(true) }),
    [palette.setOpen]
  );

  const isSidebar = shell === NAV_SHELL.SIDEBAR;
  const isTop = shell === NAV_SHELL.TOP;
  const isMinimal = shell === NAV_SHELL.MINIMAL;

  return (
    <div className="flex min-h-screen flex-col bg-base-950 transition-colors duration-200">
      {!isTop && (
        <ChromeBar
          activeTab={activeTab}
          connected={connected}
          lastUpdate={lastUpdate}
          shell={shell}
          onOpenPalette={openPalette}
        />
      )}

      <CommandPaletteBridgeContext.Provider value={paletteBridge}>
        <div className="flex min-h-0 flex-1 flex-row">
          {isSidebar && (
            <SidebarNav badges={badges} />
          )}

          <div className="flex min-w-0 flex-1 flex-col">
            {isTop && (
              <TopNav
                activeTab={activeTab}
                badges={badges}
                connected={connected}
                onProfileClick={onProfileClick}
                onOpenCommandPalette={openPalette}
              />
            )}

            {isMinimal && (
              <div className="flex items-center gap-2 border-b border-dashed border-base-800 bg-base-900/40 px-3 py-2 transition-colors duration-200 sm:hidden">
                <button
                  type="button"
                  onClick={openPalette}
                  className="group flex min-w-0 flex-1 items-center justify-between rounded-md border border-dashed border-base-800 bg-base-950/60 px-3 py-2 transition-colors duration-200 hover:border-accent/25"
                >
                  <span className="font-mono text-[11px] text-base-500 group-hover:text-base-300">Commands</span>
                  <kbd className="flex items-center gap-0.5 rounded border border-base-700 bg-base-800/80 px-1.5 py-0.5 font-mono text-[10px] font-medium text-base-400 shadow-sm transition-colors group-hover:border-accent/40 group-hover:text-base-100">
                    <span className="text-[11px] opacity-70">⌘</span>
                    <span>K</span>
                  </kbd>
                </button>
              </div>
            )}

            {<AIThoughtStream />}

            {toolbar}

            <main className="flex-1 overflow-y-auto p-6 transition-colors duration-200">{children}</main>

            {statusBar}
          </div>
        </div>

        <CommandPalette
          open={palette.open}
          onClose={() => palette.setOpen(false)}
          query={palette.query}
          onQueryChange={palette.setQuery}
          filtered={palette.filtered}
          highlight={palette.highlight}
          onHighlightChange={palette.setHighlight}
          inputRef={palette.inputRef}
          onInputKeyDown={palette.onKeyDown}
          runIndex={palette.runIndex}
        />

        <AIChatPanel isOpen={isAiChatOpen} onClose={() => setIsAiChatOpen(false)} />

        {tip && (
          <div className="fixed bottom-14 left-1/2 z-[190] max-w-md -translate-x-1/2 rounded-md border border-base-800 bg-base-900 px-4 py-2 font-mono text-[11px] text-base-300 shadow-lg transition-colors duration-200">
            {tip}
          </div>
        )}
      </CommandPaletteBridgeContext.Provider>
    </div>
  );
}
