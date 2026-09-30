import type { StreamState } from './streamReducer'

/** A polled run is not evidence of a visible reply. In particular, the server
 * can keep a run registered briefly while it finishes its bookkeeping. */
export function remoteRunHasVisibleActivity(
  state: Pick<StreamState, 'status' | 'activeRunId' | 'blocks'>,
  runId: string | null,
): boolean {
  if (state.status !== 'working' || !state.activeRunId) return false
  // Older /active-runs responses omit run_id. They can still show genuine
  // followed content; only authoritative IDs can be compared exactly.
  if (runId && state.activeRunId !== runId) return false
  return state.blocks.some((block) => {
    if (!block) return false
    if (block.type === 'tool_use' || block.type === 'image') return true
    if (block.type === 'text') return block.text.trim().length > 0
    if (block.type === 'thinking') return block.thinking.trim().length > 0
    return false
  })
}
