import { useState } from 'react'
import { FileText, TerminalSquare } from 'lucide-react'
import { FileTree } from './FileTree'
import { TerminalPane } from './TerminalPane'
import { getFile, type ApiConfig } from '../../lib/api'

type PanelTab = 'files' | 'terminal'

/** Code-mode flade i højre panel: workspace-info + fil-træ/fil-visning + terminal.
 *  Terminal-fanen er lokal kommando-runner og vises kun for workstation-workspace
 *  (§17: lokal eksekvering bliver på brugerens egen maskine). */
export function CodePanel({
  config, kind, root,
}: {
  config: ApiConfig
  kind: 'container' | 'workstation'
  root: string
}) {
  const [openPath, setOpenPath] = useState<string | null>(null)
  const [content, setContent] = useState('')
  const [tab, setTab] = useState<PanelTab>('files')
  // Terminal: workstation (lokal via bro) + container (server-side, owner-only).
  const canTerminal = true

  const openFile = (rel: string) => {
    setOpenPath(rel)
    // Container: repo-relativ 'root/rel'. Workstation: absolut sti 'root/rel' via bridge.
    const full = `${root}/${rel}`
    getFile(config, full, kind).then((f) => setContent(f.content)).catch(() => setContent('(kunne ikke læse fil)'))
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
              title="Terminal (lokal)"
            >
              <TerminalSquare size={13} /> Terminal
            </button>
          )}
        </div>
      </div>
      {tab === 'terminal' && canTerminal ? (
        <div className="codepanel-terminal">
          <TerminalPane cwd={root} kind={kind} config={config} />
        </div>
      ) : (
        <div className="codepanel-body">
          <div className="codepanel-tree">
            <FileTree config={config} kind={kind} root={root} onOpenFile={openFile} />
          </div>
          <div className="codepanel-view">
            {openPath ? (
              <>
                <div className="codepanel-filename">{openPath}</div>
                <pre className="codepanel-content">{content}</pre>
              </>
            ) : (
              <div className="codepanel-empty">Vælg en fil i træet.</div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
