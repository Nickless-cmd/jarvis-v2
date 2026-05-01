import { useEffect, useMemo, useRef, useState } from 'react'
import {
  PanelRightOpen,
  PanelRightClose,
  Camera,
  Search as SearchIcon,
  Pencil,
  Bot,
  Wrench,
  Terminal as TerminalIcon,
  FileText,
} from 'lucide-react'
import { Composer } from '@ui/components/chat/Composer.jsx'
import { ProjectAnchor } from './ProjectAnchor'
import { PinnedStrip } from './PinnedStrip'
import { StagedEditsStrip } from './StagedEditsStrip'
import { FileTreePanel } from './FileTreePanel'
import { ScreenCaptureModal } from './ScreenCaptureModal'
import { CrossSessionSearchModal } from './CrossSessionSearchModal'
import { MessageList } from './native/MessageList'
import { ChatHeader } from './native/ChatHeader'
import { TodoPanel } from './TodoPanel'
import { SlashPalette, type SlashCommand, CommandIcons } from './SlashPalette'
import { MoodPill } from './MoodPill'
import { PresencePill } from './PresencePill'
import { OutputStylePill } from './OutputStylePill'
import { AgentsPanel } from './AgentsPanel'
import { ToolInventoryModal } from './ToolInventoryModal'
import { VoiceButton } from './VoiceButton'
import { TerminalDrawer } from './native/TerminalDrawer'
import { DiffReviewPanel } from './native/DiffReviewPanel'
import { FilePreviewPane } from './native/FilePreviewPane'
import { ConnectionPill } from './ConnectionPill'
import { PendingPlansStrip } from './PendingPlansStrip'
import { TaskBar } from './TaskBar'

// Cap how many messages we render at once. The active prod session has
// 1674 messages — rendering all of them blows up every keystroke because
// each message mounts its own MarkdownRenderer + react-syntax-highlighter.
// 100 is plenty of immediate context; older history is still in the
// session and visible if we wire pagination later.
const MESSAGE_WINDOW = 100

interface ChatViewProps {
  apiBaseUrl: string
  userId: string
  userName: string
  projectRoot: string
  recentProjects: string[]
  onProjectChange: (patch: {
    projectRoot?: string
    recentProjects?: string[]
  }) => Promise<void> | void
  shell: ShellLike
  role?: 'owner' | 'member' | 'guest'
}

// useUnifiedShell return shape — kept permissive because we're crossing
// the JS↔TS boundary and apps/ui sets the contract. Strict callable
// signatures here would drift each time the hook gains a parameter.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
interface ShellLike extends Record<string, any> {}

/**
 * JarvisX chat surface — native, Claude-Code-style.
 *
 * What's native:
 *   - MessageList: own rendering of bubbles + tool-result cards
 *   - ChatHeader: minimal title + rename/delete
 *   - Top toolbar: project anchor, search, screencap, file tree toggle
 *   - StagedEditsStrip / PinnedStrip integration
 *   - Multi-user safe: sessions filtered by X-JarvisX-User header (in backend)
 *
 * What's reused from apps/ui (intentionally — these are primitives, not
 * "the chat experience"):
 *   - Composer (full-featured: attachments, plan-mode, approval, git-commit,
 *     @file autocomplete, model selector). Bjørn explicitly OK'd this.
 *   - MarkdownRenderer (used inside MessageList) + InlineToolResult cards
 *   - useUnifiedShell hook for backend state (lifted to App.tsx)
 *
 * What's gone (was via the wholesale ChatPage import):
 *   - ChatTranscript (replaced by native MessageList)
 *   - ChatSupportRail (the "system metrics" right-rail — too noisy for
 *     a desktop app; key bits like token meter live in StatusBar)
 *   - The hardcoded chat-shell-grid layout
 */
export function ChatView({
  apiBaseUrl,
  userId,
  userName,
  projectRoot,
  recentProjects,
  onProjectChange,
  shell,
  role = 'guest',
}: ChatViewProps) {
  // pause_and_ask + approval-card listeners — option button clicks in
  // InlineToolResult dispatch CustomEvents that we forward to the
  // shell's handleSend so the response lands as the next user message
  // and the run resumes.
  useEffect(() => {
    const onAnswer = (e: Event) => {
      const detail = (e as CustomEvent).detail as
        | { question: string; picked: string }
        | undefined
      if (!detail || !shell.handleSend) return
      const send = shell.handleSend as (msg: string) => void
      send(detail.picked)
    }
    const onApproval = (e: Event) => {
      const detail = (e as CustomEvent).detail as
        | { verdict: string; tool: string; reply: string }
        | undefined
      if (!detail || !shell.handleSend) return
      const send = shell.handleSend as (msg: string) => void
      send(detail.reply)
    }
    const onVoice = (e: Event) => {
      const detail = (e as CustomEvent).detail as { text: string } | undefined
      if (!detail?.text) return
      setDraft((cur) => (cur ? `${cur} ${detail.text}` : detail.text))
    }
    window.addEventListener('jarvisx:pause-answer', onAnswer)
    window.addEventListener('jarvisx:approval-response', onApproval)
    window.addEventListener('jarvisx:voice-transcript', onVoice)
    return () => {
      window.removeEventListener('jarvisx:pause-answer', onAnswer)
      window.removeEventListener('jarvisx:approval-response', onApproval)
      window.removeEventListener('jarvisx:voice-transcript', onVoice)
    }
  }, [shell.handleSend])

  const [showCapture, setShowCapture] = useState(false)
  const [showSearch, setShowSearch] = useState(false)
  const [showSlashPalette, setShowSlashPalette] = useState(false)
  const [showAgents, setShowAgents] = useState(false)
  const [showToolInventory, setShowToolInventory] = useState(false)
  const [terminalOpen, setTerminalOpen] = useState<boolean>(() => {
    return localStorage.getItem('jarvisx:terminal-open') === '1'
  })
  useEffect(() => {
    localStorage.setItem('jarvisx:terminal-open', terminalOpen ? '1' : '0')
  }, [terminalOpen])
  const [showDiffReview, setShowDiffReview] = useState(false)
  const [previewOpen, setPreviewOpen] = useState<boolean>(() => {
    return localStorage.getItem('jarvisx:preview-open') === '1'
  })
  const [previewPath, setPreviewPath] = useState<string>(() => {
    return localStorage.getItem('jarvisx:preview-path') || ''
  })
  useEffect(() => {
    localStorage.setItem('jarvisx:preview-open', previewOpen ? '1' : '0')
  }, [previewOpen])
  useEffect(() => {
    if (previewPath) localStorage.setItem('jarvisx:preview-path', previewPath)
  }, [previewPath])

  // Cross-app file preview channel — any component can dispatch
  // jarvisx:preview-file with { detail: { path } } and the right pane
  // updates without prop drilling
  useEffect(() => {
    const onPreview = (e: Event) => {
      const detail = (e as CustomEvent<{ path?: string }>).detail
      if (!detail?.path) return
      setPreviewPath(detail.path)
      setPreviewOpen(true)
    }
    window.addEventListener('jarvisx:preview-file', onPreview)
    return () => window.removeEventListener('jarvisx:preview-file', onPreview)
  }, [])

  // jarvisx:open-terminal opens the bottom drawer (TerminalDrawer also
  // listens to set its active tab from the same event)
  useEffect(() => {
    const onOpenTerm = () => setTerminalOpen(true)
    window.addEventListener('jarvisx:open-terminal', onOpenTerm)
    return () => window.removeEventListener('jarvisx:open-terminal', onOpenTerm)
  }, [])
  const [planMode, setPlanMode] = useState(false)
  const [draft, setDraft] = useState('')
  const [queuedMessage, setQueuedMessage] = useState<{
    msg: string
    opts?: unknown
  } | null>(null)

  // Cmd/Ctrl+K opens search; Cmd/Ctrl+/ opens slash palette;
  // Toggle terminal drawer with either Ctrl+J (VS Code "Toggle Panel"
  // shortcut, works on every keyboard layout) or Ctrl+` (backtick —
  // on Danish layouts this requires Shift+¨ + space dead-key dance,
  // so we match by physical key position via e.code === 'Backquote'
  // which fires regardless of what character that key produces).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const ctrlOrMeta = e.ctrlKey || e.metaKey
      if (!ctrlOrMeta) return
      if (e.key === 'k' && !e.shiftKey) {
        e.preventDefault()
        setShowSearch(true)
      } else if (e.key === '/') {
        e.preventDefault()
        setShowSlashPalette(true)
      } else if (
        !e.shiftKey &&
        !e.altKey &&
        (e.code === 'Backquote' || e.key === '`' || e.key === 'j' || e.key === 'J')
      ) {
        e.preventDefault()
        setTerminalOpen((v) => !v)
      } else if (e.key === 'n' || e.key === 'N') {
        // Ctrl+N → new chat session. Skip if Shift held (Ctrl+Shift+N
        // is "open new window" on most desktops; we don't want to steal
        // that even though Electron handles it differently).
        if (e.shiftKey || e.altKey) return
        e.preventDefault()
        shell.handleCreateSession?.()
      } else if (e.key === 'l' || e.key === 'L') {
        // Ctrl+L → focus the composer textarea. Composer doesn't expose
        // a ref to us, so we find it by class — apps/ui sets
        // .composer-shell on the wrapper and the textarea inside is
        // the first <textarea>. Cheap and stable.
        if (e.shiftKey || e.altKey) return
        e.preventDefault()
        const ta = document.querySelector(
          '.jarvisx-composer-host textarea',
        ) as HTMLTextAreaElement | null
        ta?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [shell])

  // Build the slash command list — each command is just a name + an
  // action callback. Adding new commands later means adding entries
  // to this array.
  const slashCommands: SlashCommand[] = useMemo(
    () => [
      {
        cmd: 'new',
        label: 'Ny chat',
        description: 'Start a fresh session',
        Icon: CommandIcons.Plus,
        action: () => shell.handleCreateSession?.(),
      },
      {
        cmd: 'anchor',
        label: 'Project anchor',
        description: 'Pick a project directory',
        Icon: CommandIcons.Folder,
        action: async () => {
          if (!window.jarvisx) return
          const result = await window.jarvisx.pickProjectRoot()
          if (result) onProjectChange({
            projectRoot: result.projectRoot,
            recentProjects: result.recentProjects,
          })
        },
      },
      {
        cmd: 'search',
        label: 'Cross-session search',
        description: 'Search all your past chats (Cmd-K)',
        Icon: CommandIcons.SearchIcon,
        action: () => setShowSearch(true),
      },
      {
        cmd: 'plan',
        label: 'Toggle plan mode',
        description: 'Plan-only mode — no edits without approval',
        Icon: CommandIcons.Layers,
        action: () => setPlanMode((p) => !p),
      },
      {
        cmd: 'capture',
        label: 'Screen capture',
        description: 'Grab a screen or window as image',
        Icon: CommandIcons.Mic,
        action: () => setShowCapture(true),
      },
      {
        cmd: 'export',
        label: 'Export session',
        description: 'Download current chat as markdown',
        Icon: CommandIcons.Download,
        action: () => {
          const sess = shell.activeSession as { messages?: Array<{ role: string; content: string }>; title?: string } | undefined
          if (!sess) return
          const lines = [`# ${sess.title || 'JarvisX session'}`, '']
          for (const m of sess.messages || []) {
            lines.push(`## ${m.role}`, '', m.content, '')
          }
          const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
          const url = URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.href = url
          a.download = `${(sess.title || 'session').replace(/[^\w-]+/g, '_')}.md`
          a.click()
          URL.revokeObjectURL(url)
        },
      },
      {
        cmd: 'tree',
        label: 'Toggle file tree',
        description: 'Show / hide the project file tree panel',
        Icon: CommandIcons.FileText,
        action: () => setShowFileTree((v) => !v),
      },
      {
        cmd: 'refresh',
        label: 'Refresh shell',
        description: 'Re-pull session list and surface state',
        Icon: CommandIcons.RefreshCw,
        action: () => (shell.refreshShell as undefined | (() => void))?.(),
      },
      {
        cmd: 'agents',
        label: 'Sub-agents panel',
        description: 'Toggle live view of dispatched sub-agents',
        Icon: CommandIcons.Layers,
        action: () => setShowAgents((v) => !v),
      },
      {
        cmd: 'tools',
        label: 'Tool inventory',
        description: 'Browse all of Jarvis\'s registered tools',
        Icon: CommandIcons.FileText,
        action: () => setShowToolInventory(true),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [shell.handleCreateSession, shell.refreshShell, shell.activeSession, onProjectChange],
  )

  // File tree panel toggle — persisted to localStorage so the panel
  // stays in the state Bjørn left it in across reloads.
  const [showFileTree, setShowFileTree] = useState<boolean>(() => {
    try {
      return localStorage.getItem('jarvisx.show_file_tree') === '1'
    } catch {
      return false
    }
  })
  useEffect(() => {
    try {
      localStorage.setItem('jarvisx.show_file_tree', showFileTree ? '1' : '0')
    } catch { /* ignore */ }
  }, [showFileTree])

  // Detect "/" as first char in empty composer → open slash palette
  const slashSeenRef = useRef(false)
  useEffect(() => {
    if (draft === '/' && !slashSeenRef.current) {
      slashSeenRef.current = true
      setShowSlashPalette(true)
      setDraft('')
    } else if (draft !== '/' && slashSeenRef.current) {
      slashSeenRef.current = false
    }
  }, [draft])

  // Auto-flush the queued message when streaming finishes — same pattern
  // as the original ChatPage. Lets the user keep typing while Jarvis is
  // still answering.
  const isStreaming = !!shell.isStreaming
  useEffect(() => {
    if (!isStreaming && queuedMessage && shell.handleSend) {
      const { msg, opts } = queuedMessage
      setQueuedMessage(null)
      const send = shell.handleSend as (m: string, o?: unknown) => void
      // Defer one tick so React flushes the streaming-end state first
      setTimeout(() => send(msg, opts), 0)
    }
  }, [isStreaming, queuedMessage, shell.handleSend])

  // Trim active session's messages to the most recent MESSAGE_WINDOW.
  const trimmedMessages = useMemo(() => {
    const s = shell.activeSession
    if (!s || !Array.isArray(s.messages)) return []
    if (s.messages.length <= MESSAGE_WINDOW) return s.messages
    return s.messages.slice(-MESSAGE_WINDOW)
  }, [shell.activeSession])

  const sessionTitle = (shell.activeSession?.title as string) || ''

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Top toolbar — affordances above the chat surface */}
      <header className="flex flex-shrink-0 items-center justify-between border-b border-line bg-bg1 px-4 py-2">
        <div className="flex min-w-0 items-center gap-3">
          <h2 className="flex-shrink-0 text-sm font-semibold">Chat</h2>
          <ProjectAnchor
            projectRoot={projectRoot}
            recentProjects={recentProjects}
            onChange={onProjectChange}
          />
        </div>
        <div className="flex flex-shrink-0 items-center gap-3 font-mono text-[10px] text-fg3">
          <ConnectionPill apiBaseUrl={apiBaseUrl} />
          <MoodPill apiBaseUrl={apiBaseUrl} />
          <PresencePill apiBaseUrl={apiBaseUrl} />
          <OutputStylePill apiBaseUrl={apiBaseUrl} />
          <TokenPill
            lastRunTokens={shell.lastRunTokens as { total_tokens?: number } | undefined}
            streamingTokenEstimate={shell.streamingTokenEstimate as number | undefined}
          />
          <button
            onClick={() => setShowSearch(true)}
            title="Search across sessions (Ctrl/Cmd-K)"
            className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
          >
            <SearchIcon size={12} />
          </button>
          <button
            onClick={() => setPreviewOpen((v) => !v)}
            title={previewOpen ? 'Skjul file preview' : 'Vis file preview'}
            className={[
              'flex h-6 w-6 items-center justify-center rounded transition-colors',
              previewOpen
                ? 'bg-accent/15 text-accent ring-1 ring-accent/30'
                : 'text-fg3 hover:bg-bg2 hover:text-fg',
            ].join(' ')}
          >
            <FileText size={12} />
          </button>
          <button
            onClick={() => setTerminalOpen((v) => !v)}
            title={terminalOpen ? 'Skjul terminal (Ctrl+J)' : 'Vis terminal (Ctrl+J)'}
            className={[
              'flex h-6 w-6 items-center justify-center rounded transition-colors',
              terminalOpen
                ? 'bg-accent/15 text-accent ring-1 ring-accent/30'
                : 'text-fg3 hover:bg-bg2 hover:text-fg',
            ].join(' ')}
          >
            <TerminalIcon size={12} />
          </button>
          {window.jarvisx && (
            <button
              onClick={() => setShowCapture(true)}
              title="Capture screen / window"
              className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-accent"
            >
              <Camera size={12} />
            </button>
          )}
          <VoiceButton />
          <button
            onClick={() => setShowToolInventory(true)}
            title="Tool inventory"
            className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
          >
            <Wrench size={12} />
          </button>
          <button
            onClick={() => setShowAgents((v) => !v)}
            title={showAgents ? 'Skjul sub-agents panel' : 'Vis sub-agents panel'}
            className={[
              'flex h-6 w-6 items-center justify-center rounded transition-colors',
              showAgents
                ? 'bg-accent/15 text-accent ring-1 ring-accent/30'
                : 'text-fg3 hover:bg-bg2 hover:text-fg',
            ].join(' ')}
          >
            <Bot size={12} />
          </button>
          <button
            onClick={() => setPlanMode((p) => !p)}
            title={planMode ? 'Plan mode aktivt — slå fra' : 'Aktivér plan mode'}
            className={[
              'flex h-6 w-6 items-center justify-center rounded transition-colors',
              planMode
                ? 'bg-warn/20 text-warn ring-1 ring-warn/40'
                : 'text-fg3 hover:bg-bg2 hover:text-fg',
            ].join(' ')}
          >
            <Pencil size={12} />
          </button>
          {projectRoot && (
            <button
              onClick={() => setShowFileTree((v) => !v)}
              title={showFileTree ? 'Skjul fil-træ' : 'Vis fil-træ'}
              className={[
                'flex h-6 w-6 items-center justify-center rounded transition-colors',
                showFileTree
                  ? 'bg-accent/15 text-accent ring-1 ring-accent/30'
                  : 'text-fg3 hover:bg-bg2 hover:text-fg',
              ].join(' ')}
            >
              {showFileTree ? <PanelRightClose size={12} /> : <PanelRightOpen size={12} />}
            </button>
          )}
          <span className="opacity-50">{apiBaseUrl}</span>
          <span>
            som <span className="text-accent">{userName}</span>
            <span className="ml-2 opacity-50">{userId.slice(0, 8)}…</span>
          </span>
        </div>
      </header>

      <TodoPanel
        apiBaseUrl={apiBaseUrl}
        sessionId={(shell.activeSessionId ?? null) as string | null}
      />
      <StagedEditsStrip
        apiBaseUrl={apiBaseUrl}
        sessionId={(shell.activeSessionId ?? null) as string | null}
        onReview={() => setShowDiffReview(true)}
      />
      <PendingPlansStrip
        apiBaseUrl={apiBaseUrl}
        sessionId={(shell.activeSessionId ?? null) as string | null}
        isOwner={role === 'owner'}
      />
      <TaskBar
        apiBaseUrl={apiBaseUrl}
        projectRoot={projectRoot}
        isOwner={role === 'owner'}
      />
      <PinnedStrip />
      {planMode && (
        <div className="flex flex-shrink-0 items-center gap-2 border-b border-warn/30 bg-warn/10 px-4 py-1.5">
          <Pencil size={11} className="text-warn" />
          <span className="text-[10px] font-semibold uppercase tracking-wider text-warn">
            Plan mode active
          </span>
          <span className="text-[10px] text-fg2">
            Jarvis vil planlægge før han ændrer noget. Klik blyanten for at slå fra.
          </span>
        </div>
      )}

      {/* Chat surface + optional right-side file tree panel */}
      <div className="flex h-full min-h-0 flex-1 overflow-hidden">
        <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
          {/* Diff review overlay — absolute fills this column when open
              so chat list + composer get fully replaced by the review
              experience (focused activity), but sidebar + toolbar stay
              visible so context isn't lost. */}
          <DiffReviewPanel
            open={showDiffReview}
            onClose={() => setShowDiffReview(false)}
            apiBaseUrl={apiBaseUrl}
            sessionId={(shell.activeSessionId ?? null) as string | null}
          />
          {/* Per-session header: title + rename/delete */}
          {shell.activeSession && (
            <ChatHeader
              title={sessionTitle}
              onRename={(t) => shell.handleRenameSession?.(shell.activeSessionId, t)}
              onDelete={() => shell.handleDeleteSession?.(shell.activeSessionId)}
            />
          )}

          {/* Inline error banner */}
          {shell.error && (
            <div className="flex flex-shrink-0 items-center justify-between border-b border-danger/30 bg-danger/10 px-4 py-1.5 font-mono text-[10px] text-danger">
              <span className="truncate">{String(shell.error)}</span>
            </div>
          )}

          {/* Native message list */}
          <MessageList
            messages={trimmedMessages}
            workingSteps={shell.workingSteps as never}
            isStreaming={isStreaming}
            sessionId={(shell.activeSessionId ?? null) as string | null}
            onAction={async (a) => {
              if (a.type === 'retry') {
                if (a.userText.trim()) {
                  shell.handleSend?.(a.userText.trim())
                }
              } else if (a.type === 'edit-resend') {
                if (a.newText.trim()) {
                  shell.handleSend?.(a.newText.trim())
                }
              } else if (a.type === 'fork') {
                const sessionId = shell.activeSessionId
                if (!sessionId || !a.messageId) return
                try {
                  const res = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/sessions/fork`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      source_session_id: sessionId,
                      up_to_message_id: a.messageId,
                    }),
                  })
                  if (!res.ok) throw new Error(`HTTP ${res.status}`)
                  const j = await res.json()
                  if (j?.new_session_id) {
                    shell.handleSessionSelect?.(j.new_session_id)
                  }
                } catch (e) {
                  console.error('[fork] failed:', e)
                }
              }
            }}
          />

          {/* Terminal drawer — shows live output from any process Jarvis
              has spawned via process_supervisor. Sits between the
              message list and composer so it eats vertical space from
              the chat (the natural give) instead of overlaying anything. */}
          <TerminalDrawer
            open={terminalOpen}
            onClose={() => setTerminalOpen(false)}
            apiBaseUrl={apiBaseUrl}
            role={role}
          />

          {/* Composer — reused from apps/ui. The .jarvisx-composer-host
              wrapper class flips .composer-shell out of its
              `position: absolute` mode (which is correct for webchat's
              floating-over-transcript layout but wrong for native flex).
              No border-t here — composer-card has its own visual frame
              and a hard line cuts the chat surface in two. */}
          <div className="jarvisx-composer-host flex-shrink-0 bg-bg0">
            <Composer
              value={draft}
              onChange={setDraft}
              isStreaming={isStreaming}
              queuedMessage={queuedMessage}
              onClearQueued={() => setQueuedMessage(null)}
              onSend={(msg: string, opts?: unknown) => {
                // Inject plan-mode hint when active so Jarvis sees it
                // alongside whatever options the composer normally passes
                const mergedOpts =
                  planMode && typeof opts === 'object' && opts !== null
                    ? { ...(opts as Record<string, unknown>), planMode: true }
                    : planMode
                    ? { planMode: true }
                    : opts
                if (isStreaming) {
                  setQueuedMessage({ msg, opts: mergedOpts })
                  setDraft('')
                  return
                }
                ;(shell.handleSend as (m: string, o?: unknown) => void)?.(msg, mergedOpts)
                setDraft('')
              }}
              onCancel={shell.handleCancel}
              onSteer={(msg: string) => {
                if (shell.handleSteer) {
                  ;(shell.handleSteer as (m: string) => void)(msg)
                  setDraft('')
                }
              }}
              selection={shell.shell?.selection}
              onSelectionChange={shell.handleSelectionChange}
              lastRunTokens={shell.lastRunTokens}
              streamingTokenEstimate={shell.streamingTokenEstimate}
              sessionId={shell.activeSessionId}
            />
          </div>
        </div>

        {showFileTree && projectRoot && (
          <FileTreePanel
            apiBaseUrl={apiBaseUrl}
            projectRoot={projectRoot}
            onClose={() => setShowFileTree(false)}
          />
        )}
        {showAgents && (
          <AgentsPanel
            apiBaseUrl={apiBaseUrl}
            onClose={() => setShowAgents(false)}
          />
        )}
        <FilePreviewPane
          apiBaseUrl={apiBaseUrl}
          projectRoot={projectRoot}
          open={previewOpen}
          onClose={() => setPreviewOpen(false)}
          previewPath={previewPath}
        />
      </div>

      {showCapture && (
        <ScreenCaptureModal
          apiBaseUrl={apiBaseUrl}
          onClose={() => setShowCapture(false)}
          onCaptured={({ url, filename }) => {
            const evt = new CustomEvent('jarvisx:screencap-attached', {
              detail: { url, filename },
            })
            window.dispatchEvent(evt)
            try {
              navigator.clipboard?.writeText(`![${filename}](${url})`)
            } catch { /* ignore */ }
          }}
        />
      )}
      {showSearch && (
        <CrossSessionSearchModal
          apiBaseUrl={apiBaseUrl}
          onClose={() => setShowSearch(false)}
          onPick={(hit) => {
            shell.handleSessionSelect?.(hit.session_id)
            setShowSearch(false)
          }}
        />
      )}
      {showSlashPalette && (
        <SlashPalette
          commands={slashCommands}
          onClose={() => setShowSlashPalette(false)}
        />
      )}
      {showToolInventory && (
        <ToolInventoryModal
          apiBaseUrl={apiBaseUrl}
          onClose={() => setShowToolInventory(false)}
        />
      )}
    </div>
  )
}


const COMPACT_THRESHOLD = 40000

function TokenPill({
  lastRunTokens,
  streamingTokenEstimate,
}: {
  lastRunTokens?: { total_tokens?: number }
  streamingTokenEstimate?: number
}) {
  const last = lastRunTokens?.total_tokens || 0
  const stream = streamingTokenEstimate || 0
  const effective = stream > last ? stream : last
  if (effective <= 0) return null
  const pct = Math.min(1, effective / COMPACT_THRESHOLD)
  const tone =
    pct >= 0.95 ? '#f85149'
    : pct >= 0.75 ? '#d4963a'
    : pct >= 0.5 ? '#5ab8a0'
    : '#3fb950'
  const fmt = (n: number) =>
    n < 1000 ? String(n)
    : n < 1_000_000 ? `${(n / 1000).toFixed(n < 10000 ? 1 : 0)}k`
    : `${(n / 1_000_000).toFixed(1)}M`
  return (
    <div
      className="flex items-center gap-1.5"
      title={`${effective.toLocaleString()} / ${COMPACT_THRESHOLD.toLocaleString()} tokens used in last run · /compact threshold`}
    >
      <div
        className="relative h-1 w-16 overflow-hidden rounded-full"
        style={{ background: '#21262d' }}
      >
        <div
          className="h-full transition-all duration-500 ease-out"
          style={{
            width: `${pct * 100}%`,
            background: `linear-gradient(90deg, ${tone}80, ${tone})`,
          }}
        />
      </div>
      <span className="tabular-nums" style={{ color: tone }}>
        {fmt(effective)}
      </span>
    </div>
  )
}
