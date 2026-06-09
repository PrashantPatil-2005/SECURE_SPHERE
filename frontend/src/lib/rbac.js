/** @typedef {'admin'|'analyst'|'viewer'} Role */

/** @type {Record<Role, string[]>} */
export const NAV_BY_ROLE = {
  admin: [
    'dashboard', 'events', 'incidents', 'campaigns', 'evaluation',
    'topology', 'risk', 'mitre', 'replay', 'audit', 'system', 'users',
  ],
  analyst: [
    'dashboard', 'events', 'incidents', 'campaigns', 'evaluation',
    'topology', 'risk', 'mitre', 'replay',
  ],
  viewer: ['dashboard', 'events', 'incidents', 'topology', 'risk'],
};

/** @type {Record<string, Role[]>} */
export const PERMISSION_ROLES = {
  'users.manage': ['admin'],
  'incidents.read': ['admin', 'analyst', 'viewer'],
  'incidents.write': ['admin', 'analyst'],
  'campaigns.read': ['admin', 'analyst'],
  'dashboard.read': ['admin', 'analyst', 'viewer'],
  'topology.read': ['admin', 'analyst', 'viewer'],
  'mitre.read': ['admin', 'analyst'],
  'reports.generate': ['admin', 'analyst'],
  'audit.read': ['admin'],
  'system.manage': ['admin'],
  'evaluation.read': ['admin', 'analyst'],
  'replay.read': ['admin', 'analyst'],
};

/** @param {string|null|undefined} role */
export function normalizeRole(role) {
  const r = String(role || 'viewer').toLowerCase();
  if (r === 'user' || r === 'readonly') return 'viewer';
  if (r === 'admin' || r === 'analyst' || r === 'viewer') return r;
  return 'viewer';
}

/** @param {string|null|undefined} role */
export function permissionsForRole(role) {
  const r = normalizeRole(role);
  return Object.entries(PERMISSION_ROLES)
    .filter(([, roles]) => roles.includes(r))
    .map(([p]) => p);
}

/** @param {string|null|undefined} role @param {string} permission */
export function hasPermission(role, permission, explicit = []) {
  if (Array.isArray(explicit) && explicit.includes(permission)) return true;
  const allowed = PERMISSION_ROLES[permission] || [];
  return allowed.includes(normalizeRole(role));
}

/** @param {string|null|undefined} role @param {string} navId */
export function canAccessNav(role, navId) {
  const list = NAV_BY_ROLE[normalizeRole(role)] || NAV_BY_ROLE.viewer;
  return list.includes(navId);
}

/** @param {string|null|undefined} role @param {Role|Role[]} allowed */
export function hasRole(role, allowed) {
  const r = normalizeRole(role);
  const list = Array.isArray(allowed) ? allowed : [allowed];
  return list.map(normalizeRole).includes(r);
}
