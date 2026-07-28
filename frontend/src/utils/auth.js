const AUTH_KEYS = {
  accessToken: 'access_token',
  refreshToken: 'refresh_token',
  role: 'role',
  username: 'username',
};

const LEGACY_AUTH_KEYS = ['adminToken'];
const ROLE_ALIASES = {
  admin: 'admin',
  administrator: 'admin',
  user: 'user',
  passenger: 'passenger',
};

function sanitizeValue(value) {
  return typeof value === 'string' ? value.trim() : value;
}

export function normalizeRole(role) {
  const sanitizedRole = sanitizeValue(role);
  if (typeof sanitizedRole !== 'string') {
    return '';
  }

  const normalizedRole = sanitizedRole.toLowerCase();
  return ROLE_ALIASES[normalizedRole] || normalizedRole;
}

export function getAuthSession() {
  if (typeof window === 'undefined') {
    return {
      accessToken: null,
      refreshToken: null,
      role: null,
      username: null,
    };
  }

  const accessToken = sanitizeValue(localStorage.getItem(AUTH_KEYS.accessToken));
  const refreshToken = sanitizeValue(localStorage.getItem(AUTH_KEYS.refreshToken));
  const role = sanitizeValue(localStorage.getItem(AUTH_KEYS.role));
  const username = sanitizeValue(localStorage.getItem(AUTH_KEYS.username));

  return {
    accessToken,
    refreshToken,
    role,
    normalizedRole: normalizeRole(role),
    username,
  };
}

export function setAuthSession({ access_token, refresh_token, role, username }) {
  if (typeof window === 'undefined') {
    return;
  }

  const sanitizedAccessToken = sanitizeValue(access_token);
  const sanitizedRefreshToken = sanitizeValue(refresh_token);
  const sanitizedRole = sanitizeValue(role);
  const sanitizedUsername = sanitizeValue(username);

  if (sanitizedAccessToken) {
    localStorage.setItem(AUTH_KEYS.accessToken, sanitizedAccessToken);
  } else {
    localStorage.removeItem(AUTH_KEYS.accessToken);
  }

  if (sanitizedRefreshToken) {
    localStorage.setItem(AUTH_KEYS.refreshToken, sanitizedRefreshToken);
  } else {
    localStorage.removeItem(AUTH_KEYS.refreshToken);
  }

  if (sanitizedRole) {
    localStorage.setItem(AUTH_KEYS.role, sanitizedRole);
  } else {
    localStorage.removeItem(AUTH_KEYS.role);
  }

  if (sanitizedUsername) {
    localStorage.setItem(AUTH_KEYS.username, sanitizedUsername);
  } else {
    localStorage.removeItem(AUTH_KEYS.username);
  }

  LEGACY_AUTH_KEYS.forEach((key) => localStorage.removeItem(key));
}

export function clearAuthSession() {
  if (typeof window === 'undefined') {
    return;
  }

  Object.values(AUTH_KEYS).forEach((key) => localStorage.removeItem(key));
  LEGACY_AUTH_KEYS.forEach((key) => localStorage.removeItem(key));
}

export function hasAccessToken() {
  const { accessToken } = getAuthSession();
  return Boolean(accessToken);
}

export function getPostLoginRoute(role) {
  return isAdminRole(role) ? '/admin/dashboard' : '/dashboard';
}

export function getRoleBasedRedirect(role) {
  return getPostLoginRoute(role);
}

export function isAuthenticated() {
  return hasAccessToken();
}

export function isAdminRole(role) {
  return normalizeRole(role) === 'admin';
}
