export default function SourcesList({ messages }) {
  const lastBot = [...messages].reverse().find((m) => m.role === 'assistant' && m.sources?.length)
  const sources = lastBot?.sources ?? []

  return (
    <div className="sources-list">
      <h3 className="sources-title">Sources</h3>
      {sources.length === 0 ? (
        <p className="sources-empty">No sources for the latest reply.</p>
      ) : (
        <ul className="sources-ul">
          {sources.map((s, i) => (
            <li key={i} className="source-item">
              <a
                href={s.source?.startsWith('http') ? s.source : '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="source-item-link"
              >
                {s.title || s.source || `Source ${i + 1}`}
              </a>
              {s.type && <span className="source-type">{s.type}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
