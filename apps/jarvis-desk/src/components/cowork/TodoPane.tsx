import { CircleCheck, CircleDot, Circle } from 'lucide-react'

export interface TodoItem { id: string; content: string; status: string }

export function TodoPane({ todos }: { todos: TodoItem[] }) {
  if (todos.length === 0) return <div className="cowork-empty">Ingen opgaver</div>
  return (
    <div className="cowork-todos">
      {todos.map((t) => {
        const Icon = t.status === 'completed' ? CircleCheck : t.status === 'in_progress' ? CircleDot : Circle
        return (
          <div key={t.id} className={`cowork-todo status-${t.status}`}>
            <Icon size={15} /> <span>{t.content}</span>
          </div>
        )
      })}
    </div>
  )
}
