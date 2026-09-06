import { useCallback, useEffect, useRef, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import {
  getCoworkQueue, getMcRuns, spandForRun,
  type KoeSpand, type McRunRow, type QueueItem,
} from '../lib/coworkApi'

export interface KoeIndslag {
  id: string
  spand: KoeSpand
  titel: string
  detalje: string
  /** Hvor det kom fra — så man kan handle på det rigtige sted. */
  kilde: 'godkendelse' | 'run'
  raa: QueueItem | McRunRow
}

const TOMME: Record<KoeSpand, KoeIndslag[]> = {
  venter_paa_mig: [], aktiv: [], til_gennemsyn: [], fejlet: [], faerdig: [],
}

/**
 * Én kø over alt der venter, kører eller er faldet.
 *
 * Kilderne findes allerede — /cowork/queue (godkendelser, initiativer,
 * forslag) og /mc/runs (kørsler). Det der manglede var ét sted at se dem
 * SAMLET, sorteret efter hvad man kan gøre ved dem.
 *
 * Fejler den ene kilde, vises den anden. En tom kø fordi ét kald fejlede
 * ville få det til at se ud som om intet foregik — værre end en delvis liste.
 */
export function useWorkQueue(config: ApiConfig | undefined, pollMs = 8000) {
  const [spande, setSpande] = useState<Record<KoeSpand, KoeIndslag[]>>(TOMME)
  const [henter, setHenter] = useState(true)
  const [delvis, setDelvis] = useState<string | null>(null)
  const levendeRef = useRef(true)

  useEffect(() => {
    levendeRef.current = true
    return () => { levendeRef.current = false }
  }, [])

  const hent = useCallback(async () => {
    if (!config) return
    const næste: Record<KoeSpand, KoeIndslag[]> = {
      venter_paa_mig: [], aktiv: [], til_gennemsyn: [], fejlet: [], faerdig: [],
    }
    const problemer: string[] = []

    const [kø, runs] = await Promise.allSettled([
      getCoworkQueue(config),
      getMcRuns(config, 30),
    ])

    if (kø.status === 'fulfilled') {
      for (const q of kø.value) {
        næste.venter_paa_mig.push({
          id: `q:${q.id}`, spand: 'venter_paa_mig', titel: q.title,
          detalje: q.detail, kilde: 'godkendelse', raa: q,
        })
      }
    } else problemer.push('godkendelser')

    if (runs.status === 'fulfilled') {
      const alle = [runs.value.active_run, ...runs.value.recent_runs]
        .filter((r): r is McRunRow => Boolean(r))
      const set = new Set<string>()
      for (const r of alle) {
        if (set.has(r.run_id)) continue
        set.add(r.run_id)
        const spand = spandForRun(r.status)
        næste[spand].push({
          id: `r:${r.run_id}`, spand,
          titel: r.text_preview?.slice(0, 80) || r.run_id,
          detalje: [r.model, r.lane].filter(Boolean).join(' · '),
          kilde: 'run', raa: r,
        })
      }
    } else problemer.push('kørsler')

    if (!levendeRef.current) return
    setSpande(næste)
    setDelvis(problemer.length ? `Kunne ikke hente ${problemer.join(' og ')}` : null)
    setHenter(false)
  }, [config])

  useEffect(() => {
    void hent()
    const id = setInterval(() => void hent(), pollMs)
    return () => clearInterval(id)
  }, [hent, pollMs])

  const venter = spande.venter_paa_mig.length
  return { spande, henter, delvis, venter, genhent: hent }
}
