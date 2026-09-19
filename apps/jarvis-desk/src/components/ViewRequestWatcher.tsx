import { useEffect, useRef } from 'react'
import { apiFetch, type ApiConfig } from '../lib/api'
import { skaermFor, type Panel } from '../lib/skaermRegister'

const POLL_MS = 1500

interface ViewRequest { id: string; op: 'get_layout' | 'show_pane' | 'close_pane'; args: Record<string, unknown>; session_id: string }

/**
 * Svarer på Jarvis' desk-værktøjer (Claude Desktops view-request-kanal,
 * korreleret på request-id). Serveren lægger en forespørgsel; vi udfører den
 * på skærmen og svarer med INDHOLD — layoutet, eller en fejltekst der siger
 * hvad der mangler.
 *
 * Et vindue der ikke viser samtalen, svarer IKKE: med desk åben på to
 * maskiner kunne det forkerte vindue ellers melde «ikke åben» først.
 * Værktøjets frist siger så ærligt at samtalen ikke er på skærmen.
 */
export function ViewRequestWatcher({ config }: { config: ApiConfig | null }) {
  const optaget = useRef(false)
  useEffect(() => {
    if (!config) return
    const tick = async () => {
      if (optaget.current || document.visibilityState !== 'visible') return
      optaget.current = true
      try {
        const { requests } = await apiFetch<{ requests: ViewRequest[] }>(config, '/ui/view-requests/pending')
        for (const r of requests ?? []) {
          const skaerm = skaermFor(r.session_id)
          if (!skaerm) continue
          const resultat = udfoer(r, skaerm)
          await apiFetch(config, `/ui/view-requests/${encodeURIComponent(r.id)}/svar`, { method: 'POST', body: { resultat } })
        }
      } catch { /* næste tick */ } finally { optaget.current = false }
    }
    void tick()
    const id = setInterval(() => void tick(), POLL_MS)
    return () => clearInterval(id)
  }, [config?.apiBaseUrl, config?.authToken]) // eslint-disable-line react-hooks/exhaustive-deps
  return null
}

/** Udfør én forespørgsel på den skærm der viser samtalen. Ren — testbar. */
export function udfoer(r: ViewRequest, skaerm: NonNullable<ReturnType<typeof skaermFor>>): Record<string, unknown> {
  const layout = () => ({ views: [{ placement: 'primary', surface: skaerm.flade }], open_panes: skaerm.aabne() })
  if (r.op === 'get_layout') return layout()
  const panel = String(r.args.pane ?? '') as Panel
  const fejl = r.op === 'show_pane'
    ? skaerm.vis(panel, { path: typeof r.args.path === 'string' ? r.args.path : undefined, line: typeof r.args.line === 'number' ? r.args.line : undefined })
    : skaerm.luk(panel)
  if (fejl) return { error: fejl }
  // React-tilstanden er ikke opdateret endnu i samme tick — svaret regnes ud
  // fra handlingen, så det lige åbnede panel står med (og det lukkede ikke).
  const foer = skaerm.aabne()
  const aabne = r.op === 'show_pane' ? [...new Set([...foer, panel])] : foer.filter((p) => p !== panel)
  return { ...layout(), open_panes: aabne }
}
