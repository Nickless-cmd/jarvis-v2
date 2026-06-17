import { useMemo, useState } from 'react'
import { lineDiff, type DiffLine } from '../../lib/diff'

/** Genbrugelig diff-viewer (analyse §5.5). Inline, farvekodet, med "kun ændringer".
 *  Ren præsentation oven på lib/diff.lineDiff — ingen netkald, ingen side-effekter.
 *  Wiring ind i ToolCard/approval (vis ændringer før accept) er en separat følge. */
export function DiffView({
  oldText,
  newText,
  filename,
}: {
  oldText: string
  newText: string
  filename?: string
}) {
  const [onlyChanges, setOnlyChanges] = useState(false)
  const lines = useMemo<DiffLine[]>(() => lineDiff(oldText, newText), [oldText, newText])
  const adds = lines.filter((l) => l.type === 'add').length
  const dels = lines.filter((l) => l.type === 'del').length
  const shown = onlyChanges ? lines.filter((l) => l.type !== 'same') : lines

  const gutter = (t: DiffLine['type']) => (t === 'add' ? '+' : t === 'del' ? '−' : ' ')

  return (
    <div className="diffview">
      <div className="diffview-head">
        {filename && <span className="diffview-file">{filename}</span>}
        <span className="diffview-stat">
          <span className="diffview-add">+{adds}</span> <span className="diffview-del">−{dels}</span>
        </span>
        <label className="diffview-toggle">
          <input type="checkbox" checked={onlyChanges} onChange={(e) => setOnlyChanges(e.target.checked)} />
          Kun ændringer
        </label>
      </div>
      <pre className="diffview-body">
        {shown.map((l, i) => (
          <div key={i} className={`diffline diffline-${l.type}`}>
            <span className="diffline-gutter">{gutter(l.type)}</span>
            <span className="diffline-text">{l.text || ' '}</span>
          </div>
        ))}
        {shown.length === 0 && <div className="diffview-empty">Ingen ændringer.</div>}
      </pre>
    </div>
  )
}
