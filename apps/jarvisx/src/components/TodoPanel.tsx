import { useEffect, useState, useCallback } from 'react'
import { CheckCircle2, Circle, Loader2 } from 'lucide-react'

interface Todo {
  id: string
  content: string
  status: 'pending' | 'in_progress' | 'completed' | string
}

interface Props {
  apiBaseUrl: string
  sessionId: string | null
}

/**
 * Visible todo list — the same items Jarvis manages via todo_list/
 * todo_set/todo_update_status tools, surfaced in the chat surface so
 * Bjørn sees what Jarvis is working on. Polls every 4s; collapses if
 * the list is empty.
 *
 * Design note: this matches Claude Code's "TodoWrite shows the list at
 * the top of the chat" pattern — a passive read-out of Jarvis's
 * intentions for the current run.
 */
export function TodoPanel({ apiBaseUrl, sessionId }: Props) {
  const [todos, setTodos] = useState<Todo[]>([])
  const [collapsed, setCollapsed] = useState(false)

  const fetchTodos = useCallback(async () => {
    if (!sessionId) return
    try {
      const url = `${apiBaseUrl.replace(/\/$/, '')}/api/todos?session_id=${encodeURIComponent(
        sessionId,
      )}`
      const res = await fetch(url)
      if (!res.ok) return
      const j = await res.json()
      setTodos(j.todos || [])
    } catch { /* ignore */ }
  }, [apiBaseUrl, sessionId])

  useEffect(() => {
    fetchTodos()
    const id = window.setInterval(fetchTodos, 4000)
    return () => window.clearInterval(id)
  }, [fetchTodos])

  const toggleStatus = async (todo: Todo) => {
    if (!sessionId) return
    const next: Todo['status'] =
      todo.status === 'completed'
        ? 'pending'
        : todo.status === 'in_progress'
        ? 'completed'
        : 'in_progress'
    try {
      const url = `${apiBaseUrl.replace(/\/$/, '')}/api/todos/status`
      await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, todo_id: todo.id, status: next }),
      })
      void fetchTodos()
    } catch { /* ignore */ }
  }

  if (todos.length === 0) return null

  const inProgress = todos.filter((t) => t.status === 'in_progress').length
  const completed = todos.filter((t) => t.status === 'completed').length
  const pending = todos.filter((t) => t.status === 'pending').length

  return (
    <div className="flex flex-shrink-0 flex-col border-b border-accent/20 bg-accent/5">
      <button
        onClick={() => setCollapsed((c) => !c)}
        className="flex items-center gap-2 px-4 py-1.5 text-left hover:bg-accent/5"
      >
        <CheckCircle2 size={11} className="flex-shrink-0 text-accent" />
        <span className="text-[10px] font-semibold uppercase tracking-wider text-accent">
          Todos · {todos.length}
        </span>
        <span className="font-mono text-[10px] text-fg3">
          {completed > 0 && <span className="text-ok">{completed}✓</span>}
          {completed > 0 && (inProgress > 0 || pending > 0) && ' · '}
          {inProgress > 0 && <span className="text-warn">{inProgress} ⏵</span>}
          {inProgress > 0 && pending > 0 && ' · '}
          {pending > 0 && <span>{pending} pending</span>}
        </span>
        <span className="ml-auto font-mono text-[9px] text-fg3 opacity-50">
          {collapsed ? 'show' : 'hide'}
        </span>
      </button>
      {!collapsed && (
        <div className="max-h-[280px] overflow-y-auto px-4 pb-2">
          {todos.map((t) => (
            <button
              key={t.id}
              onClick={() => toggleStatus(t)}
              className={[
                'flex w-full items-start gap-2 rounded px-2 py-1 text-left text-[12px] transition-colors hover:bg-accent/10',
                t.status === 'completed' ? 'text-fg3 line-through' : 'text-fg2',
              ].join(' ')}
            >
              <span className="mt-0.5 flex-shrink-0">
                {t.status === 'completed' ? (
                  <CheckCircle2 size={11} className="text-ok" />
                ) : t.status === 'in_progress' ? (
                  <Loader2 size={11} className="animate-spin text-warn" />
                ) : (
                  <Circle size={11} className="text-fg3" />
                )}
              </span>
              <span className="flex-1 leading-snug">{t.content}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
