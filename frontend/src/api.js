const API_BASE = import.meta.env.VITE_API_URL || ''

const fetchOpts = (method = 'GET', body = null) => {
  const opts = { method, credentials: 'include' }
  if (body && typeof body === 'object' && !(body instanceof FormData)) {
    opts.headers = { 'Content-Type': 'application/json' }
    opts.body = JSON.stringify(body)
  } else if (body instanceof FormData) {
    opts.body = body
  }
  return opts
}

export async function chat(query, tenantId = null) {
  const res = await fetch(`${API_BASE}/chat`, fetchOpts('POST', { query, tenant_id: tenantId }))
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || data.detail || res.statusText)
  return data
}

export async function tenants() {
  const res = await fetch(`${API_BASE}/tenants`, fetchOpts())
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || 'Failed to fetch tenants')
  return data
}

export async function upload(formData) {
  const res = await fetch(`${API_BASE}/upload`, fetchOpts('POST', formData))
  const data = await res.json().catch(() => ({}))
  if (!res.ok && res.status !== 207) throw new Error(data.error || (data.errors && data.errors.join(', ')) || res.statusText)
  return data
}

export async function history(start, end) {
  let url = `${API_BASE}/history`
  if (start && end) url += `?start=${start}&end=${end}`
  const res = await fetch(url, fetchOpts())
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || 'Could not fetch history')
  return Array.isArray(data) ? data : (data.history || [])
}

export async function feedback(query, isHelpful) {
  const res = await fetch(`${API_BASE}/feedback`, fetchOpts('POST', { query, is_helpful: isHelpful }))
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || 'Feedback failed')
  return data
}

export async function analytics() {
  const res = await fetch(`${API_BASE}/analytics`, fetchOpts())
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || 'Could not fetch analytics')
  return data
}

export async function schedulesGet() {
  const res = await fetch(`${API_BASE}/schedules`, fetchOpts())
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || 'Failed to fetch schedules')
  return data
}

export async function schedulesPost(payload) {
  const res = await fetch(`${API_BASE}/schedules`, fetchOpts('POST', payload))
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || 'Failed to add schedule')
  return data
}

export async function scheduleDelete(id) {
  const res = await fetch(`${API_BASE}/schedules/${id}`, fetchOpts('DELETE'))
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || 'Failed to delete')
  return data
}

export async function schedulePut(id, payload) {
  const res = await fetch(`${API_BASE}/schedules/${id}`, fetchOpts('PUT', payload))
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.error || 'Failed to update')
  return data
}

/** Check current user (for auth gate). Returns { user } or null if 401. */
export async function me() {
  const res = await fetch(`${API_BASE}/me`, fetchOpts())
  if (res.status === 401) return null
  const data = await res.json().catch(() => ({}))
  if (!res.ok) return null
  return data.user || data
}

export { API_BASE }
