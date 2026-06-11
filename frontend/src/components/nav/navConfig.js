/** @typedef {'dashboard'|'events'|'incidents'|'campaigns'|'evaluation'|'topology'|'risk'|'mitre'|'replay'|'audit'|'system'|'users'|'settings'} TabId */

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
  { id: 'dashboard', label: 'Dashboard', path: '/dashboard', section: 'core', roles: ['admin', 'analyst', 'viewer'] },
  { id: 'events', label: 'Events', path: '/events', section: 'analysis', roles: ['admin', 'analyst', 'viewer'] },
  { id: 'incidents', label: 'Incidents', path: '/incidents', section: 'analysis', roles: ['admin', 'analyst', 'viewer'] },
  { id: 'campaigns', label: 'Campaigns', path: '/campaigns', section: 'analysis', roles: ['admin', 'analyst'] },
  { id: 'evaluation', label: 'Evaluation', path: '/evaluation', section: 'analysis', roles: ['admin', 'analyst'] },
  { id: 'topology', label: 'Topology', path: '/topology', section: 'infra', roles: ['admin', 'analyst', 'viewer'] },
  { id: 'risk', label: 'Risk', path: '/risk', section: 'analysis', roles: ['admin', 'analyst', 'viewer'] },
  { id: 'mitre', label: 'MITRE', path: '/mitre', section: 'security', roles: ['admin', 'analyst'] },
  { id: 'replay', label: 'Replay', path: '/replay', section: 'security', roles: ['admin', 'analyst'] },
  { id: 'audit', label: 'Audit', path: '/audit', section: 'security', roles: ['admin'] },
  { id: 'users', label: 'Users', path: '/users', section: 'system', roles: ['admin'] },
  { id: 'system', label: 'System', path: '/system', section: 'system', roles: ['admin'] },
  { id: 'settings', label: 'Settings', path: '/settings', section: 'system', roles: ['admin', 'analyst', 'viewer'] },
];

/** ⚡ Derived maps (computed once at module load) */
const PATH_MAP = new Map(NAV_ITEMS.map((i) => [i.id, i.path]));
const ID_MAP = new Map(NAV_ITEMS.map((i) => [i.path, i.id])); // eslint-disable-line no-unused-vars

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

/** @param {string|null|undefined} role */
export function navItemsForRole(role) {
  const r = String(role || 'viewer').toLowerCase();
  return NAV_ITEMS.filter((item) => !item.roles || item.roles.includes(r));
}