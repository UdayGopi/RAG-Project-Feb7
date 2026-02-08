import { useState } from 'react'

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!value.trim() || disabled) return
    onSend(value.trim())
    setValue('')
  }

  return (
    <form className="chat-input-wrap" onSubmit={handleSubmit}>
      <textarea
        className="chat-input"
        placeholder="Ask about policies or procedures..."
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit(e)
          }
        }}
        rows={1}
        disabled={disabled}
      />
      <button type="submit" className="send-btn" disabled={disabled || !value.trim()}>
        Send
      </button>
    </form>
  )
}
