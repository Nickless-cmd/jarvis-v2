# Webchat UI Enhancements — Design Spec

## Overview

Five targeted improvements to the Jarvis webchat interface:

1. **Copy button on code blocks** — floating icon top-right, semi-transparent, appears on hover
2. **Max-height + scroll on long code blocks** — code blocks capped at ~300px, scroll within
3. **Mermaid diagram rendering** — fenced ` ```mermaid ` blocks rendered as SVG diagrams
4. **Copy entire message button** — hover toolbar under assistant bubbles (Copy + 👍)
5. **Typing indicator** — no new component; existing `streaming-cursor` used from first frame

---

## Scope

All changes are confined to `apps/ui/src/`:
- `components/chat/MarkdownRenderer.jsx` — primary file for 1, 2, 3
- `components/chat/ChatTranscript.jsx` — hover toolbar for 4; streaming-cursor already present for 5
- `styles/global.css` — CSS for hover toolbar, copy icon, Mermaid container

No backend changes. No new API endpoints.

---

## Feature Details

### 1. Copy button on code blocks

**Placement:** Floating icon overlaid top-right corner of the code block, always present (not just on hover — mobile-friendly).

**Style:** Semi-transparent dark background (`rgba(255,255,255,0.08)`), rounded corners, `Copy` icon (Lucide `Copy` — already used elsewhere in the UI). On click: icon switches to a checkmark for 1.5 s then reverts.

**Implementation:** In `MarkdownRenderer.jsx`, the `pre` override wraps the `<SyntaxHighlighter>` in a relative-positioned `<div>`. A `<button>` with `position:absolute;top:8px;right:8px` sits inside. Uses `navigator.clipboard.writeText(codeText)`.

### 2. Max-height + scroll on code blocks

**Max height:** `300px` (approximately 18–20 lines at 0.85 em).

**Behaviour:** Code block scrolls vertically within the `300px` container. No "expand" toggle — scrollable is sufficient for paste-inspect workflow.

**Implementation:** `customStyle` on `<SyntaxHighlighter>` gains `maxHeight: '300px'` and `overflowY: 'auto'`. The outer wrapper div also gets `overflow: hidden; border-radius: 6px` to clip the scroll container cleanly.

### 3. Mermaid diagram rendering

**Behaviour:** Fenced code blocks with language `mermaid` are rendered as inline SVG diagrams instead of syntax-highlighted text.

**Library:** `mermaid` npm package (install: `npm install mermaid` in `apps/ui`).

**Implementation:** In the `pre` override, check if `language === 'mermaid'`. If so, render a `<MermaidBlock code={codeText} />` component instead of `<SyntaxHighlighter>`. `MermaidBlock` is a small component in the same file:

```jsx
import mermaid from 'mermaid'
import { useEffect, useRef } from 'react'

mermaid.initialize({ startOnLoad: false, theme: 'dark' })

function MermaidBlock({ code }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!ref.current) return
    const id = `mermaid-${Math.random().toString(36).slice(2)}`
    mermaid.render(id, code).then(({ svg }) => {
      if (ref.current) ref.current.innerHTML = svg
    }).catch(() => {
      if (ref.current) ref.current.textContent = code
    })
  }, [code])
  return <div ref={ref} className="mermaid-block" />
}
```

**CSS:** `.mermaid-block` gets `overflow: auto; background: #1e1e1e; border-radius: 6px; padding: 16px; margin: 0.5em 0`.

**Fallback:** On render error, raw code is displayed as plain text.

### 4. Copy entire message button

**Trigger:** Hovering an assistant message bubble reveals a small toolbar directly below the bubble.

**Contents:** Two icon-buttons side by side:
- Copy icon (Lucide `Copy`) — copies full message markdown text to clipboard. Switches to `Check` icon for 1.5 s on success.
- Thumbs up icon (Lucide `ThumbsUp`) — no backend action in this iteration; toggles a filled state visually only.

**Style:** Toolbar has `opacity: 0` normally, `opacity: 1` on `.message-bubble:hover + .message-actions`, or use a wrapping div with CSS group-hover. Buttons use `color: #666`, `hover: #aaa`.

**Implementation:** In `ChatTranscript.jsx`, wrap each assistant message in a `<div className="message-group">`. After the bubble `<div>`, add:
```jsx
{!message.pending && message.role === 'assistant' && (
  <div className="message-actions">
    <button onClick={() => handleCopy(message.content)}>
      {copied ? <Check size={12} /> : <Copy size={12} />}
    </button>
    <button onClick={() => setLiked(l => !l)}>
      <ThumbsUp size={12} className={liked ? 'liked' : ''} />
    </button>
  </div>
)}
```

The copy state (`copied`, `liked`) is local per-message using a small wrapper component `MessageWithActions` extracted in the same file.

**CSS:**
```css
.message-group { position: relative; }
.message-actions {
  display: flex; gap: 6px; padding: 2px 4px;
  opacity: 0; transition: opacity 0.15s;
}
.message-group:hover .message-actions { opacity: 1; }
.message-actions button {
  background: none; border: none; color: #666;
  cursor: pointer; padding: 3px 6px; border-radius: 4px;
  display: flex; align-items: center; gap: 3px; font-size: 11px;
}
.message-actions button:hover { color: #aaa; background: rgba(255,255,255,0.05); }
.message-actions .liked { color: #6b9fff; }
```

### 5. Typing indicator

No change required. The existing `streaming-cursor` span is already rendered from the first pending frame in `ChatTranscript.jsx`. The blinking vertical bar is sufficient feedback that Jarvis is responding.

---

## File Map

| File | Change |
|---|---|
| `apps/ui/src/components/chat/MarkdownRenderer.jsx` | Copy button on code blocks, max-height scroll, Mermaid support |
| `apps/ui/src/components/chat/ChatTranscript.jsx` | `MessageWithActions` wrapper, hover toolbar |
| `apps/ui/src/styles/global.css` | `.message-group`, `.message-actions`, `.mermaid-block` |
| `apps/ui/package.json` | Add `mermaid` dependency |

---

## Out of Scope

- Thumbs down / negative feedback
- Persisting feedback to the API
- Syntax highlighting theme changes
- Mobile-specific touch interactions beyond what works naturally
