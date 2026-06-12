import { useState } from 'react'
import { useStream } from '../hooks/useStream'
import { useSettings } from '../hooks/useSettings'
import { MessageRow } from '../components/rich/MessageRow'
import { Composer, type ComposerSendOpts } from '../components/shell/Composer'
import { LivenessIndicator } from '../components/feedback/LivenessIndicator'
import { CodePanel } from '../components/panel/CodePanel'

const CONTAINER_ROOTS = ['docs', 'workspace', 'core', 'apps', 'scripts'] as const

/** Code mode: Jarvis koder i et valgt workspace. Stream i midten, CodePanel
 *  (fil-træ + fil/diff) til højre. v1: container-workspace, owner vælger rod. */
export function CodeView({ sessionId }: { sessionId: string | null }) {
  const stream = useStream()
  const { settings } = useSettings()
  const [root, setRoot] = useState<string>('core')
  const config = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined

  const handleSend = (text: string, opts: ComposerSendOpts) => {
    if (!sessionId) return
    stream.send(text, {
      sessionId,
      approvalMode: opts.permission,
      attachmentIds: opts.attachments.map((a) => a.id),
      mode: 'code',
      workspaceKind: 'container',
      workspaceRoot: root,
    })
  }

  return (
    <div className="codeview">
      <div className="codeview-main">
        <div className="codeview-toolbar">
          <span className="codeview-toolbar-label">Workspace</span>
          <select value={root} onChange={(e) => setRoot(e.target.value)}>
            {CONTAINER_ROOTS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
        <div className="transcript">
          {stream.blocks.length > 0 && (
            <MessageRow role="assistant" blocks={stream.blocks} density="full" streaming={stream.status === 'working'} />
          )}
          <LivenessIndicator status={stream.status} elapsedMs={stream.elapsedMs} density="full" workingStep={stream.workingStep} />
        </div>
        <div className="composer-area">
          <Composer
            streaming={stream.status === 'working'}
            onSend={handleSend}
            onStop={() => void stream.abort()}
            model="deepseek-flash"
            thinking="think"
            config={config}
            getSessionId={async () => sessionId ?? ''}
            showPermissions={true}
            contextTokens={stream.usage.input + stream.usage.cacheHit}
            compactAt={0}
          />
        </div>
      </div>
      {config && (
        <div className="codeview-panel">
          <CodePanel config={config} kind="container" root={root} />
        </div>
      )}
    </div>
  )
}
