/**
 * Bro mellem en klikket reference i markdown og den flade der kan vise den.
 *
 * BAGGRUND (27/10-2026, Bjørn): `asg-…`, `wt-…`, `wake-…`, `run-…`,
 * `agent/asg-…` og filnavne som `sideOpgaveHighlight.ts` stod som grå
 * kode-badges — korrekt formateret, men døde. Kun `side-…` og commit-hashes var
 * klikbare. Han skulle kopiere id'et for at slå det op.
 *
 * Hvorfor en event og ikke en prop: `MarkdownBlok` er `memo`'et på strengen
 * (se MarkdownRenderer.tsx), så en ny prop ville bryde memoiseringen for hver
 * blok i hele transcriptet. Samme grund som `sideOpgaveHighlight.ts` og
 * `fileTreeHighlight.ts` bruger modul-niveau pub/sub — afsender (en <a> dybt i
 * et memo'et træ) og modtager (App, der ejer `setSurface`) deler ingen
 * provider-gren.
 *
 * Lytteren er `RefAabnHost` i App.tsx.
 */

import { useEffect } from 'react'
import type { RefKind } from './linkifyRefs'

export const REF_AABN_EVENT = 'jarvis:ref-aabn'

export type RefAabnDetail = { kind: RefKind; vaerdi: string }

/** Kaldes fra MarkdownRenderer's link-onClick. */
export function aabnRef(kind: RefKind, vaerdi: string): void {
  if (!vaerdi) return
  window.dispatchEvent(new CustomEvent<RefAabnDetail>(REF_AABN_EVENT, { detail: { kind, vaerdi } }))
}

/** Lyt på klik på en reference. Returnerer en unsubscribe. */
export function onRefAabn(lytter: (d: RefAabnDetail) => void): () => void {
  const wrap = (e: Event) => {
    const d = (e as CustomEvent<RefAabnDetail>).detail
    if (d?.kind && d.vaerdi) lytter(d)
  }
  window.addEventListener(REF_AABN_EVENT, wrap)
  return () => window.removeEventListener(REF_AABN_EVENT, wrap)
}

/** Åbn Jobs-panelet (Baggrundsjob) og fremhæv en række.
 *
 *  Agent-assignments og runs har allerede en flade: `AgentJobRows` i
 *  Jobs-panelet, med `AgentInspector` bag `onOpen`. Rækkerne kender deres
 *  `assignment_id` og `run_id`, så et id er nok til at finde den rette række.
 */
export const JOBS_AABN_EVENT = 'jarvis:jobs-aabn'

export type JobsAabnDetail = { id: string }

export function aabnJobs(id: string): void {
  window.dispatchEvent(new CustomEvent<JobsAabnDetail>(JOBS_AABN_EVENT, { detail: { id } }))
}

export function onJobsAabn(lytter: (id: string) => void): () => void {
  const wrap = (e: Event) => {
    const id = (e as CustomEvent<JobsAabnDetail>).detail?.id
    if (id) lytter(id)
  }
  window.addEventListener(JOBS_AABN_EVENT, wrap)
  return () => window.removeEventListener(JOBS_AABN_EVENT, wrap)
}

/** Åbn side-opgave-panelet fra et klik på en `side-…`-reference.
 *
 *  27/10-2026: `aabnSideOpgave` fandtes og blev kaldt — men INGEN lyttede på
 *  den for at ÅBNE panelet. `SideOpgaveListe` lyttede kun for at fremhæve en
 *  række, og den kører først når panelet allerede er åbent. Kommentaren i
 *  `sideOpgaveHighlight.ts` påstod at CodeView/ChatView lyttede; det gjorde de
 *  ikke (målt: grep gav kun SideOpgaveListe + testen). Et klik på en
 *  side-opgave-reference med lukket panel gjorde derfor intet synligt.
 */
export const SIDE_OPGAVE_AABN_PANEL_EVENT = 'jarvis:side-opgave-aabn-panel'

/** Hook til de to samtale-visninger: åbner det panel en reference peger på.
 *
 *  Panelerne ejes af lokal `usePersistedState` i hver visning, så de kan ikke
 *  sættes udefra — visningen selv må lytte. Én hook, brugt to steder, så
 *  adfærden ikke kan divergere mellem chat og code.
 */
export function useRefPanelLytting(handling: {
  sideopgave: () => void
  jobs: (id: string) => void
}): void {
  const { sideopgave, jobs } = handling
  useEffect(() => {
    const lytSide = () => sideopgave()
    const lytJobs = (e: Event) => {
      const id = (e as CustomEvent<JobsAabnDetail>).detail?.id
      if (id) jobs(id)
    }
    window.addEventListener(SIDE_OPGAVE_AABN_PANEL_EVENT, lytSide)
    window.addEventListener(JOBS_AABN_EVENT, lytJobs)
    return () => {
      window.removeEventListener(SIDE_OPGAVE_AABN_PANEL_EVENT, lytSide)
      window.removeEventListener(JOBS_AABN_EVENT, lytJobs)
    }
  }, [sideopgave, jobs])
}

/** Hvilken panel-flade en reference hører til, hvis nogen.
 *
 *  `wt-` og `wake-` har INGEN flade i desk endnu — de er ikke ruter og vises
 *  intetsteds. At rout'e dem til et tilfældigt panel ville være værre end at
 *  sige det højt, så de ender i preview-panelet med id'et, hvor det kan
 *  kopieres. (Målt 27/10-2026: grep for `wt-`/`wake-` i `src/` gav nul
 *  visninger ud over de netop tilføjede regexer.)
 */
export function fladeFor(kind: RefKind): 'jobs' | 'fil' | 'preview' | 'sideopgave' {
  switch (kind) {
    case 'agent':
    case 'run':
      return 'jobs'
    case 'fil':
      return 'fil'
    case 'sideopgave':
      return 'sideopgave'
    default:
      return 'preview'
  }
}
