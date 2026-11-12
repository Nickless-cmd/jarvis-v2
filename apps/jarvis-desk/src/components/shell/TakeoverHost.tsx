import { useEffect } from 'react'
import { useSessions } from '../../hooks/useSessions'
import { bestilStemme } from '../../lib/figurBud'

/**
 * App-niveau bro til Jarvis-figuren på skrivebordet (electron/figur.ts).
 *
 * Komponenten tegner INTET. Den tegnede før et flydende «live takeover»-kort med «Åbn chat» på
 * de øvrige flader (cowork, indstillinger …) når en samtale fik et aktivt run — og det kort
 * hentede `/chat/active-runs`, altså ALLE sessioner brugeren må se, også andres (12/11-2026:
 * Bjørn så en andens session pop op i arbejdsfladen). Chat og Code har deres egen liveness,
 * og kortet var kun for de andre flader. Det er fjernet, og med det de to polls (active-runs
 * hvert 1,5 s og transcript hvert 1,2 s), som også åd af rate-limit-kvoten.
 *
 * Det der bliver: figurens taleboble. Et klik på den viser hovedvinduet, og her åbnes
 * samtalen den talte om — samme handling som at tage en samtale over fra telefonen.
 */
export function TakeoverHost({
  surface,
  setSurface
}: {
  surface: string
  setSurface: (s: 'chat') => void
}) {
  const { select } = useSessions()

  // Jarvis-figuren på skrivebordet (electron/figur.ts): et klik på dens
  // taleboble viser hovedvinduet — og her åbnes samtalen den talte om. Samme
  // handling som at tage en samtale over fra telefonen: vælg den, gå til chat.
  useEffect(() => {
    const bro = (window as unknown as { jarvisDesk?: { figur?: {
      paaAabnSamtale: (cb: (sid: string) => void) => () => void
      paaStemme: (cb: () => void) => () => void
    } } }).jarvisDesk
    const af1 = bro?.figur?.paaAabnSamtale((sid) => { select(sid); if (surface !== 'code') setSurface('chat') })
    // Stemme-ikonet: til chat, og buddet venter på ChatView (lib/figurBud).
    const af2 = bro?.figur?.paaStemme(() => { if (surface !== 'code') setSurface('chat'); bestilStemme() })
    return () => { af1?.(); af2?.() }
  }, [select, setSurface, surface])

  return null
}
