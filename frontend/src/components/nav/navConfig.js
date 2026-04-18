import {
  LayoutDashboard,
  Radio,
  Network,
  AlertTriangle,
  Zap,
  Server,
  Crosshair,
} from 'lucide-react';

/** Persisted shell: sidebar (default), top pills, or command-first chrome. */
export const NAV_SHELL = {
  SIDEBAR: 'sidebar',
  TOP: 'top',
  MINIMAL: 'minimal',
};

export const NAV_SHELL_STORAGE_KEY = 'ss_nav_shell';

export const VALID_NAV_SHELLS = Object.values(NAV_SHELL);

/** Primary SOC navigation — order matches Detect → Investigate → Analyze → Act flow. */
export const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { id: 'incidents', label: 'Incidents', path: '/incidents', icon: AlertTriangle, badgeKey: 'incidents' },
  { id: 'topology', label: 'Topology', path: '/topology', icon: Network },
  { id: 'events', label: 'Events', path: '/events', icon: Radio, badgeKey: 'events' },
  { id: 'mitre', label: 'MITRE', path: '/mitre', icon: Crosshair },
  { id: 'risk', label: 'Risk', path: '/risk', icon: Zap },
  { id: 'system', label: 'System', path: '/system', icon: Server },
];

export function pathForTab(tabId) {
  const item = NAV_ITEMS.find((n) => n.id === tabId);
  return item?.path ?? '/dashboard';
}

export function labelForTab(tabId) {
  const item = NAV_ITEMS.find((n) => n.id === tabId);
  return item?.label ?? 'Dashboard';
}
