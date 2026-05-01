import { useEffect, useState, useRef, useCallback } from 'react'

/**
 * @file autocomplete state for the Composer.
 *
 * Reads the active project root from localStorage (set by JarvisX's
 * App-level effect). When user types `@` followed by characters, this
 * hook surfaces file matches from /api/project/list with fuzzy ranking.
 *
 * The composer renders the dropdown and inserts the chosen `@~/path` on
 * select. Webchat (no project anchor) gets a no-op: the hook returns
 * empty state and the composer hides the dropdown.
 *
 * Path display rule: paths under $HOME are shown as `~/...`. Everything
 * else as absolute. Jarvis sees the literal text the user inserted.
 */
const PROJECT_ROOT_KEY = 'jarvisx.project_root'

function getActiveProjectRoot() {
  try {
    return localStorage.getItem(PROJECT_ROOT_KEY) || ''
  } catch {
    return ''
  }
}

export function useFileMentions() {
  const [projectRoot, setProjectRoot] = useState(() => getActiveProjectRoot())
  const [files, setFiles] = useState([])  // [{path, rel, size_bytes}]
  const [filesLoadedFor, setFilesLoadedFor] = useState('')
  const [query, setQuery] = useState(null)  // null = inactive, '' = just typed @
  const [matches, setMatches] = useState([])
  const [highlightIdx, setHighlightIdx] = useState(0)
  const fetchAbortRef = useRef(null)

  // Track project root changes (multi-window or anchor swap)
  useEffect(() => {
    const sync = () => setProjectRoot(getActiveProjectRoot())
    window.addEventListener('storage', sync)
    return () => window.removeEventListener('storage', sync)
  }, [])

  // Load file list when project root changes (or first activation)
  const ensureFilesLoaded = useCallback(async () => {
    const root = getActiveProjectRoot()
    if (!root) {
      setFiles([])
      setFilesLoadedFor('')
      return
    }
    if (root === filesLoadedFor && files.length > 0) return
    if (fetchAbortRef.current) fetchAbortRef.current.abort()
    const ctrl = new AbortController()
    fetchAbortRef.current = ctrl
    try {
      const res = await fetch(
        `/api/project/list?root=${encodeURIComponent(root)}&limit=2000`,
        { signal: ctrl.signal },
      )
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const j = await res.json()
      setFiles(j.files || [])
      setFilesLoadedFor(root)
    } catch (e) {
      if (e.name !== 'AbortError') {
        setFiles([])
      }
    }
  }, [files.length, filesLoadedFor])

  /**
   * Inspect the current textarea state. If cursor is right after an
   * `@xxx` token (no whitespace before the @, only valid filename
   * characters after), activate the dropdown with that query.
   *
   * Called from the composer's onChange / keyup. The composer holds the
   * textarea ref and passes value + cursor position.
   */
  const detect = useCallback(
    (value, cursorPos) => {
      if (!projectRoot) {
        setQuery(null)
        return
      }
      const before = value.slice(0, cursorPos)
      // Match @ followed by [\w.-/], with @ at start-of-line or
      // immediately after whitespace
      const m = before.match(/(^|\s)@([\w./_-]*)$/)
      if (!m) {
        setQuery(null)
        return
      }
      const q = m[2]
      setQuery(q)
      void ensureFilesLoaded()
    },
    [projectRoot, ensureFilesLoaded],
  )

  // Compute matches when query or files change
  useEffect(() => {
    if (query === null || !files.length) {
      setMatches([])
      return
    }
    const q = query.toLowerCase()
    if (!q) {
      // Just typed @ — show first ~30 files alphabetically
      setMatches(files.slice(0, 30))
      setHighlightIdx(0)
      return
    }
    // Simple ranked match: contains > startsWith > substring
    const scored = files
      .map((f) => {
        const rel = f.rel.toLowerCase()
        const base = rel.split('/').pop()
        if (base.startsWith(q)) return { f, score: 3 }
        if (rel.startsWith(q)) return { f, score: 2.5 }
        if (base.includes(q)) return { f, score: 2 }
        if (rel.includes(q)) return { f, score: 1 }
        return null
      })
      .filter(Boolean)
      .sort((a, b) => b.score - a.score)
      .slice(0, 30)
      .map((s) => s.f)
    setMatches(scored)
    setHighlightIdx(0)
  }, [query, files])

  const cancel = useCallback(() => {
    setQuery(null)
    setMatches([])
  }, [])

  /**
   * Build a path-token to insert. Returns the literal text + the range
   * of the original `@xxx` to replace. Composer applies it to the
   * textarea value.
   */
  const buildInsertion = useCallback(
    (value, cursorPos, file) => {
      const before = value.slice(0, cursorPos)
      const m = before.match(/(^|\s)@([\w./_-]*)$/)
      if (!m) return null
      const startOfAt = before.length - m[2].length - 1  // position of @
      const homeMatch = file.path.match(/^\/home\/[^/]+(.*)$/)
      const display = homeMatch ? `~${homeMatch[1]}` : file.path
      return {
        replaceFrom: startOfAt,
        replaceTo: cursorPos,
        text: `@${display} `,
      }
    },
    [],
  )

  const moveHighlight = useCallback(
    (delta) => {
      setHighlightIdx((i) => {
        if (matches.length === 0) return 0
        const next = (i + delta + matches.length) % matches.length
        return next
      })
    },
    [matches.length],
  )

  return {
    active: query !== null && projectRoot && matches.length > 0,
    query,
    matches,
    highlightIdx,
    moveHighlight,
    detect,
    cancel,
    buildInsertion,
    projectRoot,
  }
}
