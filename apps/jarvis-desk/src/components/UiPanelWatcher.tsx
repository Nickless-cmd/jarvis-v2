import { useEffect, useRef } from 'react'
import type { ApiConfig } from '../lib/api'
import type { Surface } from './shell/Sidebar'
import { usePanel } from '../hooks/usePanel'
import { getUiPanelPending, ackUiPanel } from '../lib/coworkApi'
import type { HighlightScope } from '../lib/fileTreeHighlight'
import { emitHighlight } from '../lib/fileTreeHighlight'
import { emitZone } from '../lib/coworkZone'

const POLL_MS = 4000

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
  const { open_: openPanel } = usePanel()
  const busy = useRef(false)
  const openRef = useRef(openPanel)
  openRef.current = openPanel

  useEffect(() => {
    if (!config) return

    const tick = async () => {
      if (busy.current) return
      busy.current = true
      try {
        const res = await getUiPanelPending(config)
        for (const req of res) {
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
            openRef.current({
              kind: 'file',
              title: fp.split('/').pop() || fp,
              filePath: fp,
            })
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
