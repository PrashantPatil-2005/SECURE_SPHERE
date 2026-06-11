import { useState, useEffect, useCallback, useMemo } from 'react';
import { cn } from '@/lib/utils';
import { NAV_SHELL } from '@/components/nav/navConfig';
import SidebarNav from '@/components/nav/SidebarNav';
import TopNav from '@/components/nav/TopNav';
import CommandPalette from '@/components/nav/CommandPalette';
import AIChatPanel from '@/components/ai/AIChatPanel';
import { useCommandPalette } from '@/hooks/useCommandPalette';
import { CommandPaletteBridgeContext } from '@/contexts/CommandPaletteBridge';

/**
 * Application shell: (sidebar | top | minimal) + toolbar + main + command palette.
 * ChromeBar removed — brand lives in the sidebar; path breadcrumb lives in Header.
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
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-[2100] focus:rounded-md focus:border focus:border-accent focus:bg-base-900 focus:px-3 focus:py-1.5 focus:text-xs focus:font-semibold focus:text-base-100"
      >
        Skip to main content
      </a>

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

            {/* Minimal shell: compact ⌘K strip on mobile only */}
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

            {toolbar}

            <main
              id="main-content"
              tabIndex={-1}
              className="flex-1 overflow-y-auto p-6 transition-colors duration-200 focus:outline-none"
            >
              {children}
            </main>

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
          <div className="fixed bottom-14 left-1/2 z-[190] max-w-md -translate-x-1/2 rounded-md border border-base-800 bg-base-900 px-4 py-2 text-xs text-base-300 shadow-lg transition-colors duration-200">
            {tip}
          </div>
        )}
      </CommandPaletteBridgeContext.Provider>
    </div>
  );
}
