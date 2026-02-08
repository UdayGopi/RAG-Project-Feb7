import { useState, useEffect } from 'react'
import { history } from '../api'

export default function ChatHistoryStrip({ onNewChat, onSelectHistory, refreshTrigger }) {
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

  const grouped = (() => {
    const now = new Date()
    const a = [], b = []
    items.forEach((item) => {
      const d = new Date(item.timestamp)
      if ((now - d) / (1000 * 60 * 60 * 24) <= 7) a.push(item)
      else b.push(item)
    })
    return { 'Last 7 days': a, 'Older': b }
  })()

  return (
    <div className="h-full flex flex-col border-r border-slate-200 bg-slate-50/50">
      <div className="flex-shrink-0 p-4 border-b border-slate-200">
        <div className="flex items-center gap-2 mb-3">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-semibold text-slate-500">Live Preview</span>
        </div>
        <div className="flex items-center gap-2 mb-4">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-blue-700 flex items-center justify-center text-white text-sm font-bold">AI</div>
          <span className="font-semibold text-slate-900">CarePolicy</span>
        </div>
        <button
          type="button"
          onClick={onNewChat}
          className="w-full flex items-center justify-center gap-2 rounded-xl py-2.5 px-3 bg-blue-600 text-white font-semibold text-sm hover:bg-blue-700 shadow-md transition-all"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 5v14M5 12h14" /></svg>
          New Chat
        </button>
      </div>
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 pt-3 pb-2">Chat History</p>
        <div className="px-3 pb-2">
          <div className="flex gap-1.5">
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="flex-1 min-w-0 p-1.5 text-xs border border-slate-200 rounded-lg bg-white focus:ring-2 focus:ring-blue-500" />
            <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="flex-1 min-w-0 p-1.5 text-xs border border-slate-200 rounded-lg bg-white focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-3 space-y-1 scrollbar-thin">
          {loading && <p className="text-xs text-slate-400 py-2">Loading...</p>}
          {error && <p className="text-xs text-red-600 py-2">{error}</p>}
          {!loading && !error && (
            <>
              {grouped['Last 7 days'].length > 0 && (
                <div className="py-1">
                  <p className="text-xs text-slate-400 font-medium px-1 pb-1">Last 7 days</p>
                  {grouped['Last 7 days'].map((item) => (
                    <button key={item.timestamp + (item.query || '').slice(0, 20)} type="button" onClick={() => onSelectHistory?.(item)} className="w-full text-left px-3 py-2 rounded-lg hover:bg-white flex items-center gap-2 text-slate-700 border border-transparent hover:border-slate-200 transition-all">
                      <svg className="w-4 h-4 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                      <span className="truncate text-sm">{(item.query || '').substring(0, 26)}…</span>
                    </button>
                  ))}
                </div>
              )}
              {grouped['Older'].length > 0 && (
                <div className="py-1">
                  <p className="text-xs text-slate-400 font-medium px-1 pb-1">Older</p>
                  {grouped['Older'].map((item) => (
                    <button key={item.timestamp + (item.query || '').slice(0, 20)} type="button" onClick={() => onSelectHistory?.(item)} className="w-full text-left px-3 py-2 rounded-lg hover:bg-white flex items-center gap-2 text-slate-700 border border-transparent hover:border-slate-200 transition-all">
                      <svg className="w-4 h-4 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
                      <span className="truncate text-sm">{(item.query || '').substring(0, 26)}…</span>
                    </button>
                  ))}
                </div>
              )}
              {items.length === 0 && <p className="text-xs text-slate-400 px-3 py-4">No history yet.</p>}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
