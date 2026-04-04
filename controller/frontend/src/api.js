const BASE = '/api'

// Auth credentials stored in sessionStorage
function getAuthHeader() {
  const creds = sessionStorage.getItem('controller_auth')
  if (!creds) return {}
  return { Authorization: `Basic ${creds}` }
}

export function setAuth(user, pass) {
  const encoded = btoa(`${user}:${pass}`)
  sessionStorage.setItem('controller_auth', encoded)
}

export function clearAuth() {
  sessionStorage.removeItem('controller_auth')
}

export function isAuthenticated() {
  return !!sessionStorage.getItem('controller_auth')
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...getAuthHeader(), ...options.headers },
    ...options,
  })
  if (res.status === 401) {
    clearAuth()
    window.location.reload()
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

export const api = {
  getStatus: () => request('/status'),
  getInstances: () => request('/instances'),
  createInstance: (data) => request('/instances', { method: 'POST', body: JSON.stringify(data) }),
  destroyInstance: (name, dropDb = false) => request(`/instances/${name}?drop_db=${dropDb}`, { method: 'DELETE' }),
  startInstance: (name) => request(`/instances/${name}/start`, { method: 'POST' }),
  stopInstance: (name) => request(`/instances/${name}/stop`, { method: 'POST' }),
  dbSetup: (name) => request(`/instances/${name}/db-setup`, { method: 'POST' }),
  dbSnapshot: (name) => request(`/instances/${name}/db-snapshot`, { method: 'POST' }),
  dbRestore: (name, snapshot) => request(`/instances/${name}/db-restore?snapshot=${encodeURIComponent(snapshot)}`, { method: 'POST' }),
  getSnapshots: () => request('/snapshots'),
  getInstanceStats: (name) => request(`/instances/${name}/stats`),
  getServicesStats: () => request('/services/stats'),
}

export function wsUrl(path) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const token = sessionStorage.getItem('controller_auth') || ''
  return `${proto}://${location.host}/ws${path}?token=${encodeURIComponent(token)}`
}
