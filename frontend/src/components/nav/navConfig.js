/** @typedef {'dashboard'|'events'|'incidents'|'campaigns'|'evaluation'|'topology'|'risk'|'mitre'|'audit'|'system'} TabId */

/**
 * @typedef NavItem
 * @property {TabId} id
 * @property {string} label
 * @property {string} path
 * @property {string} [section]
 * @property {boolean} [hidden]
 * @property {string[]} [roles]
 */

export const NAV_SHELL = {
  SIDEBAR: 'sidebar',
  TOP: 'top',
  MINIMAL: 'minimal',
};

export const NAV_SHELL_STORAGE_KEY = 'securisphere_nav_shell';

export const VALID_NAV_SHELLS = Object.values(NAV_SHELL);

/** 🔥 SINGLE SOURCE OF TRUTH */
export const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', path: '/dashboard', section: 'core' },
  { id: 'events', label: 'Events', path: '/events', section: 'analysis' },
  { id: 'incidents', label: 'Incidents', path: '/incidents', section: 'analysis' },
  { id: 'campaigns', label: 'Campaigns', path: '/campaigns', section: 'analysis' },
  { id: 'evaluation', label: 'Evaluation', path: '/evaluation', section: 'analysis' },
  { id: 'topology', label: 'Topology', path: '/topology', section: 'infra' },
  { id: 'risk', label: 'Risk', path: '/risk', section: 'analysis' },
  { id: 'mitre', label: 'MITRE', path: '/mitre', section: 'security' },
  { id: 'replay', label: 'Replay', path: '/replay', section: 'security' },
  { id: 'audit', label: 'Audit', path: '/audit', section: 'security' },
  { id: 'system', label: 'System', path: '/system', section: 'system' },
];

/** ⚡ Derived maps (computed once) */
const PATH_MAP = new Map(NAV_ITEMS.map((i) => [i.id, i.path]));
const ID_MAP = new Map(NAV_ITEMS.map((i) => [i.path, i.id]));

/**
 * O(1) lookup
 * @param {TabId} tabId
 */
export function pathForTab(tabId) {
  return PATH_MAP.get(tabId) ?? '/dashboard';
}

/**
 * Handles nested routes like /incidents/123
 * @param {string} pathname
 */
export function tabIdFromPath(pathname) {
  const clean = pathname.replace(/\/+$/, '');

  // 🔥 prefix match (important upgrade)
  for (const item of NAV_ITEMS) {
    if (clean === item.path || clean.startsWith(item.path + '/')) {
      return item.id;
    }
  }

  return 'dashboard';
}