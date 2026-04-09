import { useEffect, useMemo, useRef, useState } from 'react'
import { MoreVertical, Search, RefreshCw, X } from 'lucide-react'
import { Chip } from '../shared/Chip'
import { backend } from '../../lib/adapters'

export function ChatHeader({
  session,
  onRefresh,
  onRename,
  onDelete,
  isRefreshing,
  messages,
}) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const menuRef = useRef(null)
  const searchInputRef = useRef(null)

  // Close menu on click outside
  useEffect(() => {
    if (!menuOpen) return
    function handleClick(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false)
    }
    function handleEsc(e) { if (e.key === 'Escape') setMenuOpen(false) }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleEsc)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleEsc)
    }
  }, [menuOpen])

  // Focus search input when opened
  useEffect(() => {
    if (searchOpen) searchInputRef.current?.focus()
  }, [searchOpen])

  const searchResults = useMemo(() => {
    if (!searchOpen || !searchQuery.trim()) return []
    const q = searchQuery.toLowerCase()
    return (messages || []).filter(m =>
      (m.content || '').toLowerCase().includes(q)
    ).slice(0, 20)
  }, [searchOpen, searchQuery, messages])

  function handleRename() {
    setMenuOpen(false)
    const newTitle = prompt('Rename session:', session?.title || '')
    if (newTitle?.trim()) onRename?.(newTitle.trim())
  }

  function handleDelete() {
    setMenuOpen(false)
    if (confirm('Delete this session? This cannot be undone.')) {
      onDelete?.()
    }
  }

  return (
    <>
      <section className="chat-header-bar">
        <div className="chat-header-left">
          <span className="chat-header-session-title">{session?.title || 'Ny chat'}</span>
          <div className="chat-header-chips">
            <Chip color="#3d8f7c">L3</Chip>
            <Chip color="#d4963a">EXP</Chip>
          </div>
        </div>

        <div className="chat-header-right">
          <button className="icon-btn" onClick={onRefresh} title="Refresh">
            <RefreshCw size={14} className={isRefreshing ? 'spin' : ''} />
          </button>
          <button className="icon-btn" title="Search" onClick={() => { setSearchOpen(!searchOpen); setSearchQuery('') }}>
            <Search size={14} />
          </button>

          <div className="header-menu-anchor" ref={menuRef}>
            <button className="icon-btn" title="Session options" onClick={() => setMenuOpen(!menuOpen)}>
              <MoreVertical size={14} />
            </button>
            {menuOpen && (
              <div className="header-dropdown-menu">
                <button className="header-dropdown-item" onClick={handleRename}>Rename</button>
                <button className="header-dropdown-item" onClick={() => { setMenuOpen(false) }}>Pin</button>
                <button className="header-dropdown-item" onClick={() => { setMenuOpen(false) }}>Archive</button>
                <button className="header-dropdown-item danger" onClick={handleDelete}>Delete</button>
              </div>
            )}
          </div>
        </div>
      </section>

      {searchOpen && (
        <div className="chat-search-bar">
          <Search size={13} className="chat-search-icon" />
          <input
            ref={searchInputRef}
            className="chat-search-input mono"
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search in chat..."
            onKeyDown={(e) => { if (e.key === 'Escape') { setSearchOpen(false); setSearchQuery('') } }}
          />
          <button className="icon-btn" onClick={() => { setSearchOpen(false); setSearchQuery('') }}>
            <X size={13} />
          </button>
          {searchQuery.trim() && (
            <div className="chat-search-results">
              {searchResults.length === 0 ? (
                <div className="chat-search-empty mono">No matches</div>
              ) : (
                searchResults.filter((m) => m.role !== 'tool').map((m, i) => (
                  <div key={m.id || i} className="chat-search-result">
                    <span className="chat-search-result-role mono">{m.role === 'assistant' ? 'Jarvis' : 'You'}</span>
                    <span className="chat-search-result-text">{(m.content || '').slice(0, 120)}</span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </>
  )
}
