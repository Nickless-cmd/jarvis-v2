import { useEffect, useRef } from 'react'
import type { ApiConfig } from '../lib/api'
import { usePanel } from '../hooks/usePanel'
import { getUiPanelPending, ackUiPanel } from '../lib/coworkApi'

/**
 * UI-panel-kald (spec §8.2, Fase 6 #3). Poller for pending panel-forespørgsler
 * fra Jarvis (open_ui_panel-tool) og åbner preview/højre-panelet — owner-session
 * auto-åbner uden approval-kort (§8.2). Renderes inde i <PanelProvider>.
 */
const POLL_MS = 4000

export function UiPanelWatcher({ config }: { config: ApiConfig | undefined }) {
  const panel = usePanel()
  const openRef = useRef(panel.open_)
  openRef.current = panel.open_
  const closeRef = useRef(panel.close)
  closeRef.current = panel.close
  const busy = useRef(false)

  useEffect(() => {
    if (!config) return
    const tick = async () => {
      if (busy.current) return
      busy.current = true
      try {
        const pending = await getUiPanelPending(config)
        for (const req of pending) {
          if (req.action === 'close') {
            closeRef.current()
          } else {
            openRef.current({
              kind: 'markdown',
              title: 'Jarvis åbnede et panel',
              content: req.detail || 'Jarvis bad om at åbne dette panel.',
            })
          }
          await ackUiPanel(config, req.id)
        }
      } catch {
        /* polling-fallback — prøv igen næste tick */
      } finally {
        busy.current = false
      }
    }
    void tick()
    const id = setInterval(() => void tick(), POLL_MS)
    return () => clearInterval(id)
  }, [config?.apiBaseUrl, config?.authToken])

  return null
}
