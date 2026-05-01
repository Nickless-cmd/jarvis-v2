/**
 * Minimal ANSI escape parser → styled <span> tree.
 *
 * Handles the SGR (Select Graphic Rendition) subset of ANSI:
 *   - Reset (0)
 *   - Bold (1) / Dim (2) / Italic (3) / Underline (4)
 *   - 8 base foreground colors (30-37)
 *   - 8 bright foreground colors (90-97)
 *   - 8 base background colors (40-47)
 *   - 256-color (38;5;N / 48;5;N) — first 16 only mapped, rest fall back
 *   - 24-bit truecolor (38;2;R;G;B / 48;2;R;G;B)
 *
 * Anything we don't know is silently dropped — text still renders, just
 * without that style. That's the right tradeoff for terminal output we
 * don't fully control (pytest, npm, git, etc.).
 *
 * Why no library? `ansi-to-react` exists but pulls in a heavy dep tree
 * for ~80 lines of work. This stays self-contained.
 */

// 16-color palette tuned for our dark theme — slightly desaturated so
// red errors don't burn out and greens don't vibrate.
const COLOR_BASE = {
  0: '#484f58',  // black (more visible than pure #000 on dark bg)
  1: '#f85149',  // red
  2: '#3fb950',  // green
  3: '#d29922',  // yellow
  4: '#58a6ff',  // blue
  5: '#bc8cff',  // magenta
  6: '#39c5cf',  // cyan
  7: '#c9d1d9',  // white
}
const COLOR_BRIGHT = {
  0: '#6e7681',
  1: '#ff7b72',
  2: '#7fdb8b',
  3: '#e3b341',
  4: '#79c0ff',
  5: '#d2a8ff',
  6: '#56d4dd',
  7: '#f0f6fc',
}

const ANSI_RE = /\x1b\[([0-9;]*)m/g

function applyCodes(state, codes) {
  // Mutates state in place so a span can carry forward multiple codes
  // until reset.
  let i = 0
  while (i < codes.length) {
    const c = codes[i]
    if (c === 0 || isNaN(c)) {
      Object.assign(state, defaultState())
    } else if (c === 1) state.bold = true
    else if (c === 2) state.dim = true
    else if (c === 3) state.italic = true
    else if (c === 4) state.underline = true
    else if (c === 22) state.bold = false
    else if (c === 23) state.italic = false
    else if (c === 24) state.underline = false
    else if (c >= 30 && c <= 37) state.fg = COLOR_BASE[c - 30]
    else if (c === 38) {
      // 38;5;N (256) or 38;2;R;G;B (truecolor)
      if (codes[i + 1] === 5) {
        const n = codes[i + 2]
        state.fg = palette256(n)
        i += 2
      } else if (codes[i + 1] === 2) {
        state.fg = `rgb(${codes[i + 2]},${codes[i + 3]},${codes[i + 4]})`
        i += 4
      }
    } else if (c === 39) state.fg = null
    else if (c >= 40 && c <= 47) state.bg = COLOR_BASE[c - 40]
    else if (c === 48) {
      if (codes[i + 1] === 5) {
        state.bg = palette256(codes[i + 2])
        i += 2
      } else if (codes[i + 1] === 2) {
        state.bg = `rgb(${codes[i + 2]},${codes[i + 3]},${codes[i + 4]})`
        i += 4
      }
    } else if (c === 49) state.bg = null
    else if (c >= 90 && c <= 97) state.fg = COLOR_BRIGHT[c - 90]
    else if (c >= 100 && c <= 107) state.bg = COLOR_BRIGHT[c - 100]
    i += 1
  }
}

function palette256(n) {
  if (n < 8) return COLOR_BASE[n]
  if (n < 16) return COLOR_BRIGHT[n - 8]
  if (n >= 232) {
    // grayscale ramp
    const v = 8 + (n - 232) * 10
    return `rgb(${v},${v},${v})`
  }
  // 6×6×6 cube
  const idx = n - 16
  const r = Math.floor(idx / 36)
  const g = Math.floor((idx % 36) / 6)
  const b = idx % 6
  const ramp = [0, 95, 135, 175, 215, 255]
  return `rgb(${ramp[r]},${ramp[g]},${ramp[b]})`
}

function defaultState() {
  return { bold: false, dim: false, italic: false, underline: false, fg: null, bg: null }
}

function styleFor(state) {
  const s = {}
  if (state.fg) s.color = state.fg
  if (state.bg) s.background = state.bg
  if (state.bold) s.fontWeight = 700
  if (state.italic) s.fontStyle = 'italic'
  if (state.underline) s.textDecoration = 'underline'
  if (state.dim) s.opacity = 0.6
  return s
}

/**
 * Render text containing ANSI escapes as a sequence of styled spans.
 * Falls back to plain text if no escapes are present (no overhead).
 */
export function AnsiText({ text, className }) {
  if (!text || typeof text !== 'string') return null
  if (!text.includes('\x1b[')) {
    // Fast path — no ANSI codes at all.
    return <span className={className}>{text}</span>
  }
  const segments = []
  const state = defaultState()
  let lastIdx = 0
  let key = 0
  ANSI_RE.lastIndex = 0
  let match
  while ((match = ANSI_RE.exec(text)) !== null) {
    if (match.index > lastIdx) {
      segments.push(
        <span key={key++} style={styleFor(state)}>
          {text.slice(lastIdx, match.index)}
        </span>,
      )
    }
    const codes = match[1]
      ? match[1].split(';').map((c) => parseInt(c, 10))
      : [0]
    applyCodes(state, codes)
    lastIdx = match.index + match[0].length
  }
  if (lastIdx < text.length) {
    segments.push(
      <span key={key++} style={styleFor(state)}>
        {text.slice(lastIdx)}
      </span>,
    )
  }
  return <span className={className}>{segments}</span>
}
