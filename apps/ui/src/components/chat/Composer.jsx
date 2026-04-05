import { useLayoutEffect, useRef } from 'react'
import { ArrowUp, Square, Paperclip } from 'lucide-react'

export function Composer({ value, onChange, onSend, onCancel, isStreaming }) {
  const textareaRef = useRef(null)
  const canSend = Boolean(value.trim()) && !isStreaming

  useLayoutEffect(() => {
    const node = textareaRef.current
    if (!node) return
    node.style.height = '0px'
    node.style.height = `${Math.min(node.scrollHeight, 160)}px`
  }, [value])

  return (
    <section className="composer-shell">
      <div className={isStreaming ? 'composer-wrap working' : 'composer-wrap'}>
        <button className="icon-btn subtle composer-attach-btn" type="button" title="Attach">
          <Paperclip size={16} />
        </button>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              onSend()
            }
          }}
          placeholder={isStreaming ? 'Jarvis is responding…' : 'Message Jarvis…'}
          rows={1}
        />
        {isStreaming ? (
          <button
            className="send-btn cancel"
            onClick={onCancel}
            title="Stop generating"
          >
            <Square size={14} />
          </button>
        ) : (
          <button
            className="send-btn"
            onClick={onSend}
            disabled={!canSend}
            title={canSend ? 'Send message' : 'Write a message first'}
          >
            <ArrowUp size={16} />
          </button>
        )}
      </div>
    </section>
  )
}
