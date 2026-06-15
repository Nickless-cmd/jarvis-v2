import { useEffect, useState } from 'react'
import { FileText, TerminalSquare, Save, X } from 'lucide-react'
import { FileTree } from './FileTree'
import { FileContextMenu } from './FileContextMenu'
import { TerminalPane } from './TerminalPane'
import { CodeBlock } from '../rich/CodeBlock'
import { useResizableWidth } from './useResizableWidth'
import { getFile, writeFile, openExternal, type ApiConfig } from '../../lib/api'

type PanelTab = 'files' | 'terminal'

/** Sprog der vises som ren tekst (ingen kode-highlight). */
const _PLAIN = new Set(['', 'text', 'plaintext', 'txt', 'log'])

/** Code-mode flade i højre panel: workspace-info + fil-træ/fil-visning + terminal.
 *  highlightPath (Jarvis-styret) åbner + scroller-til en fil. Højreklik på en fil
 *  giver "Åbn i editor" (container: in-app editor m. gem; workstation: lokal OS-
 *  editor via xdg-open) og "Åbn i terminal" (cd'er til filens mappe). */
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
  const canTerminal = true
  // Trækbar fil-træ-bredde (mod højre). Vedholdende på tværs af genstart.
  const tree = useResizableWidth({
    initial: 190, min: 120, max: 420, side: 'right', storageKey: 'jarvis-desk:code-tree-w2',
  })
  // Højreklik-menu + in-app editor + terminal-cwd-override.
  const [menu, setMenu] = useState<{ path: string; x: number; y: number } | null>(null)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [saveMsg, setSaveMsg] = useState('')
  // Terminal-cwd: default repo-rod (container) / valgt mappe (workstation); kan
  // overrides af "Åbn i terminal" til en bestemt fils mappe.
  const baseTermCwd = kind === 'workstation' ? root : ''
  const [termCwd, setTermCwd] = useState<string | null>(null)

  const loadFile = (rel: string, edit = false) => {
    setOpenPath(rel)
    setContent('')
    setLang('')
    setEditing(false)
    setSaveMsg('')
    getFile(config, root, rel, kind)
      .then((f) => {
        setContent(f.content); setLang(f.language || '')
        if (edit) { setDraft(f.content); setEditing(true) }
      })
      .catch(() => { setContent('(kunne ikke læse fil)'); setLang('') })
  }

  // Jarvis-styret highlight: åbn filen i preview når en highlight rammer.
  useEffect(() => {
    if (highlightPath) { setTab('files'); loadFile(highlightPath) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [highlightPath])

  // Højreklik → "Åbn i terminal": cd til filens mappe + skift til terminal-fanen.
  const openInTerminal = (rel: string) => {
    const dir = rel.includes('/') ? rel.slice(0, rel.lastIndexOf('/')) : ''
    // Container-terminal jailer til repo → kun repo-relativ sti giver mening dér.
    const cwd = kind === 'workstation' ? `${root}/${dir}` : (root === 'repo' ? dir : '')
    setTermCwd(cwd)
    setTab('terminal')
  }

  // Højreklik → "Åbn i editor": workstation åbner lokal OS-editor (xdg-open);
  // container åbner in-app editoren (redigerbar + gem).
  const openInEditor = (rel: string) => {
    if (kind === 'workstation') {
      openExternal(config, root, rel, kind).catch(() => { /* stille — bruger ser intet vindue */ })
      return
    }
    setTab('files')
    loadFile(rel, true)
  }

  const save = () => {
    if (!openPath) return
    setSaveMsg('Gemmer…')
    writeFile(config, root, openPath, draft, kind)
      .then(() => { setContent(draft); setEditing(false); setSaveMsg('Gemt ✓'); setTimeout(() => setSaveMsg(''), 1800) })
      .catch((e) => setSaveMsg(`Fejl: ${e instanceof Error ? e.message : 'kunne ikke gemme'}`))
  }

  return (
    <div className="codepanel">
      <div className="codepanel-head">
        <span className="codepanel-root">{kind === 'container' ? '📦' : '💻'} {root}</span>
        <div className="codepanel-tabs">
          <button
            type="button"
            className={`codepanel-tab ${tab === 'files' ? 'active' : ''}`}
            onClick={() => setTab('files')}
            title="Filer"
          >
            <FileText size={13} /> Filer
          </button>
          {canTerminal && (
            <button
              type="button"
              className={`codepanel-tab ${tab === 'terminal' ? 'active' : ''}`}
              onClick={() => setTab('terminal')}
              title="Terminal"
            >
              <TerminalSquare size={13} /> Terminal
            </button>
          )}
        </div>
      </div>
      {tab === 'terminal' && canTerminal ? (
        <div className="codepanel-terminal">
          <TerminalPane cwd={termCwd ?? baseTermCwd} kind={kind} config={config} />
        </div>
      ) : (
        <div className="codepanel-body">
          <div className="codepanel-tree" ref={tree.ref} style={{ width: tree.width }}>
            <FileTree
              config={config} kind={kind} root={root} onOpenFile={loadFile}
              highlightPath={highlightPath}
              onContext={(path, x, y) => setMenu({ path, x, y })}
            />
          </div>
          <div
            role="separator"
            aria-orientation="vertical"
            className={`codepanel-handle ${tree.dragging ? 'dragging' : ''}`}
            onMouseDown={tree.startDrag}
          />
          <div className="codepanel-view">
            {openPath ? (
              <>
                <div className="codepanel-filename">
                  {openPath}
                  {editing && (
                    <span className="codepanel-editor-actions">
                      <button type="button" className="codepanel-save" onClick={save} title="Gem">
                        <Save size={12} /> Gem
                      </button>
                      <button type="button" className="codepanel-cancel" onClick={() => setEditing(false)} title="Annullér">
                        <X size={12} />
                      </button>
                      {saveMsg && <span className="codepanel-save-msg">{saveMsg}</span>}
                    </span>
                  )}
                </div>
                {editing ? (
                  <textarea
                    className="codepanel-editor"
                    value={draft}
                    spellCheck={false}
                    onChange={(e) => setDraft(e.target.value)}
                  />
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
