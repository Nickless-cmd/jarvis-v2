import { useCallback, useEffect, useState } from 'react'
import { X, ShieldAlert, CircleAlert, CircleCheck, Bell, Package } from 'lucide-react'
import { openEventSocket, type ApiConfig } from '../../lib/api'
import {
  hentNotifikationer, afgoerNotifikation, setNotifikation, type Notifikation,
} from '../../lib/notifikationerApi'
import { SettingsState, SettingsActionError } from '../settings/SettingsState'

const IKON: Record<string, typeof Bell> = {
  approval: ShieldAlert, question: ShieldAlert,
  run_failed: CircleAlert, run_done: CircleCheck,
  release: Package,
}

/** «for 3 min siden» — et klokkeslaet siger mindre end et interval her. */
function siden(iso: string): string {
  const ms = Date.now() - Date.parse(iso)
  if (!Number.isFinite(ms) || ms < 0) return ''
  const min = Math.floor(ms / 60_000)
  if (min < 1) return 'lige nu'
  if (min < 60) return `${min} min siden`
  const timer = Math.floor(min / 60)
  if (timer < 24) return `${timer} t siden`
  return `${Math.floor(timer / 24)} d siden`
}

/**
 * Notifikations-feeden — en to-do-liste, ikke en journal.
 *
 * Har man handlet, er posten vaek. Derfor er en tom feed en GOD nyhed, og
 * derfor maa en fejlet hentning aldrig ligne den: de to staar som hver sin
 * besked, og fejlen har en «Prøv igen».
 *
 * Fejlteksten for en mislykket hentning skrives IKKE via SettingsState's
 * skabelon («Kunne ikke hente ${label}.») — den bøjning bruger «hente», ikke
 * «hentes», og der staar altid et mellemrum foer ${label}, saa ordet
 * «hentes» kan aldrig forekomme i den udskrevne saetning, uanset hvad label
 * er. Klokke.tsx (samme flade, forrige opgave) bruger allerede idiomet
 * «kunne ikke hentes», og det er ogsaa det resten af huset bruger. Derfor
 * genbruges her kun SAMME klasser/struktur som SettingsState's fejl-gren
 * (.settings-feedback.error, role="alert", en «Prøv igen»-knap) — ikke selve
 * funktionen — til denne ene besked. SettingsState bruges uaendret til
 * hente-tilstanden, og SettingsActionError bruges uaendret til svar-fejl.
 */
export function NotifikationsFeed({ config, onLuk, onAabnSession }: {
  config: ApiConfig | null
  onLuk: () => void
  onAabnSession: (sessionId: string) => void
}) {
  const [poster, setPoster] = useState<Notifikation[] | null>(null)
  const [fejl, setFejl] = useState(false)
  const [handlingFejl, setHandlingFejl] = useState('')
  const [travl, setTravl] = useState('')

  const hent = useCallback(() => {
    if (!config) return
    void hentNotifikationer(config)
      .then((f) => { setPoster(f.poster); setFejl(false) })
      .catch(() => setFejl(true))
  }, [config])

  useEffect(() => { hent() }, [hent])

  // V5: ruden deler klokkens live-signal fremfor at staa stille mens den er
  // aaben. Samme WS-lytter som Klokke.tsx (samme bus, samme filter paa
  // `notifikation.*`) — en selvstaendig lytter her, ikke loeftet state fra
  // Klokke, fordi de to komponenter allerede hver isaer henter deres egen
  // liste (klokken tager kun `antal`, ruden hele `poster`), og en delt
  // lytter aendrer ikke ved det. At loefte state op ville kraeve at aendre
  // Klokkens snitflade og alle dens eksisterende tests for at undgaa et
  // dobbelt hent-kald — denne rude faar blot den samme selvstaendige lytter,
  // saa de to aldrig kan drive fra hinanden igen.
  useEffect(() => {
    if (!config) return
    let ws: WebSocket | null = null
    try {
      ws = openEventSocket(config)
      ws.onmessage = (e) => {
        try {
          const kind = String(JSON.parse(String(e.data))?.kind || '')
          if (kind.startsWith('notifikation.')) hent()
        } catch { /* ikke-JSON paa bussen er ikke vores */ }
      }
      ws.onerror = () => { /* mount+handling daekker stadig */ }
    } catch { /* mount+handling daekker stadig */ }
    return () => { try { ws?.close() } catch { /* noop */ } }
  }, [config, hent])

  const afgoer = async (p: Notifikation, godkendt: boolean) => {
    if (!config) return
    setTravl(p.id); setHandlingFejl('')
    try {
      const svar = await afgoerNotifikation(config, p.id, godkendt)
      if (!svar.ok) { setHandlingFejl(svar.fejl || 'Svaret kunne ikke sendes.'); return }
      hent()
    } catch {
      setHandlingFejl('Svaret kunne ikke sendes. Prøv igen.')
    } finally { setTravl('') }
  }

  const aabn = (p: Notifikation) => {
    if (p.session_id) onAabnSession(p.session_id)
    // En `foraeldet` post (ejeren kunne ikke hydreres) maa ALDRIG lukkes med
    // /set — den venter stadig. Kun navigation er tilladt; et lukket kort kan
    // ikke komme igen gennem dedup'en paa serveren, saa en utilgaengelig ejer
    // maa ikke faa den til at ligne en klaret opgave (V1, 22/9-2026).
    if (config && !p.foraeldet) void setNotifikation(config, p.id).then(hent).catch(() => undefined)
  }

  return (
    <div className="notif-feed" role="dialog" aria-label="Notifikationer">
      <div className="notif-head">
        <span>Notifikationer</span>
        <button type="button" className="jobs-close" onClick={onLuk} aria-label="Luk">
          <X size={14} />
        </button>
      </div>

      <SettingsActionError message={handlingFejl} />

      {fejl ? (
        <div className="settings-feedback error" role="alert">
          <p>Notifikationerne kunne ikke hentes.</p>
          <button type="button" onClick={hent}>Prøv igen</button>
        </div>
      ) : poster === null ? (
        <SettingsState status="loading" label="notifikationerne" onRetry={() => {}} />
      ) : poster.length === 0 ? (
        <p className="notif-tom">Ingen notifikationer — alt er klaret.</p>
      ) : (
        <ul className="notif-liste">
          {poster.map((p) => {
            const Ikon = IKON[p.slags] ?? Bell
            return (
              <li key={p.id}>
                <div
                  className={`notif-post${p.foraeldet ? ' er-foraeldet' : ''}`}
                  data-testid={`notif-${p.id}`}
                  title={p.tekst || p.titel}
                  role="button"
                  tabIndex={0}
                  onClick={() => { if (!p.kan_afgoere) aabn(p) }}
                  onKeyDown={(e) => { if (e.key === 'Enter' && !p.kan_afgoere) aabn(p) }}
                >
                  <Ikon size={14} className="notif-ikon" aria-hidden="true" />
                  <span className="notif-titel">{p.titel}</span>
                  <span className="notif-tid">{siden(p.oprettet)}</span>
                </div>
                {p.foraeldet && (
                  <p className="notif-foraeldet">Kunne ikke opdateres — det viste er sidste nyt.</p>
                )}
                {p.kan_afgoere && (
                  <div className="notif-handlinger">
                    <button type="button" disabled={travl === p.id}
                            onClick={() => void afgoer(p, true)}>Godkend</button>
                    <button type="button" disabled={travl === p.id}
                            onClick={() => void afgoer(p, false)}>Afvis</button>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
