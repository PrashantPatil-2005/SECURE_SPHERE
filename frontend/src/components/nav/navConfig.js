// /** @typedef {{ id: string; label: string; path: string }} NavItem */

// export const NAV_SHELL = {
//   SIDEBAR: 'sidebar',
//   TOP: 'top',
//   MINIMAL: 'minimal',
// };

// export const NAV_SHELL_STORAGE_KEY = 'securisphere_nav_shell';

// export const VALID_NAV_SHELLS = [NAV_SHELL.SIDEBAR, NAV_SHELL.TOP, NAV_SHELL.MINIMAL];

// /** @type {Record<string, string>} */
// const TAB_TO_PATH = {
//   intro: '/intro',
//   dashboard: '/dashboard',
//   events: '/events',
//   incidents: '/incidents',
//   topology: '/topology',
//   risk: '/risk',
//   mitre: '/mitre',
//   system: '/system',
// };

// /** @type {NavItem[]} */
// export const NAV_ITEMS = [
//   { id: 'intro', label: 'Intro', path: '/intro' },
//   { id: 'dashboard', label: 'Dashboard', path: '/dashboard' },
//   { id: 'events', label: 'Events', path: '/events' },
//   { id: 'incidents', label: 'Incidents', path: '/incidents' },
//   { id: 'topology', label: 'Topology', path: '/topology' },
//   { id: 'risk', label: 'Risk', path: '/risk' },
//   { id: 'mitre', label: 'MITRE', path: '/mitre' },
//   { id: 'system', label: 'System', path: '/system' },
// ];

// /**
//  * @param {string} tabId
//  * @returns {string}
//  */
// export function pathForTab(tabId) {
//   return TAB_TO_PATH[tabId] ?? '/dashboard';
// }

// /**
//  * @param {string} pathname
//  * @returns {string}
//  */
// export function tabIdFromPath(pathname) {
//   const normalized = pathname.replace(/\/+$/, '') || '/';
//   const hit = Object.entries(TAB_TO_PATH).find(([, p]) => p === normalized);
//   if (hit) return hit[0];
//   return 'dashboard';
// }
/// @typedef {'intro'|'dashboard'|'events'|'incidents'|'topology'|'risk'|'mitre'|'system'} TabId

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
  { id: 'intro', label: 'Intro', path: '/intro', section: 'core' },
  { id: 'dashboard', label: 'Dashboard', path: '/dashboard', section: 'core' },
  { id: 'events', label: 'Events', path: '/events', section: 'analysis' },
  { id: 'incidents', label: 'Incidents', path: '/incidents', section: 'analysis' },
  { id: 'topology', label: 'Topology', path: '/topology', section: 'infra' },
  { id: 'risk', label: 'Risk', path: '/risk', section: 'analysis' },
  { id: 'mitre', label: 'MITRE', path: '/mitre', section: 'security' },
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