import { useState } from 'react'
import { CircleCheck, CircleDot, Circle, Trash2 } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { createCoworkTodo, setCoworkTodoStatus, deleteCoworkTodo } from '../../lib/coworkApi'

export interface TodoItem { id: string; content: string; status: string }

const NEXT: Record<string, string> = { pending: 'in_progress', in_progress: 'completed', completed: 'pending' }

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
    await createCoworkTodo(config, c)
    after()
  }
  const cycle = async (t: TodoItem) => {
    if (!config) return
    await setCoworkTodoStatus(config, t.id, NEXT[t.status] || 'pending')
    after()
  }
  const remove = async (t: TodoItem) => {
    if (!config) return
    await deleteCoworkTodo(config, t.id)
    after()
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
        const Icon = t.status === 'completed' ? CircleCheck : t.status === 'in_progress' ? CircleDot : Circle
        return (
          <div key={t.id} className={`cowork-todo status-${t.status}`}>
            {editable
              ? <button type="button" className="todo-status-btn" aria-label="Skift status" onClick={() => void cycle(t)}><Icon size={15} /></button>
              : <Icon size={15} />}
            <span>{t.content}</span>
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
