import { useEffect, useState } from 'react'
import { FileText, TerminalSquare, Save, X, Search, GitCommit } from 'lucide-react'
import { FileTree } from './FileTree'
import { FileContextMenu } from './FileContextMenu'
import { TerminalPane } from './TerminalPane'
import { CodeBlock } from '../rich/CodeBlock'
import { useResizableWidth } from './useResizableWidth'
import { invalidateTree } from '../../lib/treeCache'
import {
  getFile, writeFile, openExternal, getActiveFile, commitMessage, commitFile, type ApiConfig,
} from '../../lib/api'

type PanelTab = 'files' | 'terminal'

/** Sprog der vises som ren tekst (ingen kode-highlight). */
const _PLAIN = new Set(['', 'text', 'plaintext', 'txt', 'log'])
const ACTIVE_POLL_MS = 1500

/** Code-mode flade i højre panel: fil-træ/fil-visning + terminal. Tabs er
 *  keep-alive (skjules med display, gen-monteres IKKE — terminal/xterm + tree-
 *  fetch er tunge). highlightPath = Jarvis pegede; activePath = live fil Jarvis
 *  læser/skriver nu. Editor: redigér + find/erstat + Gem / Gem & commit. */
export function CodePanel({
  config, kind, root, highlightPath,
}: {
  config: ApiConfig
  kind: 'container' | 'workstation'
  root: string
  highlightPath?: string
}) {
  const [openPath, setOpenPath] = useState<string | null>(null)
  const [content, setContent] = useState('')
  const [lang, setLang] = useState('')
  const [tab, setTab] = useState<PanelTab>('files')
  const [termMounted, setTermMounted] = useState(false)
  const canTerminal = true
  const tree = useResizableWidth({
    initial: 190, min: 120, max: 420, side: 'right', storageKey: 'jarvis-desk:code-tree-w2',
  })
  const [menu, setMenu] = useState<{ path: string; x: number; y: number } | null>(null)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [saveMsg, setSaveMsg] = useState('')
  // Find/erstat i editoren.
  const [showFind, setShowFind] = useState(false)
  const [findText, setFindText] = useState('')
  const [replaceText, setReplaceText] = useState('')
  // Gem & commit-flow: redigerbar auto-besked → commit.
  const [commitDraft, setCommitDraft] = useState<string | null>(null)
  const [commitBusy, setCommitBusy] = useState(false)
  // Live: filen Jarvis senest rørte.
  const [activePath, setActivePath] = useState('')
  const baseTermCwd = kind === 'workstation' ? root : ''
  const [termCwd, setTermCwd] = useState<string | null>(null)

  const canCommit = kind === 'container' && root === 'repo'

  const loadFile = (rel: string, edit = false) => {
    setOpenPath(rel); setContent(''); setLang(''); setEditing(false)
    setSaveMsg(''); setCommitDraft(null); setShowFind(false)
    getFile(config, root, rel, kind)
      .then((f) => {
        setContent(f.content); setLang(f.language || '')
        if (edit) { setDraft(f.content); setEditing(true) }
      })
      .catch(() => { setContent('(kunne ikke læse fil)'); setLang('') })
  }

  useEffect(() => {
    if (highlightPath) { setTab('files'); loadFile(highlightPath) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlightPath])

  useEffect(() => { if (tab === 'terminal') setTermMounted(true) }, [tab])

  // Live poll: marker filen Jarvis netop nu rører (kun mens fil-fanen er åben).
  useEffect(() => {
    if (tab !== 'files') return
    let cancelled = false
    const tick = () => {
      getActiveFile(config)
        .then((r) => { if (!cancelled) setActivePath(r.path || '') })
        .catch(() => { /* poll-fallback */ })
    }
    tick()
    const id = setInterval(tick, ACTIVE_POLL_MS)
    return () => { cancelled = true; clearInterval(id) }
  }, [config, tab])

  const openInTerminal = (rel: string) => {
    const dir = rel.includes('/') ? rel.slice(0, rel.lastIndexOf('/')) : ''
    const cwd = kind === 'workstation' ? `${root}/${dir}` : (root === 'repo' ? dir : '')
    setTermCwd(cwd); setTermMounted(true); setTab('terminal')
  }

  const openInEditor = (rel: string) => {
    if (kind === 'workstation') {
      openExternal(config, root, rel, kind).catch(() => { /* stille */ })
      return
    }
    setTab('files'); loadFile(rel, true)
  }

  const save = () => {
    if (!openPath) return
    setSaveMsg('Gemmer…')
    writeFile(config, root, openPath, draft, kind)
      .then(() => {
        setContent(draft); setEditing(false); setSaveMsg('Gemt ✓')
        invalidateTree(kind, root, openPath.includes('/') ? openPath.slice(0, openPath.lastIndexOf('/')) : '')
        setTimeout(() => setSaveMsg(''), 1800)
      })
      .catch((e) => setSaveMsg(`Fejl: ${e instanceof Error ? e.message : 'kunne ikke gemme'}`))
  }

  // Gem & commit: hent auto-besked → vis redigerbart felt.
  const startCommit = () => {
    if (!openPath) return
    setSaveMsg(''); setCommitBusy(true); setCommitDraft('')
    commitMessage(config, root, openPath, draft)
      .then((r) => setCommitDraft(r.message || `update ${openPath}`))
      .catch(() => setCommitDraft(`update ${openPath}`))
      .finally(() => setCommitBusy(false))
  }
  const doCommit = () => {
    if (!openPath || commitDraft === null) return
    setCommitBusy(true)
    commitFile(config, root, openPath, draft, commitDraft)
      .then((r) => {
        setContent(draft); setEditing(false); setCommitDraft(null)
        setSaveMsg(r.status === 'nochange' ? 'Ingen ændring' : `Committed ${r.sha ?? ''} ✓`)
        invalidateTree(kind, root, openPath.includes('/') ? openPath.slice(0, openPath.lastIndexOf('/')) : '')
        setTimeout(() => setSaveMsg(''), 2400)
      })
      .catch((e) => setSaveMsg(`Commit-fejl: ${e instanceof Error ? e.message : '?'}`))
      .finally(() => setCommitBusy(false))
  }

  const replaceAll = () => {
    if (!findText) return
    setDraft((d) => d.split(findText).join(replaceText))
  }
  const matchCount = findText ? draft.split(findText).length - 1 : 0

  return (
    <div className="codepanel">
      <div className="codepanel-head">
        <span className="codepanel-root">{kind === 'container' ? '📦' : '💻'} {root}</span>
        <div className="codepanel-tabs">
          <button type="button" className={`codepanel-tab ${tab === 'files' ? 'active' : ''}`}
            onClick={() => setTab('files')} title="Filer">
            <FileText size={13} /> Filer
          </button>
          {canTerminal && (
            <button type="button" className={`codepanel-tab ${tab === 'terminal' ? 'active' : ''}`}
              onClick={() => setTab('terminal')} title="Terminal">
              <TerminalSquare size={13} /> Terminal
            </button>
          )}
        </div>
      </div>

      {/* Keep-alive: begge faner forbliver monteret, skjules med display. */}
      <div className="codepanel-body" style={{ display: tab === 'files' ? 'flex' : 'none' }}>
        <div className="codepanel-tree" ref={tree.ref} style={{ width: tree.width }}>
          <FileTree
            config={config} kind={kind} root={root} onOpenFile={loadFile}
            highlightPath={highlightPath} activePath={activePath}
            onContext={(path, x, y) => setMenu({ path, x, y })}
          />
        </div>
        <div role="separator" aria-orientation="vertical"
          className={`codepanel-handle ${tree.dragging ? 'dragging' : ''}`}
          onMouseDown={tree.startDrag} />
        <div className="codepanel-view">
          {openPath ? (
            <>
              <div className="codepanel-filename">
                {openPath}
                {editing && (
                  <span className="codepanel-editor-actions">
                    <button type="button" className="codepanel-tool" onClick={() => setShowFind((s) => !s)} title="Find/erstat">
                      <Search size={12} />
                    </button>
                    <button type="button" className="codepanel-save" onClick={save} title="Gem">
                      <Save size={12} /> Gem
                    </button>
                    {canCommit && (
                      <button type="button" className="codepanel-save" onClick={startCommit} disabled={commitBusy} title="Gem & commit">
                        <GitCommit size={12} /> Gem & commit
                      </button>
                    )}
                    <button type="button" className="codepanel-cancel" onClick={() => { setEditing(false); setCommitDraft(null) }} title="Annullér">
                      <X size={12} />
                    </button>
                    {saveMsg && <span className="codepanel-save-msg">{saveMsg}</span>}
                  </span>
                )}
                {!editing && saveMsg && <span className="codepanel-save-msg">{saveMsg}</span>}
              </div>
              {editing && showFind && (
                <div className="codepanel-find">
                  <input className="codepanel-find-input" placeholder="Find" value={findText}
                    onChange={(e) => setFindText(e.target.value)} />
                  <input className="codepanel-find-input" placeholder="Erstat med" value={replaceText}
                    onChange={(e) => setReplaceText(e.target.value)} />
                  <button type="button" className="codepanel-tool" onClick={replaceAll} disabled={!findText}>Erstat alle</button>
                  <span className="codepanel-save-msg">{findText ? `${matchCount} match` : ''}</span>
                </div>
              )}
              {editing && commitDraft !== null && (
                <div className="codepanel-commit">
                  <input className="codepanel-commit-input" value={commitDraft}
                    placeholder={commitBusy ? 'Genererer besked…' : 'Commit-besked'}
                    onChange={(e) => setCommitDraft(e.target.value)} />
                  <button type="button" className="codepanel-save" onClick={doCommit} disabled={commitBusy || !commitDraft.trim()}>
                    Commit
                  </button>
                  <button type="button" className="codepanel-cancel" onClick={() => setCommitDraft(null)}><X size={12} /></button>
                </div>
              )}
              {editing ? (
                <textarea className="codepanel-editor" value={draft} spellCheck={false}
                  onChange={(e) => setDraft(e.target.value)} />
              ) : _PLAIN.has(lang.toLowerCase()) ? (
                <pre className="codepanel-content">{content}</pre>
              ) : (
                <CodeBlock code={content} lang={lang} />
              )}
            </>
          ) : (
            <div className="codepanel-empty">Vælg en fil i træet. Højreklik for editor/terminal.</div>
          )}
        </div>
      </div>

      {termMounted && (
        <div className="codepanel-terminal" style={{ display: tab === 'terminal' ? 'block' : 'none' }}>
          <TerminalPane cwd={termCwd ?? baseTermCwd} kind={kind} config={config} />
        </div>
      )}

      {menu && (
        <FileContextMenu
          x={menu.x} y={menu.y}
          onEditor={() => openInEditor(menu.path)}
          onTerminal={() => openInTerminal(menu.path)}
          onClose={() => setMenu(null)}
        />
      )}
    </div>
  )
}
