export default function Dashboard({ user }) {
  return (
    <div className="p-6 md:p-8 h-full overflow-y-auto bg-gradient-to-br from-slate-50 to-blue-50/30">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Welcome Section */}
        <div className="glass-card rounded-2xl p-8 border border-slate-200">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-600 to-blue-700 flex items-center justify-center shadow-lg flex-shrink-0">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <div className="flex-1">
              <h1 className="text-3xl font-bold text-slate-900 font-heading">
                Welcome back, {user?.name || user?.email?.split('@')[0] || 'User'}! 👋
              </h1>
              <p className="text-slate-600 mt-2">Ready to explore your policy knowledge base and get instant answers.</p>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="glass-card rounded-xl p-6 border border-slate-200">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <div>
                <p className="text-sm text-slate-600 font-medium">Chat Assistant</p>
                <p className="text-2xl font-bold text-slate-900">Ready</p>
              </div>
            </div>
          </div>

          <div className="glass-card rounded-xl p-6 border border-slate-200">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <p className="text-sm text-slate-600 font-medium">Knowledge Base</p>
                <p className="text-2xl font-bold text-slate-900">Active</p>
              </div>
            </div>
          </div>

          <div className="glass-card rounded-xl p-6 border border-slate-200">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-green-500 to-green-600 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div>
                <p className="text-sm text-slate-600 font-medium">System Status</p>
                <p className="text-2xl font-bold text-slate-900">Online</p>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="glass-card rounded-2xl p-6 border border-slate-200">
          <h2 className="text-xl font-bold text-slate-900 font-heading mb-4 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-blue-600" />
            Quick Actions
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button className="group p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50/50 transition-all text-left">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-100 group-hover:bg-blue-200 flex items-center justify-center transition-colors">
                  <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                </div>
                <div>
                  <p className="font-semibold text-slate-900">Start New Chat</p>
                  <p className="text-xs text-slate-600">Ask questions about policies</p>
                </div>
              </div>
            </button>

            <button className="group p-4 rounded-xl border border-slate-200 bg-white hover:border-purple-300 hover:bg-purple-50/50 transition-all text-left">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-purple-100 group-hover:bg-purple-200 flex items-center justify-center transition-colors">
                  <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <div>
                  <p className="font-semibold text-slate-900">Upload Documents</p>
                  <p className="text-xs text-slate-600">Add to knowledge base</p>
                </div>
              </div>
            </button>

            <button className="group p-4 rounded-xl border border-slate-200 bg-white hover:border-cyan-300 hover:bg-cyan-50/50 transition-all text-left">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-cyan-100 group-hover:bg-cyan-200 flex items-center justify-center transition-colors">
                  <svg className="w-5 h-5 text-cyan-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <div>
                  <p className="font-semibold text-slate-900">View Analytics</p>
                  <p className="text-xs text-slate-600">Track usage and insights</p>
                </div>
              </div>
            </button>

            <button className="group p-4 rounded-xl border border-slate-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/50 transition-all text-left">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-indigo-100 group-hover:bg-indigo-200 flex items-center justify-center transition-colors">
                  <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <p className="font-semibold text-slate-900">Schedule Tasks</p>
                  <p className="text-xs text-slate-600">Automate ingestion</p>
                </div>
              </div>
            </button>
          </div>
        </div>

        {/* Getting Started */}
        <div className="glass-card rounded-2xl p-6 border border-slate-200">
          <h2 className="text-xl font-bold text-slate-900 font-heading mb-4 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-600" />
            Getting Started
          </h2>
          <div className="space-y-3">
            <div className="flex items-start gap-3 p-3 rounded-lg bg-white border border-slate-100">
              <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                <svg className="w-3 h-3 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </div>
              <div>
                <p className="font-semibold text-slate-900">Sign In Complete</p>
                <p className="text-sm text-slate-600">You're logged in and ready to go</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-white border border-slate-100">
              <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-bold text-blue-600">2</span>
              </div>
              <div>
                <p className="font-semibold text-slate-900">Start Chatting</p>
                <p className="text-sm text-slate-600">Click the chat button in the sidebar to begin asking questions</p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-3 rounded-lg bg-white border border-slate-100">
              <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                <span className="text-xs font-bold text-blue-600">3</span>
              </div>
              <div>
                <p className="font-semibold text-slate-900">Upload Documents</p>
                <p className="text-sm text-slate-600">Go to Knowledge Base to add your policy documents</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
