import type { StreamState } from './streamReducer'

/** A polled run is not evidence of a visible reply. In particular, the server
 * can keep a run registered briefly while it finishes its bookkeeping. */
export function remoteRunHasVisibleActivity(
  state: Pick<StreamState, 'status' | 'activeRunId' | 'blocks'>,
  runId: string | null,
): boolean {
  if (!runId || state.activeRunId !== runId || state.status !== 'working') return false
  return state.blocks.some((block) => {
    if (!block) return false
    if (block.type === 'tool_use' || block.type === 'image') return true
    if (block.type === 'text') return block.text.trim().length > 0
    if (block.type === 'thinking') return block.thinking.trim().length > 0
    return false
  })
}
