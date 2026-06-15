import { useEffect, useRef } from 'react'
import type { ApiConfig } from '../lib/api'
import type { Surface } from './shell/Sidebar'
import { usePanel } from '../hooks/usePanel'
import { getUiPanelPending, ackUiPanel } from '../lib/coworkApi'
import { emitHighlight } from '../lib/fileTreeHighlight'
import { emitZone } from '../lib/coworkZone'

/**
 * UI-panel-kald (spec §8.2, Fase 6 #3). Poller for pending panel-forespørgsler
 * fra Jarvis (open_ui_panel-tool) og åbner preview/højre-panelet — owner-session
 * auto-åbner uden approval-kort (§8.2). Renderes inde i <PanelProvider>.
 *
 * panel="file_tree" er Jarvis-styret highlight: skift til code-mode + emit stien
 * til fil-træet (CodeView abonnerer), så han kan pege på en fil brugeren leder
 * efter (file-tree-control-spec 2026-06-15).
 */
const POLL_MS = 4000

/** En `detail` der ligner en repo-relativ filsti (ingen mellemrum, ender på en
 *  fil-endelse) → vis filen i preview. Ellers er detail bare en note. */
function _looksLikeFilePath(detail: string | undefined): boolean {
  const d = (detail || '').trim()
  return /^[^\s]+\.[a-z0-9]{1,6}$/i.test(d)
}

export function UiPanelWatcher({
  config, setSurface,
}: { config: ApiConfig | undefined; setSurface?: (s: Surface) => void }) {
  const panel = usePanel()
  const openRef = useRef(panel.open_)
  openRef.current = panel.open_
  const closeRef = useRef(panel.close)
  closeRef.current = panel.close
  const surfaceRef = useRef(setSurface)
  surfaceRef.current = setSurface
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
          } else if (req.panel === 'settings') {
            // Jarvis åbner cowork-indstillinger (§5): skift surface + vis settings-zonen.
            surfaceRef.current?.('cowork')
            emitZone('settings')
          } else if (req.panel === 'file_tree') {
            // Jarvis-styret highlight: vis code-mode + scroll-til + markér filen.
            surfaceRef.current?.('code')
            if (req.detail) emitHighlight(req.detail)
          } else if (_looksLikeFilePath(req.detail)) {
            // preview/right med en filsti i detail → load+rendér FILEN (ikke bare
            // sti-teksten). Repo-relativ sti hentes via /chat/file (root='repo').
            const fp = req.detail.trim()
            openRef.current({
              kind: 'file',
              title: fp.split('/').pop() || fp,
              filePath: fp,
            })
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
