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
  // Lukningen skal bære sin egen begrundelse (16/10-2026): `completed` kræver
  // hvad der blev gjort, `dismissed` hvorfor den ikke skal løses. Serveren
  // afviser ellers — se `bekraeft`.
  const [lukker, setLukker] = useState<{ id: string; beslutning: 'completed' | 'dismissed' } | null>(null)
  const [tekst, setTekst] = useState('')

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

  /** Åbn lukke-formen. Den lukker IKKE selv — se `bekraeft`. */
  const aabnLuk = (t: SideTask, beslutning: 'completed' | 'dismissed') => {
    setFejl('')
    setTekst('')
    setLukker({ id: t.side_task_id, beslutning })
  }

  /**
   * Luk opgaven — med den begrundelse serveren kræver (16/10-2026).
   *
   * Bjørn: «Krav ved completed — men dismissed med begrundelse er altid en vej
   * ud». Et tomt felt er ikke en begrundelse, og et afvist kald ville se ud som
   * om knappen ikke virkede; derfor fanges det her først.
   */
  const bekraeft = async (t: SideTask) => {
    if (!config || travl || !lukker || lukker.id !== t.side_task_id) return
    const ord = tekst.trim()
    if (ord.length < 10) {
      setFejl(lukker.beslutning === 'completed'
        ? 'Skriv hvad der faktisk blev gjort — lukningen skal kunne efterprøves.'
        : 'Skriv hvorfor opgaven ikke skal løses.')
      return
    }
    setTravl(t.side_task_id)
    try {
      await setSideTaskStatus(config, t.side_task_id, lukker.beslutning,
        lukker.beslutning === 'completed' ? { bevis: ord } : { reason: ord })
      setLukker(null); setTekst('')
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
            {t.bevis ? <p className="sop-bevis">Bevis: {t.bevis}</p> : null}
            {t.dismiss_reason ? <p className="sop-bevis">Grund: {t.dismiss_reason}</p> : null}
            {t.status === 'pending' || t.status === 'queued' || t.status === 'activated' ? (
              lukker?.id === t.side_task_id ? (
                <div className="sop-lukform">
                  <label className="sop-luklabel" htmlFor={`sop-begrundelse-${t.side_task_id}`}>
                    {lukker.beslutning === 'completed'
                      ? 'Hvad blev gjort? (beviset gemmes på opgaven)'
                      : 'Hvorfor skal den ikke løses?'}
                  </label>
                  <textarea id={`sop-begrundelse-${t.side_task_id}`} className="sop-begrundelse" rows={2}
                            value={tekst}
                            placeholder={lukker.beslutning === 'completed'
                              ? 'fx commit 0ddcd976b — docs regenereret'
                              : 'fx ikke længere relevant efter 8d88ab530'}
                            onChange={(e) => setTekst(e.target.value)} />
                  <div className="sop-knapper">
                    <button type="button" disabled={travl === t.side_task_id}
                            onClick={() => void bekraeft(t)}>
                      {lukker.beslutning === 'completed' ? 'Bekræft færdig' : 'Bekræft fjern'}
                    </button>
                    <button type="button" disabled={travl === t.side_task_id}
                            onClick={() => { setLukker(null); setTekst('') }}>Annullér</button>
                  </div>
                </div>
              ) : (
                <div className="sop-knapper">
                  <button type="button" disabled={travl === t.side_task_id}
                          onClick={() => aabnLuk(t, 'completed')}>Markér færdig</button>
                  <button type="button" disabled={travl === t.side_task_id}
                          onClick={() => aabnLuk(t, 'dismissed')}>Fjern</button>
                </div>
              )
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  )
}
