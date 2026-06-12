import { useState } from 'react'
import { FileTree } from './FileTree'
import { getFile, type ApiConfig } from '../../lib/api'

/** Code-mode flade i højre panel: workspace-info + fil-træ + fil-visning.
 *  (Diff-visning fra tool_use-blokke kobles på i Task 10 via openDiff-prop.) */
export function CodePanel({
  config, kind, root,
}: {
  config: ApiConfig
  kind: 'container' | 'workstation'
  root: string
}) {
  const [openPath, setOpenPath] = useState<string | null>(null)
  const [content, setContent] = useState('')

  const openFile = (rel: string) => {
    setOpenPath(rel)
    // Container: repo-relativ 'root/rel'. Workstation: absolut sti 'root/rel' via bridge.
    const full = `${root}/${rel}`
    getFile(config, full, kind).then((f) => setContent(f.content)).catch(() => setContent('(kunne ikke læse fil)'))
  }

  return (
    <div className="codepanel">
      <div className="codepanel-head">{kind === 'container' ? '📦' : '💻'} {root}</div>
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
    </div>
  )
}
