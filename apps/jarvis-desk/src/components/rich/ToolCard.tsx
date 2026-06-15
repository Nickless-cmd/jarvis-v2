import { useState } from 'react'
import { Check, X, Loader } from 'lucide-react'
import type { ContentBlock } from '../../lib/sseProtocol'
import { lineDiff } from '../../lib/diff'
import { lookupTool } from '../../lib/toolRegistry'
import { diffStat } from '../../lib/diffStat'

/** Density-aware, værktøjs-specifik tool-kald-visning (Claude Desktop-stil).
 *  bash → terminal-blok, write/edit → fil-header + diff, read/glob/grep → kompakt.
 *  Argumenter og resultat rendres INERT via <pre> — aldrig markdown/HTML — så
 *  fjendtligt tool-output ikke kan injicere klikbare elementer. */
export function ToolCard({
  block,
  density,
}: {
  block: Extract<ContentBlock, { type: 'tool_use' }>
  density: 'compact' | 'full'
}) {
  const [open, setOpen] = useState(density === 'full')
  const expanded = density === 'full' || open

  const args = parseArgs(block)
  const fam = toolFamily(block.name)
  const meta = lookupTool(block.name)
  const summary = meta.summarize(args, block.result)
  const ds = diffStat(block.name, args)
  const status = block.status ?? 'running'
  const Icon = meta.Icon

  return (
    <div className={`toolcard fam-${fam} status-${status}`}>
      <button
        type="button"
        className="toolcard-head"
        onClick={() => density === 'compact' && setOpen((o) => !o)}
      >
        <Icon size={13} className="toolcard-icon" />
        <span className="toolcard-name">{meta.label}</span>
        {summary && <span className="toolcard-summary">{summary}</span>}
        {ds && (
          <span className="toolcard-diffstat">
            <span className="git-add">+{ds.add}</span> <span className="git-del">−{ds.del}</span>
          </span>
        )}
        <StatusBadge status={status} />
      </button>
      {expanded && (
        <div className="toolcard-body">
          {renderBody(fam, args, block.result)}
        </div>
      )}
    </div>
  )
}

type Fam = 'bash' | 'write' | 'edit' | 'read' | 'glob' | 'grep' | 'list' | 'other'

function toolFamily(name: string): Fam {
  const n = name.toLowerCase()
  if (n.includes('bash')) return 'bash'
  if (n.includes('write_file')) return 'write'
  if (n.includes('edit_file')) return 'edit'
  if (n.includes('read_file')) return 'read'
  if (n.includes('glob') || n.includes('find_files')) return 'glob'
  if (n.includes('grep') || n === 'search') return 'grep'
  if (n.includes('list_dir')) return 'list'
  return 'other'
}

function parseArgs(block: Extract<ContentBlock, { type: 'tool_use' }>): Record<string, unknown> {
  if (block.input && Object.keys(block.input).length) return block.input
  try { return JSON.parse(block.partialJson || '{}') } catch { return {} }
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'done') return <span className="toolcard-status ok"><Check size={11} /></span>
  if (status === 'error') return <span className="toolcard-status err"><X size={11} /></span>
  return <span className="toolcard-status run"><Loader size={11} /></span>
}

function renderBody(fam: Fam, args: Record<string, unknown>, result?: string) {
  if (fam === 'bash') {
    return (
      <div className="tc-term">
        <div className="tc-term-cmd">$ {String(args.command || '')}</div>
        {result && <pre className="tc-term-out">{result}</pre>}
      </div>
    )
  }
  if (fam === 'edit') {
    const oldS = String(args.old_string ?? args.old ?? '')
    const newS = String(args.new_string ?? args.new ?? '')
    if (oldS || newS) {
      const diff = lineDiff(oldS, newS)
      const add = diff.filter((d) => d.type === 'add').length
      const del = diff.filter((d) => d.type === 'del').length
      return (
        <div className="tc-diff">
          <div className="tc-diff-stat"><span className="git-add">+{add}</span> <span className="git-del">−{del}</span></div>
          <pre className="tc-diff-body">{diff.map((d, i) => (
            <div key={i} className={`tc-diff-line ${d.type}`}>{d.type === 'add' ? '+' : d.type === 'del' ? '−' : ' '} {d.text}</div>
          ))}</pre>
        </div>
      )
    }
  }
  if (fam === 'write') {
    const content = String(args.content ?? '')
    const lines = content ? content.split('\n').length : 0
    return (
      <div className="tc-write">
        <div className="tc-write-stat">Skrev {lines} linjer</div>
        {content && <pre className="tc-write-body">{content.length > 4000 ? content.slice(0, 4000) + '\n…' : content}</pre>}
      </div>
    )
  }
  // read / glob / grep / list / other: vis resultat (og args for 'other')
  return (
    <>
      {fam === 'other' && Object.keys(args).length > 0 && (
        <pre className="toolcard-args">{JSON.stringify(args, null, 2)}</pre>
      )}
      {result && <pre className="toolcard-result">{result}</pre>}
    </>
  )
}
