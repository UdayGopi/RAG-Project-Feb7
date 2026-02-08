import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import { chat, feedback } from '../api'

const BOT_AVATAR = (
  <div className="flex-shrink-0 w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-blue-700 flex items-center justify-center shadow-md text-white text-sm font-semibold">
    AI
  </div>
)

const WELCOME_DATA = {
  is_welcome: true,
  detailed_response: "Hi, I'm your policy assistant. Use **Upload Docs** to add knowledge, then ask me anything. I'll answer with sources and key points.",
  summary: "Welcome to CarePolicy Hub.",
}

function TypingIndicator() {
  return (
    <div className="flex items-start gap-3 message-in">
      {BOT_AVATAR}
      <div className="rounded-2xl rounded-tl-md px-4 py-3 bg-slate-100 border border-slate-200/80 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="typing-dot w-2 h-2 bg-blue-500 rounded-full inline-block" />
          <span className="typing-dot w-2 h-2 bg-blue-500 rounded-full inline-block" />
          <span className="typing-dot w-2 h-2 bg-blue-500 rounded-full inline-block" />
          <span className="ml-2 text-sm font-medium text-slate-600">Thinking...</span>
        </div>
      </div>
    </div>
  )
}

function UserBubble({ text }) {
  return (
    <div className="flex justify-end message-in">
      <div className="max-w-[85%] sm:max-w-[75%] rounded-2xl rounded-br-md px-4 py-3 bg-blue-600 text-white shadow-md">
        <p className="text-sm leading-relaxed">{text}</p>
      </div>
    </div>
  )
}

function AiMessage({ data, originalQuery, onAsk }) {
  const [feedbackSent, setFeedbackSent] = useState(false)
  const [rephraseSuggestions, setRephraseSuggestions] = useState([])

  const handleFeedback = async (isHelpful) => {
    if (feedbackSent) return
    setFeedbackSent(true)
    try {
      const res = await feedback(originalQuery, isHelpful)
      if (!isHelpful && Array.isArray(res.suggestions) && res.suggestions.length > 0) {
        setRephraseSuggestions(res.suggestions.slice(0, 3))
      }
    } catch (_) {}
  }

  if (data.is_welcome || data.is_conversational) {
    return (
      <div className="flex items-start gap-3 message-in">
        {BOT_AVATAR}
        <div className="max-w-[85%] sm:max-w-2xl rounded-2xl rounded-tl-md px-4 py-3 bg-white border border-slate-200 shadow-sm">
          <p className="text-slate-700 text-sm leading-relaxed">{data.answer || data.detailed_response}</p>
        </div>
      </div>
    )
  }

  if (data.needs_tenant_selection) {
    const tenants = data.tenants || []
    return (
      <div className="flex items-start gap-3 message-in">
        {BOT_AVATAR}
        <div className="max-w-[85%] sm:max-w-2xl rounded-2xl rounded-tl-md px-4 py-3 bg-white border border-blue-200 shadow-sm">
          <p className="text-blue-800 font-semibold text-sm mb-3">
            Select a tenant for &quot;{data.original_query}&quot;:
          </p>
          <div className="flex flex-wrap gap-2">
            {tenants.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => onAsk(`${data.original_query} for ${t}`)}
                className="px-3 py-1.5 bg-blue-50 text-blue-700 text-xs font-medium rounded-lg hover:bg-blue-100 transition-colors"
              >
                {t}
              </button>
            ))}
            <button
              type="button"
              onClick={() => onAsk(`${data.original_query} [AUTO]`)}
              className="px-3 py-1.5 bg-slate-100 text-slate-600 text-xs font-medium rounded-lg hover:bg-slate-200 transition-colors"
            >
              Skip (Auto-Select)
            </button>
          </div>
        </div>
      </div>
    )
  }

  const hasCodes = Array.isArray(data.codes) && data.codes.length > 0
  const sources = (data.sources || []).slice(0, 5)
  const uniqSources = []
  const seen = new Set()
  for (const s of sources) {
    const key = (s.url || s.relative_path || s.filename || '').toLowerCase()
    if (!seen.has(key)) { seen.add(key); uniqSources.push(s) }
  }
  const maxScore = Math.max(...uniqSources.map((s) => (typeof s.relevance === 'number' ? s.relevance : 0)), 0)
  const API_BASE = import.meta.env.VITE_API_URL || ''

  return (
    <div className="flex items-start gap-3 message-in">
      {BOT_AVATAR}
      <div className="max-w-[85%] sm:max-w-2xl rounded-2xl rounded-tl-md px-4 py-3 bg-white border border-slate-200 shadow-sm space-y-3">
        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Summary</h4>
          <p className="text-slate-700 text-sm leading-relaxed">{data.summary || 'No summary available.'}</p>
        </div>

        <div>
          <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Detailed</h4>
          <div className="prose prose-sm text-slate-700 max-w-none">
            <ReactMarkdown>{data.detailed_response || ''}</ReactMarkdown>
          </div>
        </div>

        {Array.isArray(data.key_points) && data.key_points.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Key points</h4>
            <ul className="list-disc pl-4 space-y-0.5 text-slate-700 text-sm">
              {data.key_points.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {Array.isArray(data.suggestions) && data.suggestions.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Suggestions</h4>
            <ul className="list-disc pl-4 space-y-0.5 text-slate-700 text-sm">
              {data.suggestions.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {hasCodes && (
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Codes</h4>
            <ul className="list-disc pl-4 space-y-0.5 font-mono text-slate-800 text-sm">
              {data.codes.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </div>
        )}

        {uniqSources.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1">Sources</h4>
            <p className="text-xs text-slate-500 mb-1.5">Document or URL and exact page(s) the response was generated from.</p>
            <ul className="space-y-2 text-xs text-slate-700">
              {uniqSources.map((s, i) => {
                const raw = typeof s.relevance === 'number' ? s.relevance : 0
                const normPct = maxScore > 0 ? Math.round((raw / maxScore) * 100) : 0
                const hasUrl = !!s.url
                const pages = Array.isArray(s.pages) ? s.pages : (s.page != null ? [s.page] : [])
                const pageLabel = pages.length === 0 ? '' : pages.length === 1 ? `Page ${pages[0]}` : `Pages ${pages.sort((a, b) => Number(a) - Number(b)).join(', ')}`
                const firstPage = pages.length > 0 ? pages[0] : null
                const fname = String(s.filename || '')
                const pathParts = fname.replace(/\.tables\.txt$/, '').replace(/::tables$/, '').split(/[\\/]/)
                const baseName = pathParts[pathParts.length - 1] || fname
                const pathForUrl = s.relative_path || baseName
                const viewPageFrag = firstPage != null ? `#page=${encodeURIComponent(firstPage)}` : ''
                const viewHref = hasUrl ? s.url : `${API_BASE}/view/${data.selected_tenant || ''}/${encodeURIComponent(pathForUrl)}${viewPageFrag}`
                const viewLabel = hasUrl ? 'Open URL' : 'View'
                const downloadHref = `${API_BASE}/download/${data.selected_tenant || ''}/${encodeURIComponent(pathForUrl)}`
                const nameLower = (baseName || fname || '').toLowerCase()
                const isOnboardingForm = (nameLower.includes('rc') && nameLower.includes('onboarding')) || (nameLower.includes('hih') && nameLower.includes('onboarding'))
                const showDownload = isOnboardingForm
                const displaySource = hasUrl ? (() => {
                  try {
                    const u = new URL(s.url)
                    return u.hostname + (u.pathname !== '/' ? u.pathname.slice(0, 40) + (u.pathname.length > 40 ? '…' : '') : '')
                  } catch {
                    return s.url
                  }
                })() : baseName
                return (
                  <li key={i} className="flex justify-between items-center gap-2 bg-slate-50 px-2.5 py-2 rounded-lg border border-slate-100">
                    <div className="min-w-0 flex-1">
                      <span className="font-medium text-slate-800 block truncate" title={hasUrl ? s.url : baseName}>
                        {displaySource}
                      </span>
                      {pageLabel && <span className="text-slate-500 font-medium mt-0.5 block">→ {pageLabel}</span>}
                    </div>
                    <span className="flex items-center gap-1.5 flex-shrink-0">
                      <span className="font-mono text-blue-600 font-semibold text-xs">{normPct}%</span>
                      <a href={viewHref} target="_blank" rel="noopener noreferrer" className="px-2 py-0.5 rounded bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 whitespace-nowrap">
                        {viewLabel}
                      </a>
                      {showDownload && (
                        <a href={downloadHref} target="_blank" rel="noopener noreferrer" className="px-2 py-0.5 rounded bg-slate-600 text-white text-xs font-medium hover:bg-slate-700 whitespace-nowrap">
                          Download
                        </a>
                      )}
                    </span>
                  </li>
                )
              })}
            </ul>
          </div>
        )}

        {Array.isArray(data.follow_up_questions) && data.follow_up_questions.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">Follow-up</h4>
            <div className="flex flex-wrap gap-1.5">
              {data.follow_up_questions.map((q, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => onAsk(q)}
                  className="px-2.5 py-1.5 bg-slate-100 text-slate-700 text-xs font-medium rounded-lg hover:bg-blue-50 hover:text-blue-700 hover:border-blue-200 border border-transparent transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="pt-2 border-t border-slate-100 flex items-center gap-2 text-xs text-slate-500">
          {!feedbackSent ? (
            <>
              <span className="font-medium">Helpful?</span>
              <button type="button" onClick={() => handleFeedback(true)} className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors" aria-label="Yes">👍</button>
              <button type="button" onClick={() => handleFeedback(false)} className="p-1.5 rounded-lg hover:bg-slate-100 transition-colors" aria-label="No">👎</button>
            </>
          ) : (
            <span className="font-medium text-slate-600">Thanks for your feedback.</span>
          )}
        </div>

        {rephraseSuggestions.length > 0 && (
          <div className="p-2.5 bg-blue-50 border border-blue-100 rounded-xl">
            <h5 className="text-xs font-semibold text-blue-800 mb-1.5">Try rephrasing:</h5>
            <div className="flex flex-wrap gap-1.5">
              {rephraseSuggestions.map((q, i) => (
                <button key={i} type="button" onClick={() => onAsk(q)} className="px-2.5 py-1.5 bg-blue-100 text-blue-800 text-xs font-medium rounded-lg hover:bg-blue-200">
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ErrorBubble({ message }) {
  return (
    <div className="flex items-start gap-3 message-in">
      {BOT_AVATAR}
      <div className="max-w-[85%] sm:max-w-2xl rounded-2xl rounded-tl-md px-4 py-3 bg-red-50 border border-red-200">
        <p className="font-semibold text-red-800 text-sm mb-1">Error</p>
        <p className="text-red-700 text-sm">{message}</p>
      </div>
    </div>
  )
}

const SUGGESTED_CARDS = [
  { label: 'How can you help me?', icon: 'chat', query: 'How can you help me with my policy documents?' },
  { label: 'What topics can you assist with?', icon: 'chart', query: 'What topics and documents can you assist me with?' },
  { label: 'Tell me more about your capabilities', icon: 'sparkle', query: 'What are your capabilities for policy and document search?' },
  { label: 'Give a quick summary of my docs', icon: 'search', query: 'Give me a quick overview or summary of my ingested documents.' },
]

const SuggestedCardIcon = ({ name }) => {
  const cls = 'w-5 h-5 text-blue-600'
  if (name === 'chat') return <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
  if (name === 'chart') return <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
  if (name === 'sparkle') return <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" /></svg>
  if (name === 'search') return <svg className={cls} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
  return null
}

export default function ChatPanel({ messages, thinking, onSend }) {
  const chatEndRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const handleSubmit = (e) => {
    e.preventDefault()
    const ta = textareaRef.current
    if (!ta) return
    const q = ta.value.trim()
    if (!q) return
    onSend(q)
    ta.value = ''
    ta.style.height = 'auto'
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const showWelcome = messages.length === 0

  return (
    <div className="h-full flex flex-col min-h-0 bg-white">
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 space-y-5">
          {showWelcome && (
            <>
              <div className="text-center py-8">
                <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">
                  Hello! Welcome to <span className="text-blue-600">CarePolicy Hub</span>
                </h2>
                <p className="mt-2 text-slate-600 text-sm">Test and interact with your policy assistant in real-time.</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {SUGGESTED_CARDS.map((card, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => onSend(card.query)}
                    className="flex items-center gap-3 p-4 rounded-xl border border-slate-200 bg-white hover:border-blue-300 hover:bg-blue-50/50 shadow-sm hover:shadow-md transition-all text-left group"
                  >
                    <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0 group-hover:bg-blue-100 transition-colors">
                      <SuggestedCardIcon name={card.icon} />
                    </div>
                    <span className="flex-1 text-sm font-medium text-slate-800 truncate">{card.label}</span>
                    <svg className="w-4 h-4 text-slate-400 group-hover:text-blue-600 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" /></svg>
                  </button>
                ))}
              </div>
            </>
          )}
          {messages.map((m, i) => (
            <div key={i}>
              {m.role === 'user' && <UserBubble text={m.text} />}
              {m.role === 'assistant' && m.data && <AiMessage data={m.data} originalQuery={m.query || ''} onAsk={onSend} />}
              {m.role === 'error' && <ErrorBubble message={m.text} />}
            </div>
          ))}
          {thinking && <TypingIndicator />}
          <div ref={chatEndRef} />
        </div>
      </div>

      <div className="flex-shrink-0 border-t border-slate-200 bg-white px-4 sm:px-6 py-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex gap-3 items-end">
          <div className="flex-1 flex items-center gap-2 min-h-[48px] py-2 px-4 rounded-xl border border-slate-300 bg-slate-50/50 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500 transition-all">
            <button type="button" className="p-1.5 rounded-lg text-slate-400 hover:bg-slate-200/50 hover:text-slate-600" aria-label="Attach">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" /></svg>
            </button>
            <textarea
              ref={textareaRef}
              rows={1}
              placeholder="Ask a question..."
              onKeyDown={handleKeyDown}
              className="flex-1 min-h-[32px] max-h-[140px] bg-transparent text-slate-900 placeholder-slate-400 resize-none text-sm border-none focus:outline-none focus:ring-0"
            />
          </div>
          <button
            type="submit"
            disabled={thinking}
            className="flex-shrink-0 w-12 h-12 rounded-full bg-blue-600 text-white flex items-center justify-center hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed shadow-md hover:shadow-lg transition-all"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" /></svg>
          </button>
        </form>
      </div>
    </div>
  )
}
