import { useEffect, useRef, useState } from 'react'
import { ChevronDown, ChevronRight, ListTodo } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { getSideTasks, setSideTaskStatus, type SideTask, type SideTaskAfslutning } from '../../lib/sideTasksApi'
import '../../styles/side-tasks.css'

export const POLL_MS = 6000

/**
 * Jarvis' flaggede sideopgaver, fast under chatheaderen (spec
 * desk-sideopgaver, 19/9-2026). Vises uanset hvilken samtale der er åben —
 * også i en tom — til Bjørn eller Jarvis afslutter dem. At flagge starter
 * intet arbejde; listen er en huskeseddel, ikke en kø.
 *
 * - Hentes ved montering og hvert 6. sekund.
 * - Netværksfejl: senest kendte liste bliver stående.
 * - Færdig/Fjern: rækken forsvinder straks ved succes; ved fejl bliver den
 *   stående med fejlen ved siden af.
 * - 403 (ikke ejer): intet vises, og der spørges ikke igen.
 */
export function SideTasksBar({ config }: { config: ApiConfig | null }) {
  const [opgaver, setOpgaver] = useState<SideTask[]>([])
  const [aaben, setAaben] = useState<Record<string, boolean>>({})
  const [fejl, setFejl] = useState<Record<string, string>>({})
  const [travl, setTravl] = useState<string | null>(null)
  const forbudt = useRef(false)

  const hent = async (cfg: ApiConfig) => {
    if (forbudt.current) return
    try {
      setOpgaver(await getSideTasks(cfg))
    } catch (e) {
      if (/\b403\b/.test(e instanceof Error ? e.message : '')) { forbudt.current = true; setOpgaver([]) }
      // ellers: behold senest kendte
    }
  }

  useEffect(() => {
    if (!config) return
    forbudt.current = false
    void hent(config)
    const id = setInterval(() => void hent(config), POLL_MS)
    return () => clearInterval(id)
  }, [config?.apiBaseUrl, config?.authToken]) // eslint-disable-line react-hooks/exhaustive-deps

  const afslut = async (id: string, status: SideTaskAfslutning) => {
    if (!config) return
    setTravl(id)
    setFejl((f) => { const n = { ...f }; delete n[id]; return n })
    try {
      await setSideTaskStatus(config, id, status)
      setOpgaver((l) => l.filter((t) => t.side_task_id !== id))
      void hent(config)
    } catch (e) {
      setFejl((f) => ({ ...f, [id]: e instanceof Error ? e.message : 'Kunne ikke opdatere' }))
    } finally {
      setTravl(null)
    }
  }

  if (opgaver.length === 0) return null
  return (
    <section className="side-tasks" aria-label="Sideopgaver" data-testid="side-tasks">
      <div className="side-tasks-head">
        <ListTodo size={14} strokeWidth={1.8} aria-hidden />
        <span>Sideopgaver</span>
        <span className="side-tasks-antal">{opgaver.length}</span>
      </div>
      <ul className="side-tasks-liste">
        {opgaver.map((t) => {
          const udfoldet = !!aaben[t.side_task_id]
          const optaget = travl === t.side_task_id
          return (
            <li key={t.side_task_id} className="side-task">
              <div className="side-task-linje">
                <button
                  type="button"
                  className="side-task-fold"
                  aria-expanded={udfoldet}
                  aria-label={`${udfoldet ? 'Skjul' : 'Vis'} detaljer for ${t.title}`}
                  onClick={() => setAaben((a) => ({ ...a, [t.side_task_id]: !udfoldet }))}
                >
                  {udfoldet ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                </button>
                <div className="side-task-tekst">
                  <span className="side-task-titel" title={t.title}>
                    {t.title}
                    {t.status === 'activated' ? <span className="side-task-igang">i gang</span> : null}
                  </span>
                  {t.tldr ? <span className="side-task-tldr" title={t.tldr}>{t.tldr}</span> : null}
                </div>
                <div className="side-task-knapper">
                  <button type="button" disabled={optaget} onClick={() => void afslut(t.side_task_id, 'completed')}>Færdig</button>
                  <button type="button" className="side-task-fjern" disabled={optaget} onClick={() => void afslut(t.side_task_id, 'dismissed')}>Fjern</button>
                </div>
              </div>
              {udfoldet ? <pre className="side-task-prompt">{t.prompt}</pre> : null}
              {fejl[t.side_task_id] ? <p className="side-task-fejl" role="alert">{fejl[t.side_task_id]}</p> : null}
            </li>
          )
        })}
      </ul>
    </section>
  )
}
