/** @typedef {{ id: string; label: string; path: string }} NavItem */

export const NAV_SHELL = {
  SIDEBAR: 'sidebar',
  TOP: 'top',
  MINIMAL: 'minimal',
};

export const NAV_SHELL_STORAGE_KEY = 'securisphere_nav_shell';

export const VALID_NAV_SHELLS = [NAV_SHELL.SIDEBAR, NAV_SHELL.TOP, NAV_SHELL.MINIMAL];

/** @type {Record<string, string>} */
const TAB_TO_PATH = {
  intro: '/intro',
  dashboard: '/dashboard',
  events: '/events',
  incidents: '/incidents',
  topology: '/topology',
  risk: '/risk',
  mitre: '/mitre',
  system: '/system',
};

/** @type {NavItem[]} */
export const NAV_ITEMS = [
  { id: 'intro', label: 'Intro', path: '/intro' },
  { id: 'dashboard', label: 'Dashboard', path: '/dashboard' },
  { id: 'events', label: 'Events', path: '/events' },
  { id: 'incidents', label: 'Incidents', path: '/incidents' },
  { id: 'topology', label: 'Topology', path: '/topology' },
  { id: 'risk', label: 'Risk', path: '/risk' },
  { id: 'mitre', label: 'MITRE', path: '/mitre' },
  { id: 'system', label: 'System', path: '/system' },
];

/**
 * @param {string} tabId
 * @returns {string}
 */
export function pathForTab(tabId) {
  return TAB_TO_PATH[tabId] ?? '/dashboard';
}

/**
 * @param {string} pathname
 * @returns {string}
 */
export function tabIdFromPath(pathname) {
  const normalized = pathname.replace(/\/+$/, '') || '/';
  const hit = Object.entries(TAB_TO_PATH).find(([, p]) => p === normalized);
  if (hit) return hit[0];
  return 'dashboard';
}
