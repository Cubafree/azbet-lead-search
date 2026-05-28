const BASE = import.meta.env.VITE_API_URL || ''

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

export const api = {
  // Channels
  getChannels: (params = {}) => {
    const qs = new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ''))
    ).toString()
    return request(`/api/channels${qs ? `?${qs}` : ''}`)
  },
  getStats: () => request('/api/channels/stats'),
  updateChannel: (id, body) => request(`/api/channels/${id}`, {
    method: 'PATCH', body: JSON.stringify(body),
  }),

  // Jobs
  runJob: (queries) => request('/api/jobs/run', {
    method: 'POST', body: JSON.stringify({ queries: queries ?? null }),
  }),
  getJobStatus: (jobId) => request(`/api/jobs/status/${jobId}`),
  getLatestJob: () => request('/api/jobs/latest'),

  // Autonomous agent
  runAgent: (geo = 'all') => request('/api/agent/run', {
    method: 'POST', body: JSON.stringify({ geo }),
  }),

  // Archive / unarchive
  archiveChannel: (id) => request(`/api/channels/${id}/archive`, { method: 'POST' }),
  unarchiveChannel: (id) => request(`/api/channels/${id}/unarchive`, { method: 'POST' }),
  setContacted: (id, value) => request(`/api/channels/${id}`, {
    method: 'PATCH', body: JSON.stringify({ is_contacted: value }),
  }),

  // Monitor
  checkCompetitors: () => request('/api/monitor/competitors', { method: 'POST', body: JSON.stringify({}) }),
  refreshStale: () => request('/api/monitor/refresh-stale', { method: 'POST', body: JSON.stringify({}) }),

  // Affiliate grouping
  groupAffiliates: () => request('/api/channels/group-affiliates', { method: 'POST' }),

  // Queries
  getQueries: () => request('/api/queries'),
  createQuery: (body) => request('/api/queries', { method: 'POST', body: JSON.stringify(body) }),
  deleteQuery: (id) => request(`/api/queries/${id}`, { method: 'DELETE' }),
  resetQuery: (id) => request(`/api/queries/${id}/reset`, { method: 'POST' }),
}
