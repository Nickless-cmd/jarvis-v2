import { useLayoutEffect, useRef } from 'react'
import { ArrowUp, LoaderCircle, Paperclip } from 'lucide-react'

export function Composer({ value, onChange, onSend, isStreaming }) {
  const textareaRef = useRef(null)

  useLayoutEffect(() => {
    const node = textareaRef.current
    if (!node) return
    node.style.height = '0px'
    node.style.height = `${Math.min(node.scrollHeight, 160)}px`
  }, [value])

  return (
    <section className="composer-shell">
      <div className="composer-wrap">
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
          placeholder="Message Jarvis…"
          rows={1}
        />
        <button
          className={isStreaming ? 'send-btn working' : 'send-btn'}
          onClick={onSend}
          disabled={isStreaming}
          title={isStreaming ? 'Jarvis is working' : 'Send message'}
        >
          {isStreaming ? <LoaderCircle size={16} className="spin" /> : <ArrowUp size={16} />}
        </button>
      </div>
    </section>
  )
}
