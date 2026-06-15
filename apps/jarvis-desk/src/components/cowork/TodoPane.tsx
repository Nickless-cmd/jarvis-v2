import { useState } from 'react'
import { CircleCheck, CircleDot, Circle, Trash2, Pause, Play } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { createCoworkTodo, setCoworkTodoStatus, deleteCoworkTodo, setCoworkTodoExpiry } from '../../lib/coworkApi'

export interface TodoItem { id: string; content: string; status: string; expires_at?: string }

const NEXT: Record<string, string> = { pending: 'in_progress', in_progress: 'completed', completed: 'pending' }
const TTL_MS: Record<string, number | null> = { none: null, hour: 3600e3, day: 86400e3, week: 604800e3 }

export function TodoPane({
  todos, config, onChanged,
}: { todos: TodoItem[]; config?: ApiConfig; onChanged?: () => void }) {
  const [draft, setDraft] = useState('')
  const editable = !!config
  const after = () => { onChanged?.() }

  const submit = async () => {
    const c = draft.trim()
    if (!c || !config) return
    setDraft('')
    await createCoworkTodo(config, c); after()
  }
  const cycle = async (t: TodoItem) => {
    if (!config || t.status === 'expired') return
    await setCoworkTodoStatus(config, t.id, NEXT[t.status] || 'pending'); after()
  }
  const togglePause = async (t: TodoItem) => {
    if (!config) return
    await setCoworkTodoStatus(config, t.id, t.status === 'paused' ? 'pending' : 'paused'); after()
  }
  const remove = async (t: TodoItem) => {
    if (!config) return
    await deleteCoworkTodo(config, t.id); after()
  }
  const setTtl = async (t: TodoItem, key: string) => {
    if (!config) return
    const ms = TTL_MS[key]
    const iso = ms == null ? null : new Date(Date.now() + ms).toISOString()
    await setCoworkTodoExpiry(config, t.id, iso); after()
  }

  return (
    <div className="cowork-todos">
      {editable && (
        <input
          className="cowork-todo-input"
          placeholder="Ny opgave…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') void submit() }}
        />
      )}
      {todos.length === 0 && <div className="cowork-empty">Ingen opgaver</div>}
      {todos.map((t) => {
        const expired = t.status === 'expired'
        const Icon = t.status === 'completed' ? CircleCheck : t.status === 'in_progress' ? CircleDot : Circle
        return (
          <div key={t.id} className={`cowork-todo status-${t.status}`}>
            {editable && !expired
              ? <button type="button" className="todo-status-btn" aria-label="Skift status" onClick={() => void cycle(t)}><Icon size={15} /></button>
              : <Icon size={15} />}
            <span>{t.content}</span>
            {expired && <span className="todo-expired-tag">udløbet</span>}
            {editable && !expired && (
              <>
                <button type="button" className="todo-pause-btn"
                  aria-label={t.status === 'paused' ? 'Genoptag' : 'Pause'} onClick={() => void togglePause(t)}>
                  {t.status === 'paused' ? <Play size={13} /> : <Pause size={13} />}
                </button>
                <select className="todo-ttl" aria-label="Udløb"
                  value={t.expires_at ? 'custom' : 'none'} onChange={(e) => void setTtl(t, e.target.value)}>
                  <option value="none">Intet udløb</option>
                  {t.expires_at && <option value="custom">Udløber…</option>}
                  <option value="hour">1 time</option>
                  <option value="day">1 dag</option>
                  <option value="week">1 uge</option>
                </select>
              </>
            )}
            {editable && (
              <button type="button" className="todo-del-btn" aria-label="Slet" onClick={() => void remove(t)}>
                <Trash2 size={13} />
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}
