import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import { chat as apiChat, health, tenants } from '../api'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'
import SourcesList from './SourcesList'

export default function Chat({ onStatusChange }) {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [tenantList, setTenantList] = useState([])
  const [selectedTenant, setSelectedTenant] = useState('')
  const messagesEndRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    async function check() {
      try {
        const h = await health()
        onStatusChange?.('ok')
        const t = await tenants().catch(() => ({ tenants: [] }))
        if (!cancelled) setTenantList(t.tenants || [])
      } catch {
        if (!cancelled) onStatusChange?.('error')
      }
    }
    check()
    return () => { cancelled = true }
  }, [onStatusChange])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async (text) => {
    if (!text.trim() || loading) return
    const userMsg = { role: 'user', content: text.trim(), sources: [] }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)
    try {
      const res = await apiChat(text.trim(), selectedTenant || null)
      const summary = res.summary ?? ''
      const detailed = res.detailed_response ?? res.summary ?? ''
      const sources = Array.isArray(res.sources) ? res.sources : []
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: detailed,
          summary,
          sources,
          confidence: res.confidence,
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Error: ${err.message}`,
          sources: [],
          error: true,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-layout">
      <div className="chat-panel">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="empty-state">
              <p className="empty-title">Start a conversation</p>
              <p className="empty-sub">Ask about policies, procedures, or upload documents to query.</p>
              {tenantList.length > 0 && (
                <div className="tenant-select-wrap">
                  <label>Tenant</label>
                  <select
                    value={selectedTenant}
                    onChange={(e) => setSelectedTenant(e.target.value)}
                    className="tenant-select"
                  >
                    <option value="">Auto</option>
                    {tenantList.map((t) => (
                      <option key={t} value={t}>{t}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>
          )}
          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}
          {loading && (
            <div className="message bot typing-wrap">
              <div className="typing-dots">
                <span /><span /><span />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <ChatInput onSend={handleSend} disabled={loading} />
      </div>
      <aside className="sources-panel">
        <SourcesList messages={messages} />
      </aside>
    </div>
  )
}
