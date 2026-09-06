import { useCallback, useMemo, useRef, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import { apiFetch } from '../lib/api'
import { listProjectFiles, type ProjectFil } from '../lib/projectApi'
import {
  findAktivMention, indsætMention, rangerFiler, type AktivMention,
} from '../lib/fileMention'

/** @fil-komplettering i komposeren.
 *
 *  Indekset hentes først når brugeren rent faktisk skriver '@' — det er
 *  tusindvis af stier, og de fleste beskeder nævner ingen fil. Roden læses
 *  fra serveren i stedet for at stå hardkodet i klienten.
 */
export function useFileMention(config: ApiConfig | undefined, aktiveret: boolean) {
  const [filer, setFiler] = useState<ProjectFil[]>([])
  const [mention, setMention] = useState<AktivMention | null>(null)
  const [valgt, setValgt] = useState(0)
  const henter = useRef(false)
  const fejlet = useRef(false)

  const hentIndeks = useCallback(async () => {
    if (!config || henter.current || fejlet.current || filer.length > 0) return
    henter.current = true
    try {
      const g = await apiFetch<{ workspace?: string }>(config, '/system/git')
      const rod = g.workspace
      if (!rod) { fejlet.current = true; return }
      setFiler(await listProjectFiles(config, rod))
    } catch {
      // Ingen liste er bedre end en fejlboble midt i indtastningen; @ opfører
      // sig så bare som almindelig tekst.
      fejlet.current = true
    } finally {
      henter.current = false
    }
  }, [config, filer.length])

  /** Kaldes ved hvert input/caret-flyt. */
  const opdater = useCallback((tekst: string, caret: number) => {
    if (!aktiveret) { setMention(null); return }
    const m = findAktivMention(tekst, caret)
    setMention(m)
    setValgt(0)
    if (m) void hentIndeks()
  }, [aktiveret, hentIndeks])

  const forslag = useMemo(
    () => (mention ? rangerFiler(filer, mention.query) : []),
    [filer, mention],
  )
  const åben = mention !== null && forslag.length > 0

  const luk = useCallback(() => setMention(null), [])
  const flyt = useCallback((d: number) => {
    setValgt((v) => (forslag.length === 0 ? 0 : (v + d + forslag.length) % forslag.length))
  }, [forslag.length])

  /** Indsætter det valgte forslag. Returnerer null hvis intet er åbent. */
  const vælg = useCallback((tekst: string, indeks = valgt) => {
    if (!mention) return null
    const f = forslag[indeks]
    if (!f) return null
    setMention(null)
    return indsætMention(tekst, mention, f.rel)
  }, [mention, forslag, valgt])

  return { åben, forslag, valgt, opdater, luk, flyt, vælg }
}
