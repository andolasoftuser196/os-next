const BASE = '/api'

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
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
  getInstanceStats: (name) => request(`/instances/${name}/stats`),
  getServicesStats: () => request('/services/stats'),
}

export function wsUrl(path) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${proto}://${location.host}/ws${path}`
}
