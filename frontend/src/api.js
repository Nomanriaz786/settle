/** Small fetch helpers for the Settle API. Errors carry the server's message. */
async function call(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' }, ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`)
  return data
}

export const api = {
  disputes: () => call('/disputes'),
  dispute: (id) => call(`/disputes/${id}`),
  analyze: (id) => call(`/disputes/${id}/analyze`, { method: 'POST' }),
  approve: (id, evidence_text) => call(`/disputes/${id}/approve`, { method: 'POST', body: { evidence_text } }),
  accept: (id) => call(`/disputes/${id}/accept`, { method: 'POST' }),
  simulate: (scenario) => call('/simulate', { method: 'POST', body: { scenario } }),
}
