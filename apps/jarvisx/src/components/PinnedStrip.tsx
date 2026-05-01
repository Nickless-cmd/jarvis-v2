import { Pin, X } from 'lucide-react'
import { usePinnedResults } from '../lib/usePinnedResults'

/**
 * Sticky strip above the chat showing pinned tool-result cards. Each
 * pin is a tiny chip with the result_id slug and summary; click → toggle
 * a popover preview that reuses the same /api/tool-result endpoint.
 *
 * For the first cut we keep it lightweight — chips with summary only.
 * Phase 2 idea: actually inject pinned results into Jarvis's prompt
 * context so HE keeps seeing them too. Requires a small backend change
 * to prompt_contract awareness section.
 */
export function PinnedStrip() {
  const { pins, unpin, clearAll } = usePinnedResults()

  if (pins.length === 0) return null

  return (
    <div className="flex flex-shrink-0 items-center gap-2 border-b border-line bg-bg1/60 px-4 py-1.5">
      <Pin size={11} className="flex-shrink-0 text-accent" />
      <span className="flex-shrink-0 text-[9px] font-semibold uppercase tracking-wider text-fg3">
        Pinned · {pins.length}
      </span>
      <div className="flex flex-1 items-center gap-1.5 overflow-x-auto">
        {pins.map((p) => (
          <PinnedChip
            key={p.resultId}
            resultId={p.resultId}
            summary={p.summary}
            onUnpin={() => unpin(p.resultId)}
          />
        ))}
      </div>
      <button
        onClick={clearAll}
        title="Unpin all"
        className="flex-shrink-0 text-[10px] text-fg3 hover:text-danger"
      >
        clear
      </button>
    </div>
  )
}

function PinnedChip({
  resultId,
  summary,
  onUnpin,
}: {
  resultId: string
  summary: string
  onUnpin: () => void
}) {
  // Try to extract `[tool_name]: rest` for compact label
  const m = summary.match(/^\[([\w_]+)\]:\s*(.*)$/)
  const tool = m?.[1] || 'tool'
  const rest = (m?.[2] || summary).slice(0, 80)
  const slug = resultId.slice(-6)
  return (
    <div
      className="group flex flex-shrink-0 items-center gap-1.5 rounded-md border border-accent/30 bg-accent/10 px-2 py-0.5 text-[10px] font-mono"
      title={`${resultId}\n${summary}`}
    >
      <span className="font-semibold text-accent">{tool}</span>
      {rest && <span className="max-w-[260px] truncate text-fg2">{rest}</span>}
      <span className="text-fg3 opacity-50">·{slug}</span>
      <button
        onClick={onUnpin}
        className="flex h-4 w-4 items-center justify-center rounded text-fg3 opacity-0 transition-opacity hover:text-danger group-hover:opacity-100"
        title="Unpin"
      >
        <X size={9} />
      </button>
    </div>
  )
}
