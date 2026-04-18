import { X, Moon, Sun, Rows3, LayoutList, Eye, EyeOff, PanelLeft, PanelTop, Command } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { useAppStore } from '@/stores/useAppStore';
import { NAV_SHELL } from '@/components/nav/navConfig';
import AppNavTabs from '@/components/nav/AppNavTabs';

/**
 * Fixed right tweaks rail — theme + layout from store; surfaces use semantic `base-*`.
 */
export default function TweaksPanel({ badges = {} }) {
  const open = useAppStore((s) => s.tweaksOpen);
  const setOpen = useAppStore((s) => s.setTweaksOpen);
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);
  const density = useAppStore((s) => s.density);
  const setDensity = useAppStore((s) => s.setDensity);
  const ann = useAppStore((s) => s.ann);
  const toggleAnn = useAppStore((s) => s.toggleAnn);
  const nav = useAppStore((s) => s.nav);
  const setNav = useAppStore((s) => s.setNav);
  const kc = useAppStore((s) => s.kc);
  const setKc = useAppStore((s) => s.setKc);

  if (!open) return null;

  const panel = 'rounded-xl border border-base-800 bg-base-900/80 p-3 transition-colors duration-200';
  const label = 'mb-2 font-mono text-[10px] font-semibold uppercase tracking-wider text-base-600';

  return (
    <>
      <button
        type="button"
        aria-label="Close tweaks"
        className="fixed inset-0 z-[240] bg-base-950/60 backdrop-blur-[1px] transition-colors duration-200"
        onClick={() => setOpen(false)}
      />
      <aside
        className={cn(
          'fixed right-0 top-0 z-[250] flex h-full w-full max-w-sm flex-col border-l border-base-800 bg-base-950 shadow-xl',
          'transition-colors duration-200'
        )}
      >
        <div className="flex items-center justify-between border-b border-base-800 px-4 py-3">
          <span className="font-mono text-xs font-semibold uppercase tracking-wider text-base-500">Tweaks</span>
          <Button variant="icon" size="icon" onClick={() => setOpen(false)} title="Close">
            <X className="h-4 w-4" />
          </Button>
        </div>

        <div className="flex-1 space-y-5 overflow-y-auto p-4">
          <section className={panel}>
            <div className={label}>Theme</div>
            <div className="flex gap-2">
              <Button
                variant={theme === 'dark' ? 'primary' : 'secondary'}
                size="sm"
                className="flex-1 gap-1.5 font-mono text-xs"
                onClick={() => setTheme('dark')}
              >
                <Moon className="h-3.5 w-3.5" /> Dark
              </Button>
              <Button
                variant={theme === 'light' ? 'primary' : 'secondary'}
                size="sm"
                className="flex-1 gap-1.5 font-mono text-xs"
                onClick={() => setTheme('light')}
              >
                <Sun className="h-3.5 w-3.5" /> Light
              </Button>
            </div>
          </section>

          <section className={panel}>
            <div className={label}>Density</div>
            <div className="flex gap-2">
              <Button
                variant={density === 'comfy' ? 'primary' : 'secondary'}
                size="sm"
                className="flex-1 gap-1.5 font-mono text-xs"
                onClick={() => setDensity('comfy')}
              >
                <Rows3 className="h-3.5 w-3.5" /> Comfy
              </Button>
              <Button
                variant={density === 'compact' ? 'primary' : 'secondary'}
                size="sm"
                className="flex-1 gap-1.5 font-mono text-xs"
                onClick={() => setDensity('compact')}
              >
                <LayoutList className="h-3.5 w-3.5" /> Compact
              </Button>
            </div>
          </section>

          <section className={panel}>
            <div className={label}>Annotations</div>
            <Button
              variant="secondary"
              size="sm"
              className="w-full justify-center gap-2 font-mono text-xs"
              onClick={() => toggleAnn()}
            >
              {ann === 'on' ? <Eye className="h-3.5 w-3.5" /> : <EyeOff className="h-3.5 w-3.5" />}
              {ann === 'on' ? 'On' : 'Off'}
            </Button>
          </section>

          <section className={panel}>
            <div className={label}>Kill chain view</div>
            <select
              value={kc}
              onChange={(e) => setKc(e.target.value)}
              className="h-9 w-full rounded-md border border-base-800 bg-base-950 px-2 font-mono text-xs text-base-200 outline-none transition-colors duration-200 focus:border-accent/40"
            >
              <option value="timeline">Timeline</option>
              <option value="table">Table</option>
            </select>
          </section>

          <section className={panel}>
            <div className={label}>Navigation shell</div>
            <div className="flex flex-col gap-1.5">
              {[
                { id: NAV_SHELL.SIDEBAR, label: 'Sidebar', Icon: PanelLeft },
                { id: NAV_SHELL.TOP, label: 'Top bar', Icon: PanelTop },
                { id: NAV_SHELL.MINIMAL, label: 'Command-first', Icon: Command },
              ].map(({ id, label, Icon }) => (
                <Button
                  key={id}
                  variant={nav === id ? 'primary' : 'secondary'}
                  size="sm"
                  className="w-full justify-start gap-2 font-mono text-xs"
                  onClick={() => setNav(id)}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {label}
                </Button>
              ))}
            </div>
          </section>

          <section className={panel}>
            <div className={label}>Quick jump</div>
            <AppNavTabs badges={badges} className="border-0 pb-0" />
          </section>
        </div>
      </aside>
    </>
  );
}
