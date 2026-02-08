import { API_BASE } from '../api'

const features = [
  { title: 'AI Policy Chat', desc: 'Ask in plain language. Get answers with sources and exact pages.', icon: '💬', gradient: 'from-blue-500 to-blue-600' },
  { title: 'Admin Analytics Dashboard', desc: 'Multi-chart analytics with real-time stats, trends, and tenant insights.', icon: '📊', gradient: 'from-purple-500 to-blue-600' },
  { title: 'Document Ingestion', desc: 'Upload PDFs, DOCX, or ingest from URLs. Organize by tenant.', icon: '📤', gradient: 'from-cyan-500 to-blue-500' },
  { title: 'Scheduled Ingestion', desc: 'Automate URL ingestion on a schedule with cron support.', icon: '🕐', gradient: 'from-blue-600 to-indigo-600' },
  { title: 'Chat History', desc: 'Filter by date, resume threads, full context tracking.', icon: '📋', gradient: 'from-sky-500 to-blue-500' },
  { title: 'Enterprise Security', desc: 'OAuth 2.0, tenant isolation, audit logs, and compliance ready.', icon: '🛡️', gradient: 'from-blue-700 to-indigo-700' },
]

const useCases = [
  { title: 'Compliance teams', body: 'Keep policies searchable and cited for audits.', icon: '✅' },
  { title: 'Policy writers', body: 'Find existing guidance and avoid duplication.', icon: '✍️' },
  { title: 'Support & ops', body: 'Answer internal questions with sources.', icon: '💼' },
]

export default function Landing() {
  const signInUrl = `${API_BASE || ''}/auth.html`

  return (
    <div className="min-h-screen flex flex-col bg-dash-bg">
      {/* Nav - modern glassmorphism */}
      <header className="sticky top-0 z-50 border-b border-slate-200/50 bg-white/80 backdrop-blur-xl shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-600 via-blue-600 to-blue-700 rounded-xl flex items-center justify-center shadow-lg hover:shadow-blue-500/30 transition-shadow">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-white">
                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <span className="text-xl font-bold text-slate-900 tracking-tight font-heading">CarePolicy Hub</span>
          </div>
          <nav className="flex items-center gap-6">
            <a href="#features" className="text-sm font-semibold text-slate-600 hover:text-blue-600 transition-colors hidden sm:inline">Features</a>
            <a href="#how" className="text-sm font-semibold text-slate-600 hover:text-blue-600 transition-colors hidden sm:inline">How it works</a>
            <a href={signInUrl} className="inline-flex items-center px-6 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 text-white text-sm font-bold shadow-lg shadow-blue-500/30 hover:shadow-blue-500/40 hover:from-blue-700 hover:to-blue-800 transition-all transform hover:scale-105">
              Sign In
            </a>
          </nav>
        </div>
      </header>

      {/* Hero - modern card with animations and dashboard preview */}
      <section className="px-4 sm:px-6 lg:px-8 py-12 sm:py-20">
        <div className="max-w-7xl mx-auto">
          <div className="relative rounded-3xl border border-slate-200/80 bg-white/90 backdrop-blur-sm shadow-2xl overflow-hidden group hover:shadow-blue-500/10 transition-shadow duration-500">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-50/40 via-white to-slate-50/40 opacity-60" />
            <div className="absolute top-0 right-0 w-64 h-64 bg-blue-400/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-purple-400/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2" />
            
            <div className="relative p-8 sm:p-12 lg:p-16">
              {/* Text content */}
              <div className="text-center mb-12">
                <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-slate-900 tracking-tight font-heading leading-tight animate-fade-in">
                  Your policy knowledge, <span className="bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">powered by AI</span>
                </h1>
                <p className="mt-6 text-lg sm:text-xl text-slate-600 max-w-3xl mx-auto leading-relaxed">
                  Ingest documents, ask questions in plain language, and get accurate answers with sources and exact pages. Built for enterprise compliance and policy teams.
                </p>
                <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
                  <a href={signInUrl} className="w-full sm:w-auto group inline-flex items-center justify-center gap-2 px-8 py-4 rounded-xl bg-gradient-to-r from-blue-600 to-blue-700 text-white text-base font-bold shadow-xl shadow-blue-500/25 hover:shadow-2xl hover:shadow-blue-500/30 hover:from-blue-700 hover:to-blue-800 transition-all transform hover:scale-105">
                    Get Started
                    <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>
                  </a>
                  <a href="#features" className="w-full sm:w-auto inline-flex items-center justify-center px-8 py-4 rounded-xl border-2 border-slate-300 text-slate-700 font-bold hover:border-blue-500 hover:text-blue-600 hover:bg-blue-50/50 bg-white/80 backdrop-blur-sm transition-all transform hover:scale-105">
                    See Features
                  </a>
                </div>
              </div>

              {/* Dashboard Preview Image/Mockup */}
              <div className="relative mx-auto max-w-5xl">
                <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 blur-3xl transform scale-95" />
                <div className="relative rounded-2xl border-2 border-slate-300/50 bg-white/95 backdrop-blur-xl shadow-2xl overflow-hidden transform hover:scale-[1.02] transition-transform duration-500">
                  {/* Browser chrome */}
                  <div className="bg-slate-100 border-b border-slate-300 px-4 py-3 flex items-center gap-2">
                    <div className="flex gap-1.5">
                      <div className="w-3 h-3 rounded-full bg-red-400" />
                      <div className="w-3 h-3 rounded-full bg-yellow-400" />
                      <div className="w-3 h-3 rounded-full bg-green-400" />
                    </div>
                    <div className="flex-1 mx-4 px-4 py-1.5 bg-white rounded-lg border border-slate-200 text-xs text-slate-500 flex items-center gap-2">
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" /></svg>
                      carepolicy-hub.com
                    </div>
                  </div>
                  
                  {/* Dashboard mockup */}
                  <div className="bg-gradient-to-br from-slate-50 to-blue-50/30 p-6">
                    {/* Header */}
                    <div className="bg-white/80 backdrop-blur-sm rounded-xl border border-slate-200 p-4 mb-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-600 to-blue-700 flex items-center justify-center">
                          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>
                        </div>
                        <div>
                          <div className="text-sm font-bold text-slate-900">AI Assistant Dashboard</div>
                          <div className="text-xs text-slate-500">Enterprise Admin Panel</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                        <span className="text-xs font-semibold text-green-700">Live</span>
                      </div>
                    </div>

                    {/* Stats cards row */}
                    <div className="grid grid-cols-4 gap-3 mb-4">
                      {[
                        { label: 'Queries', value: '2.4K', color: 'blue' },
                        { label: 'Tenants', value: '12', color: 'purple' },
                        { label: 'Docs', value: '487', color: 'cyan' },
                        { label: 'Uptime', value: '99.9%', color: 'green' },
                      ].map((stat, i) => (
                        <div key={i} className="bg-white/90 rounded-lg border border-slate-200 p-3">
                          <div className={`text-xs font-medium text-${stat.color}-600 mb-1`}>{stat.label}</div>
                          <div className="text-lg font-bold text-slate-900">{stat.value}</div>
                        </div>
                      ))}
                    </div>

                    {/* Charts grid */}
                    <div className="grid grid-cols-2 gap-3">
                      {/* Chart 1 - bars */}
                      <div className="bg-white/90 rounded-lg border border-slate-200 p-4">
                        <div className="text-xs font-semibold text-slate-700 mb-3">Query Analytics</div>
                        <div className="flex items-end justify-between gap-1 h-24">
                          {[40, 65, 45, 80, 55, 70].map((h, i) => (
                            <div key={i} className="flex-1 bg-gradient-to-t from-blue-600 to-blue-400 rounded-t" style={{ height: `${h}%` }} />
                          ))}
                        </div>
                      </div>
                      {/* Chart 2 - donut */}
                      <div className="bg-white/90 rounded-lg border border-slate-200 p-4">
                        <div className="text-xs font-semibold text-slate-700 mb-3">Distribution</div>
                        <div className="flex items-center justify-center h-24">
                          <svg className="w-20 h-20" viewBox="0 0 100 100">
                            <circle cx="50" cy="50" r="40" fill="none" stroke="#e2e8f0" strokeWidth="12" />
                            <circle cx="50" cy="50" r="40" fill="none" stroke="#2563eb" strokeWidth="12" strokeDasharray="180 251.2" strokeDashoffset="0" transform="rotate(-90 50 50)" />
                            <circle cx="50" cy="50" r="40" fill="none" stroke="#8b5cf6" strokeWidth="12" strokeDasharray="50 251.2" strokeDashoffset="-180" transform="rotate(-90 50 50)" />
                          </svg>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features - modern elevated cards */}
      <section id="features" className="px-4 sm:px-6 lg:px-8 py-16">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 font-heading">Everything you need</h2>
            <p className="mt-3 text-lg text-slate-600 max-w-2xl mx-auto">Complete platform for enterprise policy and compliance management</p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <div key={i} className="group relative rounded-2xl border border-slate-200 bg-white p-6 shadow-lg hover:shadow-2xl hover:shadow-blue-500/10 hover:border-blue-300 transition-all duration-300 transform hover:-translate-y-1">
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${f.gradient} text-white flex items-center justify-center mb-5 shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                  <span className="text-2xl">{f.icon}</span>
                </div>
                <h3 className="text-lg font-bold text-slate-900 font-heading mb-2">{f.title}</h3>
                <p className="text-slate-600 text-sm leading-relaxed">{f.desc}</p>
                <div className="absolute top-4 right-4 w-20 h-20 bg-gradient-to-br from-blue-400/5 to-purple-400/5 rounded-full blur-2xl group-hover:from-blue-400/10 group-hover:to-purple-400/10 transition-all" />
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Use cases - modern card row */}
      <section className="px-4 sm:px-6 lg:px-8 py-16">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-slate-900 font-heading">Who it's for</h2>
            <p className="mt-2 text-slate-600">Trusted by leading teams</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {useCases.map((uc, i) => (
              <div key={i} className="relative rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-lg hover:shadow-xl hover:border-blue-200 transition-all group">
                <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-100 to-blue-200 flex items-center justify-center mx-auto mb-4 text-3xl group-hover:scale-110 transition-transform">
                  {uc.icon}
                </div>
                <h3 className="font-bold text-slate-900 text-lg font-heading mb-2">{uc.title}</h3>
                <p className="text-slate-600 text-sm leading-relaxed">{uc.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works - elevated cards with icons */}
      <section id="how" className="px-4 sm:px-6 lg:px-8 py-16 bg-white/60 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 font-heading">How it works</h2>
            <p className="mt-2 text-slate-600">Get started in three simple steps</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="relative rounded-3xl border border-slate-200 bg-white p-12 shadow-xl text-center group hover:shadow-2xl hover:border-blue-300 transition-all transform hover:-translate-y-1">
              <div className="absolute top-8 right-8">
                <svg className="w-16 h-16 text-slate-100" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <div className="relative">
                <div className="w-20 h-20 rounded-full bg-white border-4 border-slate-100 flex items-center justify-center mx-auto mb-6">
                  <svg className="w-10 h-10 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                  </svg>
                </div>
                <h3 className="font-bold text-slate-900 text-2xl font-heading mb-3">Upload or ingest</h3>
                <p className="text-slate-600 leading-relaxed">Add PDFs, DOCX, or URLs. Organize by tenant.</p>
              </div>
            </div>

            <div className="relative rounded-3xl border border-slate-200 bg-white p-12 shadow-xl text-center group hover:shadow-2xl hover:border-blue-300 transition-all transform hover:-translate-y-1">
              <div className="absolute top-8 right-8">
                <svg className="w-16 h-16 text-slate-100" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <div className="relative">
                <div className="w-20 h-20 rounded-full bg-white border-4 border-slate-100 flex items-center justify-center mx-auto mb-6">
                  <svg className="w-10 h-10 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                </div>
                <h3 className="font-bold text-slate-900 text-2xl font-heading mb-3">Ask anything</h3>
                <p className="text-slate-600 leading-relaxed">Chat in natural language. Get answers with sources and pages.</p>
              </div>
            </div>

            <div className="relative rounded-3xl border border-slate-200 bg-white p-12 shadow-xl text-center group hover:shadow-2xl hover:border-blue-300 transition-all transform hover:-translate-y-1">
              <div className="absolute top-8 right-8">
                <svg className="w-16 h-16 text-slate-100" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <div className="relative">
                <div className="w-20 h-20 rounded-full bg-white border-4 border-slate-100 flex items-center justify-center mx-auto mb-6">
                  <svg className="w-10 h-10 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <h3 className="font-bold text-slate-900 text-2xl font-heading mb-3">Scale with analytics</h3>
                <p className="text-slate-600 leading-relaxed">Track usage, schedule ingestion, stay current.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Live Chatbot Preview */}
      <section className="px-4 sm:px-6 lg:px-8 py-16">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900 font-heading">Try it live</h2>
            <p className="mt-2 text-slate-600">Experience the power of AI-driven policy assistance</p>
          </div>
          <div className="relative rounded-3xl border-2 border-slate-200 bg-white shadow-2xl overflow-hidden max-w-4xl mx-auto">
            {/* Chat Header */}
            <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-6 py-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-white/20 backdrop-blur-sm flex items-center justify-center">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-white font-bold">CarePolicy Assistant</h3>
                  <p className="text-blue-100 text-xs">AI-powered policy expert</p>
                </div>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/20 backdrop-blur-sm">
                <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                <span className="text-white text-xs font-semibold">Online</span>
              </div>
            </div>

            {/* Chat Messages */}
            <div className="p-6 space-y-4 bg-gradient-to-br from-slate-50 to-blue-50/30 min-h-[400px]">
              {/* User message */}
              <div className="flex justify-end">
                <div className="max-w-[80%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-md">
                  <p className="text-sm">What is the policy for remote work?</p>
                </div>
              </div>

              {/* AI response */}
              <div className="flex justify-start">
                <div className="max-w-[85%] bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-md border border-slate-200">
                  <p className="text-sm text-slate-800 mb-3">Based on our remote work policy documents, employees can work remotely up to 3 days per week with manager approval. Full-time remote work requires VP approval.</p>
                  <div className="mt-3 pt-3 border-t border-slate-100">
                    <p className="text-xs text-slate-500 font-semibold mb-2">Sources:</p>
                    <div className="flex flex-wrap gap-2">
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded-lg text-xs">
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M9 2a2 2 0 00-2 2v8a2 2 0 002 2h6a2 2 0 002-2V6.414A2 2 0 0016.414 5L14 2.586A2 2 0 0012.586 2H9z" /></svg>
                        HR Policy • Page 12
                      </span>
                      <span className="inline-flex items-center gap-1 px-2 py-1 bg-purple-50 text-purple-700 rounded-lg text-xs">
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20"><path d="M9 2a2 2 0 00-2 2v8a2 2 0 002 2h6a2 2 0 002-2V6.414A2 2 0 0016.414 5L14 2.586A2 2 0 0012.586 2H9z" /></svg>
                        Work Guidelines • Page 5
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Input box (disabled) */}
              <div className="pt-4">
                <div className="flex gap-2 items-center px-4 py-3 bg-white border-2 border-slate-200 rounded-2xl">
                  <input 
                    type="text" 
                    placeholder="Sign in to start chatting..."
                    disabled
                    className="flex-1 outline-none text-sm text-slate-400 bg-transparent"
                  />
                  <button disabled className="p-2 rounded-xl bg-slate-100 text-slate-400">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA - modern gradient card */}
      <section className="px-4 sm:px-6 lg:px-8 py-16">
        <div className="max-w-4xl mx-auto">
          <div className="relative rounded-3xl bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-700 p-12 sm:p-16 text-center shadow-2xl overflow-hidden group">
            <div className="absolute inset-0 bg-gradient-to-br from-blue-400/20 via-transparent to-purple-400/20" />
            <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full blur-3xl" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-purple-300/10 rounded-full blur-3xl" />
            <div className="relative">
              <h2 className="text-3xl sm:text-4xl font-bold text-white font-heading">Ready to transform your policy workflow?</h2>
              <p className="mt-4 text-blue-100 text-lg max-w-2xl mx-auto">
                Join enterprise teams using CarePolicy Hub for AI-powered policy assistance.
              </p>
              <a href={signInUrl} className="mt-8 inline-flex items-center justify-center gap-2 px-10 py-4 rounded-xl bg-white text-blue-600 font-bold shadow-2xl hover:bg-blue-50 transition-all transform hover:scale-105 group">
                Sign In to CarePolicy Hub
                <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" /></svg>
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Footer - modern */}
      <footer className="border-t border-slate-200 bg-white/90 backdrop-blur-sm px-4 sm:px-6 lg:px-8 py-10 mt-auto">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl flex items-center justify-center shadow-md">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-white">
                  <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div>
                <span className="font-bold text-slate-900 font-heading block">CarePolicy Hub</span>
                <span className="text-xs text-slate-500">AI Policy Assistant</span>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row items-center gap-4 text-sm text-slate-500">
              <span>© 2024 CarePolicy Hub</span>
              <span className="hidden sm:inline">•</span>
              <span>Enterprise compliance & policy management</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
