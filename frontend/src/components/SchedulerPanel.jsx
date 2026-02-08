import { useState, useEffect } from 'react'
import { tenants, schedulesGet, schedulesPost, scheduleDelete, schedulePut } from '../api'

export default function SchedulerPanel() {
  const [tenantList, setTenantList] = useState([])
  const [schedules, setSchedules] = useState([])
  const [tenant, setTenant] = useState('')
  const [tenantNew, setTenantNew] = useState('')
  const [url, setUrl] = useState('')
  const [frequency, setFrequency] = useState('daily')
  const [startTime, setStartTime] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadTenants = async () => {
    try {
      const data = await tenants()
      setTenantList(data.tenants || [])
    } catch (_) {}
  }

  const loadSchedules = async () => {
    try {
      const data = await schedulesGet()
      setSchedules(data.schedules || [])
      setError(null)
    } catch (e) {
      setError(e.message)
      setSchedules([])
    }
  }

  useEffect(() => {
    loadTenants()
    loadSchedules()
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    const t = (tenantNew && tenantNew.trim()) || tenant || ''
    if (!t) {
      setError('Please select or enter a tenant.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await schedulesPost({ tenant: t, url: url.trim(), frequency, start_time: startTime })
      setTenant('')
      setTenantNew('')
      setUrl('')
      setStartTime('')
      loadSchedules()
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    try {
      await scheduleDelete(id)
      loadSchedules()
    } catch (e) {
      setError(e.message)
    }
  }

  const handleEdit = async (s) => {
    const newTenant = window.prompt('Tenant', s.tenant || '')
    if (newTenant === null) return
    const newUrl = window.prompt('URL', s.url || '')
    if (newUrl === null) return
    const newFreq = window.prompt('Frequency (hourly,daily,weekly,monthly,3months,6months)', s.frequency || '')
    if (newFreq === null) return
    const newStart = window.prompt('Start time (ISO/datetime-local)', s.start_time || '')
    if (newStart === null) return
    try {
      await schedulePut(s.id, { tenant: newTenant, url: newUrl, frequency: newFreq, start_time: newStart })
      loadSchedules()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="p-6 space-y-6 h-full overflow-y-auto bg-slate-50">
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <h3 className="text-2xl font-bold text-slate-900 mb-6 tracking-tight">Scheduler Ingestion</h3>
        <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Select Tenant</label>
            <select
              value={tenant}
              onChange={(e) => setTenant(e.target.value)}
              className="w-full p-3 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">-- Select --</option>
              {tenantList.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
            <p className="text-xs text-slate-500 mt-1.5">or create a new tenant</p>
            <input
              type="text"
              value={tenantNew}
              onChange={(e) => setTenantNew(e.target.value)}
              placeholder="New tenant ID (optional)"
              className="mt-2 w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">URL</label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://..."
              className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Frequency</label>
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="hourly">Hourly</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="3months">Every 3 months</option>
              <option value="6months">Every 6 months</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold text-slate-700 mb-2">Start time (ISO)</label>
            <input
              type="datetime-local"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div className="md:col-span-2">
            {error && <p className="text-red-600 text-sm mb-2">{error}</p>}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white font-semibold p-3 rounded-xl hover:bg-blue-700 transition-all shadow-md hover:shadow-lg disabled:opacity-70"
            >
              Add Schedule
            </button>
          </div>
        </form>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <h4 className="text-lg font-bold text-slate-900 mb-4 tracking-tight">Existing Schedules</h4>
        {schedules.length === 0 ? (
          <p className="text-sm text-slate-500">No schedules yet.</p>
        ) : (
          <ul className="space-y-2 text-sm text-slate-700">
            {schedules.map((s) => (
              <li key={s.id} className="flex items-center justify-between bg-slate-50 border border-slate-200 rounded-lg p-3">
                <span className="truncate mr-3 text-slate-700">
                  <strong className="text-slate-900">{s.tenant}</strong> — {s.url} — {s.frequency} — {s.start_time || ''}
                </span>
                <span className="flex items-center gap-2 flex-shrink-0">
                  <button type="button" onClick={() => handleEdit(s)} className="px-3 py-1.5 text-xs border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 font-medium">
                    Edit
                  </button>
                  <button type="button" onClick={() => handleDelete(s.id)} className="px-3 py-1.5 text-xs border border-red-300 rounded-lg text-red-700 hover:bg-red-50 font-medium">
                    Delete
                  </button>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
