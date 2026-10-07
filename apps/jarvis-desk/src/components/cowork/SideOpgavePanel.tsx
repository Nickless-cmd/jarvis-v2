import { useCallback, useEffect, useState } from 'react'
import { getAlleSideTasks, setSideTaskStatus, type SideTask } from '../../lib/sideTasksApi'
import type { ApiConfig } from '../../lib/api'

/**
 * Alle sideopgaver — også de lukkede.
 *
 * Bjørn 3/10-2026: «desk har ikk noget panel der viser opgaver der er flagged
 * selv om jeg har trykket dem væk». Kortet i chatten viser kun de ÅBNE, og
 * `/cowork/side-tasks` svarede kun med dem — så en lukket opgave forsvandt
 * sporløst.
 *
 * Målt samme dag: alle seks poster i hans fil var terminale, så kortet var
 * KORREKT tomt. Persistensen virkede (bevist med to processer); det var
 * visningen der ikke fandtes. Derfor kunne «lukket» ikke skelnes fra «blev den
 * nogensinde gemt?», og det er præcis hvad panelet her gør muligt.
 */
const STATUS_TEKST: Record<string, string> = {
  pending: 'Venter',
  queued: 'I kø',
  activated: 'I gang',
  completed: 'Færdig',
  dismissed: 'Fjernet',
}

function naar(iso?: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('da-DK', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function SideOpgavePanel({ config }: { config?: ApiConfig }) {
  const [opgaver, setOpgaver] = useState<SideTask[] | null>(null)
  const [fejl, setFejl] = useState('')
  const [travl, setTravl] = useState('')

  const hent = useCallback(async () => {
    if (!config) return
    try {
      setOpgaver(await getAlleSideTasks(config))
      setFejl('')
    } catch (e) {
      // Tom liste og en fejl er ikke det samme — og det var hele problemet.
      setFejl(e instanceof Error ? e.message : 'Kunne ikke hente sideopgaverne')
    }
  }, [config])

  useEffect(() => { void hent() }, [hent])

  const luk = async (t: SideTask, beslutning: 'completed' | 'dismissed') => {
    if (!config || travl) return
    setTravl(t.side_task_id)
    try {
      await setSideTaskStatus(config, t.side_task_id, beslutning)
      await hent()
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'Det lykkedes ikke')
    } finally {
      setTravl('')
    }
  }

  if (opgaver === null && !fejl) return <p className="settings-hint">Henter…</p>
  const aabne = (opgaver ?? []).filter((t) => t.status === 'pending' || t.status === 'queued' || t.status === 'activated')
  const lukkede = (opgaver ?? []).filter((t) => t.status === 'completed' || t.status === 'dismissed')

  return (
    <div className="sop" data-testid="side-opgave-panel">
      {fejl ? <p className="sop-fejl" role="alert">{fejl}</p> : null}
      <p className="settings-hint">
        {aabne.length} åbne · {lukkede.length} lukkede. En lukket opgave kan ikke genåbnes —
        den står her som spor.
      </p>
      {(opgaver ?? []).length === 0 && !fejl ? (
        <p className="settings-hint">Jarvis har ikke flagget nogen opgaver endnu.</p>
      ) : null}
      <ul className="sop-liste">
        {(opgaver ?? []).map((t) => (
          <li key={t.side_task_id} className={`sop-post sop-${t.status}`}>
            <div className="sop-top">
              <span className="sop-status">{STATUS_TEKST[t.status] ?? t.status}</span>
              <span className="sop-titel">{t.title}</span>
            </div>
            {t.tldr ? <p className="sop-tldr">{t.tldr}</p> : null}
            <p className="sop-meta">
              <span>flagget {naar(t.created_at)}</span>
              {t.resolved_at ? <span> · lukket {naar(t.resolved_at)}</span> : null}
              {t.lukket_af ? <span> · af {t.lukket_af}</span> : null}
              {t.arbejds_session ? <span> · arbejde i {t.arbejds_session.slice(0, 16)}…</span> : null}
              {t.arbejds_run_id ? <span> · run {t.arbejds_run_id.slice(0, 16)}…</span> : null}
            </p>
            {t.status === 'pending' || t.status === 'queued' || t.status === 'activated' ? (
              <div className="sop-knapper">
                <button type="button" disabled={travl === t.side_task_id}
                        onClick={() => void luk(t, 'completed')}>Markér færdig</button>
                <button type="button" disabled={travl === t.side_task_id}
                        onClick={() => void luk(t, 'dismissed')}>Fjern</button>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}
