import { useEffect, useRef } from 'react'
import type { ApiConfig } from '../lib/api'
import type { Surface } from './shell/Sidebar'
import { usePanel } from '../hooks/usePanel'
import { getUiPanelPending, ackUiPanel } from '../lib/coworkApi'
import type { HighlightScope } from '../lib/fileTreeHighlight'
import { emitHighlight } from '../lib/fileTreeHighlight'
import { emitZone } from '../lib/coworkZone'

const POLL_MS = 4000

/** detail er en filsti hvis den er ÉT token uden mellemrum og slutter på en
 *  fil-endelse (fx 'docs/spec.md'). Ellers er detail bare en note → markdown. */
function _looksLikeFilePath(detail: string | undefined): boolean {
  const d = (detail || '').trim()
  return /^[^\s]+\.[a-z0-9]{1,6}$/i.test(d)
}

/**
 * UI-panel-kald (spec §8.2, Fase 6 #3, opdateret 2026-06-16 med scope).
 * Poller for pending panel-forespørgsler fra Jarvis (open_ui_panel-tool) og
 * åbner preview/højre-panelet — owner-sessioner auto-åbner uden godkendelse.
 *
 * For panel='file_tree': sender detail + scope til emitHighlight så CodeView
 * kan highlight i enten server-repoet (scope='repo') eller workstation
 * (scope='workstation').
 */
export function UiPanelWatcher({
  config,
  setSurface,
}: {
  config: ApiConfig | null
  setSurface: (s: Surface) => void
}) {
  const panel = usePanel()
  const busy = useRef(false)
  const openRef = useRef(panel.open_)
  openRef.current = panel.open_
  const closeRef = useRef(panel.close)
  closeRef.current = panel.close

  useEffect(() => {
    if (!config) return

    const tick = async () => {
      if (busy.current) return
      busy.current = true
      try {
        const res = await getUiPanelPending(config)
        for (const req of res) {
          // close — luk det åbne panel (uanset hvilket)
          if (req.action === 'close') {
            closeRef.current()
            await ackUiPanel(config, req.id)
            continue
          }

          // file_tree — Jarvis vil highlighte en fil i træet
          if (req.panel === 'file_tree') {
            setSurface('code')
            const scope: HighlightScope = req.scope === 'workstation' ? 'workstation' : 'repo'
            emitHighlight(req.detail || '', scope)
            await ackUiPanel(config, req.id)
            continue
          }

          // preview — åbn i preview-panelet
          const fp = (req.detail || '').trim()
          if (req.panel === 'preview' && fp) {
            setSurface('code')
            openRef.current(
              _looksLikeFilePath(fp)
                ? { kind: 'file', title: fp.split('/').pop() || fp, filePath: fp }
                : { kind: 'markdown', title: 'Jarvis åbnede et panel', content: fp },
            )
            await ackUiPanel(config, req.id)
            continue
          }

          // right — åbn i højre side-panel
          if (req.panel === 'right') {
            setSurface('code')
            openRef.current({
              kind: 'markdown',
              title: 'Jarvis åbnede et panel',
              content: req.detail || 'Jarvis bad om at åbne dette panel.',
            })
            await ackUiPanel(config, req.id)
            continue
          }

          // settings — skift til cowork + åbn settings-zone
          if (req.panel === 'settings') {
            setSurface('cowork')
            emitZone('settings')
            await ackUiPanel(config, req.id)
            continue
          }

          // files — default, åbn som markdown
          if (req.panel === 'files') {
            setSurface('code')
            openRef.current({
              kind: 'markdown',
              title: 'Jarvis åbnede et panel',
              content: req.detail || 'Jarvis bad om at åbne dette panel.',
            })
            await ackUiPanel(config, req.id)
            continue
          }

          // Hvis ingen match: ack alligevel så den ikke blokerer
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
  }, [config?.apiBaseUrl, config?.authToken, setSurface])

  return null
}
