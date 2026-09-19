import { useEffect, useRef, useState } from 'react'
import { ChevronDown, ChevronLeft, ChevronRight, X } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import { getSideTasks, setSideTaskStatus, type SideTask } from '../../lib/sideTasksApi'
import '../../styles/side-tasks.css'

export const POLL_MS = 6000

/** Hvad fladen kan gøre med en opgave. `worktree` findes kun hvor der er et
 *  git-arbejdsområde at lave den i (code-fladen på en mappe). */
export interface SideOpgaveHandlinger {
  startLokalt: (t: SideTask) => Promise<void>
  baggrund: (t: SideTask) => Promise<void>
  loesHer: (t: SideTask) => void | Promise<void>
  worktree?: (t: SideTask) => Promise<void>
}

type Valg = 'worktree' | 'lokalt' | 'baggrund' | 'her' | 'faerdig'

const NAVN: Record<Valg, string> = {
  worktree: 'Start i worktree',
  lokalt: 'Start i ny samtale',
  baggrund: 'Send til baggrunden',
  her: 'Løs i denne samtale',
  faerdig: 'Markér som færdig',
}

/**
 * Jarvis' flaggede sideopgaver som Claude Desktops «Suggested task»-kort
 * (Bjørn 19/9-2026: «som på billederne … og samme muligheder»).
 *
 * Et kort ad gangen, stablet når der er flere, med bladring (‹ 2 af 3 ›).
 * × fjerner opgaven. Knappen til højre starter den; pilen ved siden af har
 * resten: ny samtale, baggrunden (CC's «Send to cloud» — Jarvis arbejder
 * alene på serveren), løs i denne samtale, og markér som færdig.
 *
 * Kortet ligger oven over inputfeltet i BÅDE chat og code, tom og aktiv
 * samtale. Første udgave sad kun i chat — og Bjørn stod i code, så en
 * opgave Jarvis havde flagget, var usynlig.
 *
 * Serveren er eneste sandhed: hentes ved montering og hvert 6. sekund;
 * netværksfejl beholder sidst kendte; 403 (ikke ejer) viser intet og
 * spørger ikke igen.
 */
export function SideOpgaveKort({ config, handlinger }: { config: ApiConfig | null; handlinger: SideOpgaveHandlinger }) {
  const [opgaver, setOpgaver] = useState<SideTask[]>([])
  const [i, setI] = useState(0)
  const [menu, setMenu] = useState(false)
  const [travl, setTravl] = useState(false)
  const [fejl, setFejl] = useState('')
  const forbudt = useRef(false)
  const rod = useRef<HTMLDivElement>(null)

  const hent = async (cfg: ApiConfig) => {
    if (forbudt.current) return
    try {
      setOpgaver(await getSideTasks(cfg))
    } catch (e) {
      if (/\b403\b/.test(e instanceof Error ? e.message : '')) { forbudt.current = true; setOpgaver([]) }
    }
  }

  useEffect(() => {
    if (!config) return
    forbudt.current = false
    void hent(config)
    const id = setInterval(() => void hent(config), POLL_MS)
    return () => clearInterval(id)
  }, [config?.apiBaseUrl, config?.authToken]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!menu) return
    const luk = (e: MouseEvent) => { if (!rod.current?.contains(e.target as Node)) setMenu(false) }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setMenu(false) }
    document.addEventListener('mousedown', luk)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', luk); document.removeEventListener('keydown', esc) }
  }, [menu])

  if (opgaver.length === 0) return null
  const n = opgaver.length
  const idx = Math.min(i, n - 1)
  const t = opgaver[idx]!
  const standard: Valg = handlinger.worktree ? 'worktree' : 'lokalt'
  const valg: Valg[] = [...(handlinger.worktree ? ['worktree' as const] : []), 'lokalt', 'baggrund', 'her']

  const udfoer = async (v: Valg) => {
    if (!config || travl) return
    setMenu(false); setTravl(true); setFejl('')
    try {
      if (v === 'faerdig') {
        await setSideTaskStatus(config, t.side_task_id, 'completed')
        setOpgaver((l) => l.filter((x) => x.side_task_id !== t.side_task_id))
      } else {
        if (v === 'worktree') await handlinger.worktree!(t)
        else if (v === 'lokalt') await handlinger.startLokalt(t)
        else if (v === 'baggrund') await handlinger.baggrund(t)
        else await handlinger.loesHer(t)
        // Startet = i gang. Den bliver stående til nogen afslutter den.
        if (t.status !== 'activated') {
          await setSideTaskStatus(config, t.side_task_id, 'activated')
          setOpgaver((l) => l.map((x) => (x.side_task_id === t.side_task_id ? { ...x, status: 'activated' } : x)))
        }
      }
      void hent(config)
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'Det lykkedes ikke')
    } finally {
      setTravl(false)
    }
  }

  const fjern = async () => {
    if (!config || travl) return
    setTravl(true); setFejl('')
    try {
      await setSideTaskStatus(config, t.side_task_id, 'dismissed')
      setOpgaver((l) => l.filter((x) => x.side_task_id !== t.side_task_id))
      void hent(config)
    } catch (e) {
      setFejl(e instanceof Error ? e.message : 'Kunne ikke fjerne opgaven')
    } finally {
      setTravl(false)
    }
  }

  const beskrivelse = t.tldr || t.prompt
  return (
    <div className="sok-dok" ref={rod}>
      <section className={`sok${n > 1 ? ' sok-stak' : ''}`} aria-label="Sideopgave" data-testid="side-tasks" aria-busy={travl}>
        <div className="sok-top">
          <span className="sok-overskrift">Sideopgave{t.status === 'activated' ? <span className="sok-igang">i gang</span> : null}</span>
          <button type="button" className="sok-luk" aria-label="Fjern sideopgaven" title="Fjern sideopgaven" disabled={travl} onClick={() => void fjern()}>
            <X size={15} />
          </button>
        </div>
        <h4 className="sok-titel">{t.title}</h4>
        <p className="sok-tekst" title={t.prompt}>{beskrivelse}</p>
        {fejl ? <p className="sok-fejl" role="alert">{fejl}</p> : null}
        <div className="sok-fod">
          <div className="sok-blad" aria-label="Bladr i sideopgaverne">
            <button type="button" aria-label="Forrige sideopgave" disabled={idx === 0} onClick={() => setI(idx - 1)}><ChevronLeft size={15} /></button>
            <span>{idx + 1} af {n}</span>
            <button type="button" aria-label="Næste sideopgave" disabled={idx >= n - 1} onClick={() => setI(idx + 1)}><ChevronRight size={15} /></button>
          </div>
          <div className="sok-delt">
            <button type="button" className="sok-start" disabled={travl} onClick={() => void udfoer(standard)}>
              {travl ? 'Starter…' : NAVN[standard]}
            </button>
            <button type="button" className="sok-pil" aria-label="Flere valg" aria-haspopup="menu" aria-expanded={menu} disabled={travl} onClick={() => setMenu((m) => !m)}>
              <ChevronDown size={14} />
            </button>
            {menu ? (
              <div className="sok-menu" role="menu">
                {valg.map((v) => (
                  <button key={v} type="button" role="menuitem" onClick={() => void udfoer(v)}>
                    <span>{NAVN[v]}</span>
                    {v === standard ? <span className="sok-standard">Standard</span> : null}
                  </button>
                ))}
                <div className="sok-skille" role="separator" />
                <button type="button" role="menuitem" onClick={() => void udfoer('faerdig')}>{NAVN.faerdig}</button>
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </div>
  )
}
