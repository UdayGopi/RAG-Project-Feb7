import ReactMarkdown from 'react-markdown'

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`message ${isUser ? 'user' : 'bot'} ${message.error ? 'error' : ''}`}>
      <div className="message-avatar">
        {isUser ? 'You' : '◇'}
      </div>
      <div className="message-body">
        <div className="msg-content">
          {isUser ? (
            message.content
          ) : (
            <ReactMarkdown>{message.content}</ReactMarkdown>
          )}
        </div>
        {!isUser && message.sources?.length > 0 && (
          <div className="message-sources-inline">
            <span className="sources-label">Sources:</span>
            {message.sources.slice(0, 3).map((s, i) => (
              <a
                key={i}
                href={s.source?.startsWith('http') ? s.source : '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="source-link"
              >
                {typeof s.source === 'string' && s.source.length > 60
                  ? s.source.slice(0, 57) + '...'
                  : s.source || 'Source'}
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
