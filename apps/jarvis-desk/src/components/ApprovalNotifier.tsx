import { useEffect, useRef } from 'react'

/** OS-notifikation når Jarvis venter på en godkendelse (analyse §14.4).
 *  Prop-drevet → testbar. Fyrer kun ved overgang (ny approvalId), ikke ved re-render.
 *  Electron-siden (notify:taskDone) viser KUN notifikationen når vinduet ikke er i
 *  fokus + klik fokuserer vinduet — så her kaldes bare ubetinget ved ny approval. */
export function ApprovalNotifier({
  approvalId,
  tool,
  action,
  notify,
}: {
  approvalId: string | null
  tool?: string
  action?: string
  notify: (title: string, body: string) => void
}) {
  const lastRef = useRef<string | null>(null)

  useEffect(() => {
    if (approvalId && approvalId !== lastRef.current) {
      lastRef.current = approvalId
      const body = action ? `${tool}: ${action}`.slice(0, 140) : `${tool ?? 'En handling'} kræver din godkendelse`
      notify('Jarvis venter på din godkendelse', body)
    }
    if (!approvalId) lastRef.current = null
  }, [approvalId, tool, action, notify])

  return null
}
