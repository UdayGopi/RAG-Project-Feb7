import { useState, useEffect } from 'react'
import { history } from '../api'

const LogoIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-white">
    <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>
)

export default function Sidebar({ onNewChat, onSelectHistory, isOpen = true, refreshTrigger = 0 }) {
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadHistory = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await history(startDate || undefined, endDate || undefined)
      setItems(Array.isArray(data) ? data.reverse() : [])
    } catch (e) {
      setError(e.message)
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadHistory()
  }, [startDate, endDate, refreshTrigger])

  return (
    <aside className="h-full flex flex-col overflow-hidden">
      <div className="flex-shrink-0 p-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl flex items-center justify-center shadow-md">
            <LogoIcon />
          </div>
          <div className="min-w-0">
            <h1 className="text-base font-bold text-slate-900 truncate">CarePolicy Hub</h1>
            <p className="text-xs text-slate-500">AI Policy Assistant</p>
          </div>
        </div>
      </div>

      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 pt-4 pb-2">Chat History</h2>
        <div className="px-4 pb-3">
          <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <label className="text-xs text-slate-600 font-medium block mb-1.5">Filter by date</label>
            <div className="flex gap-1.5">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="flex-1 min-w-0 p-1.5 text-xs border border-slate-200 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
              />
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="flex-1 min-w-0 p-1.5 text-xs border border-slate-200 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
              />
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-4 space-y-1.5 scrollbar-thin">
          {loading && <p className="text-xs text-slate-400 py-2">Loading...</p>}
          {error && (
            <p className="text-xs text-red-600 p-2.5 bg-red-50 rounded-lg border border-red-100">{error}</p>
          )}
          {!loading && !error && items.length === 0 && (
            <p className="text-xs text-slate-400 p-3 bg-slate-50 rounded-lg border border-slate-100">
              No history for this period.
            </p>
          )}
          {!loading && items.length > 0 && items.map((item) => (
            <button
              key={item.timestamp + (item.query || '').slice(0, 20)}
              type="button"
              onClick={() => onSelectHistory?.(item)}
              className="w-full text-left p-2.5 text-sm text-slate-700 rounded-lg hover:bg-slate-50 border border-slate-100 hover:border-blue-200 transition-all"
            >
              <span className="block font-medium text-slate-900 truncate text-xs">
                {(item.query || '').substring(0, 36)}…
              </span>
              <span className="text-xs text-slate-400 mt-0.5 block">
                {new Date(item.timestamp).toLocaleString()}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex-shrink-0 p-4 border-t border-slate-100">
        <button
          type="button"
          onClick={onNewChat}
          className="w-full bg-blue-600 text-white py-2.5 rounded-xl text-sm font-semibold hover:bg-blue-700 transition-all flex items-center justify-center gap-2 shadow-md"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M5 12h14" /><path d="M12 5v14" />
          </svg>
          New Conversation
        </button>
      </div>
    </aside>
  )
}
