import { useState, useCallback, useEffect } from 'react'
import { chat, API_BASE, me } from './api'
import Landing from './components/Landing'
import NavSidebar from './components/NavSidebar'
import Dashboard from './components/Dashboard'
import ChatHistoryStrip from './components/ChatHistoryStrip'
import ChatPanel from './components/ChatPanel'
import UploadPanel from './components/UploadPanel'
import AnalyticsPanel from './components/AnalyticsPanel'
import SchedulerPanel from './components/SchedulerPanel'
import UserProfile from './components/UserProfile'
import './index.css'

const PANEL_TITLES = {
  analytics: { title: 'Dashboard', subtitle: 'Analytics and insights for your CarePolicy Hub.' },
  upload: { title: 'Knowledge Base', subtitle: 'Upload and ingest documents for your assistant.' },
  scheduler: { title: 'Scheduler', subtitle: 'Schedule URL ingestion and recurring updates.' },
  profile: { title: 'My Profile', subtitle: 'Manage your account and preferences.' },
}

export default function App() {
  const [authUser, setAuthUser] = useState(undefined)
  const [activePanel, setActivePanel] = useState('analytics')
  const [messages, setMessages] = useState([])
  const [thinking, setThinking] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [navCollapsed, setNavCollapsed] = useState(false)
  const [chatSidebarOpen, setChatSidebarOpen] = useState(false)
  const [chatFullscreen, setChatFullscreen] = useState(false)
  const [historyRefresh, setHistoryRefresh] = useState(0)

  useEffect(() => {
    me()
      .then((user) => setAuthUser(user || null))
      .catch(() => setAuthUser(null))
  }, [])

  const handleNewChat = useCallback(() => {
    setMessages([])
    setHistoryRefresh((n) => n + 1)
  }, [])

  const handleSelectHistory = useCallback((item) => {
    setMessages([
      { role: 'user', text: item.query },
      { role: 'assistant', data: item.response || {}, query: item.query },
    ])
    setChatSidebarOpen(true)
  }, [])

  const handleSend = useCallback(async (query) => {
    setMessages((prev) => [...prev, { role: 'user', text: query }])
    setThinking(true)
    try {
      const data = await chat(query)
      setMessages((prev) => [...prev, { role: 'assistant', data, query }])
      setHistoryRefresh((n) => n + 1)
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'error', text: err.message }])
    } finally {
      setThinking(false)
    }
  }, [])

  const handleSignOut = () => {
    try {
      fetch(`${API_BASE}/auth/signout`, { method: 'POST', credentials: 'include' }).finally(() => {
        setAuthUser(null)
        setMessages([])
        setActivePanel('analytics')
        setChatSidebarOpen(false)
      })
    } catch {
      setAuthUser(null)
    }
  }

  const handleOpenChat = () => {
    setChatFullscreen(true)
  }

  if (authUser === undefined) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-dash-bg">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-600">Loading...</p>
        </div>
      </div>
    )
  }

  if (!authUser) {
    return <Landing />
  }

  const panelInfo = PANEL_TITLES[activePanel] || PANEL_TITLES.analytics

  return (
    <div className="h-screen w-full flex flex-col bg-dash-bg overflow-hidden">
      {sidebarOpen && (
        <button
          type="button"
          aria-label="Close sidebar"
          className="md:hidden fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {chatFullscreen && (
        <div className="fixed inset-0 z-50 bg-slate-900/95 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full h-full max-w-7xl bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-slate-200 bg-slate-50">
              <h2 className="text-lg font-bold text-slate-900 font-heading">Chat Assistant - Fullscreen</h2>
              <button
                onClick={() => setChatFullscreen(false)}
                className="p-2 rounded-lg hover:bg-slate-200 transition-colors"
              >
                <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="flex-1 flex overflow-hidden">
              <div className="w-72 border-r border-slate-200">
                <ChatHistoryStrip onNewChat={handleNewChat} onSelectHistory={handleSelectHistory} refreshTrigger={historyRefresh} />
              </div>
              <div className="flex-1">
                <ChatPanel messages={messages} thinking={thinking} onSend={handleSend} />
              </div>
            </div>
          </div>
        </div>
      )}

      <main className="flex-1 flex min-h-0 w-full">
        <div className={`${sidebarOpen ? 'flex' : 'hidden'} flex-shrink-0 z-50 md:z-auto md:relative absolute inset-y-0 left-0 h-full md:relative`}>
          <NavSidebar
            activePanel={activePanel}
            onSelectPanel={setActivePanel}
            user={authUser}
            collapsed={navCollapsed}
            onToggleCollapse={() => setNavCollapsed((c) => !c)}
            onOpenChat={handleOpenChat}
          />
        </div>

        <div className="flex-1 flex min-w-0 min-h-0 relative">
          <div className="flex flex-col min-w-0 flex-1">
            {/* Small header for Open Chat and User name */}
            <div className="flex-shrink-0 bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
              <div>
                <h1 className="text-lg font-bold text-slate-900 font-heading">{panelInfo.title}</h1>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setChatFullscreen(true)}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 text-white text-sm font-semibold shadow-md hover:shadow-lg hover:from-blue-700 hover:to-blue-800 transition-all"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                  <span>Open Chat</span>
                </button>
                <button
                  onClick={() => setActivePanel('profile')}
                  className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-50 border border-slate-200 hover:bg-slate-100 transition-all"
                >
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-blue-600 to-blue-700 text-white flex items-center justify-center text-xs font-semibold">
                    {(authUser?.name || authUser?.email || 'U').charAt(0).toUpperCase()}
                  </div>
                  <span className="text-sm font-medium text-slate-700">{authUser?.name || authUser?.email?.split('@')[0] || 'User'}</span>
                </button>
              </div>
            </div>

            <div className="flex-1 flex flex-col p-0 min-h-0">
              {activePanel === 'upload' && (
                <div className="flex-1 overflow-y-auto h-full">
                  <UploadPanel />
                </div>
              )}
              {activePanel === 'analytics' && (
                <div className="flex-1 overflow-y-auto h-full">
                  <AnalyticsPanel />
                </div>
              )}
              {activePanel === 'scheduler' && (
                <div className="flex-1 overflow-y-auto h-full">
                  <SchedulerPanel />
                </div>
              )}
              {activePanel === 'profile' && (
                <div className="flex-1 overflow-y-auto h-full">
                  <UserProfile user={authUser} onSignOut={handleSignOut} />
                </div>
              )}
            </div>
          </div>

          {/* Mobile menu button */}
          <button
            onClick={() => setSidebarOpen((o) => !o)}
            className="md:hidden fixed top-6 left-6 z-40 p-3 rounded-xl border border-slate-200 bg-white shadow-lg hover:bg-slate-50 transition-all"
            aria-label="Menu"
          >
            <svg className="w-6 h-6 text-slate-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>



        </div>
      </main>
    </div>
  )
}
