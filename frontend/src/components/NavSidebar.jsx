const navItems = [
  { id: 'analytics', label: 'Dashboard', icon: 'analytics' },
  { id: 'upload', label: 'Knowledge Base', icon: 'knowledge' },
  { id: 'scheduler', label: 'Scheduler', icon: 'scheduler' },
  { id: 'profile', label: 'My Profile', icon: 'profile' },
]

const Icon = ({ name, className = 'w-5 h-5' }) => {
  const c = className
  if (name === 'knowledge') return <svg className={c} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" /></svg>
  if (name === 'analytics') return <svg className={c} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
  if (name === 'scheduler') return <svg className={c} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
  if (name === 'profile') return <svg className={c} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
  return null
}

export default function NavSidebar({ activePanel, onSelectPanel, user, collapsed, onToggleCollapse }) {
  return (
    <aside className={`h-full flex flex-col bg-white border-r border-slate-200 transition-all duration-200 ${collapsed ? 'w-[72px]' : 'w-56'}`}>
      <div className="flex-shrink-0 p-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-600 to-blue-700 flex items-center justify-center shadow-md flex-shrink-0">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white">
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          {!collapsed && <span className="font-bold text-slate-900 text-lg tracking-tight truncate">CarePolicy Hub</span>}
        </div>
      </div>

      <nav className="flex-1 py-4 px-3 min-h-0 overflow-y-auto scrollbar-thin">
        {navItems.map((item) => {
          const isActive = activePanel === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelectPanel(item.id)}
              className={`w-full flex items-center gap-3 rounded-xl py-2.5 px-3 mb-1 transition-all ${
                isActive ? 'bg-blue-600 text-white shadow-md' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`}
            >
              <Icon name={item.icon} className="w-5 h-5 flex-shrink-0" />
              {!collapsed && <span className="font-medium text-sm truncate">{item.label}</span>}
            </button>
          )
        })}
      </nav>

      <div className="flex-shrink-0 p-3 border-t border-slate-100">
        <button
          type="button"
          onClick={() => onSelectPanel('profile')}
          className={`w-full flex items-center gap-2 p-2 rounded-xl transition-all ${
            activePanel === 'profile' ? 'bg-blue-50 border border-blue-200' : 'hover:bg-slate-50'
          }`}
        >
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-600 to-blue-700 text-white flex items-center justify-center text-sm font-semibold flex-shrink-0">
            {(user?.name || user?.email || 'U').charAt(0).toUpperCase()}
          </div>
          {!collapsed && (
            <div className="flex-1 text-left min-w-0">
              <p className="text-xs font-semibold text-slate-900 truncate">{user?.name || user?.email?.split('@')[0] || 'User'}</p>
              <p className="text-xs text-slate-500 truncate">View Profile</p>
            </div>
          )}
        </button>
        <button type="button" onClick={onToggleCollapse} className="w-full mt-2 p-1.5 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-600 flex items-center justify-center" aria-label={collapsed ? 'Expand' : 'Collapse'}>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={collapsed ? "M9 5l7 7-7 7" : "M15 19l-7-7 7-7"} /></svg>
        </button>
      </div>
    </aside>
  )
}
