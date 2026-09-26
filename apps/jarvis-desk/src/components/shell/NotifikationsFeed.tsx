import { useCallback, useEffect, useState } from 'react'
import {
  X, ShieldAlert, CircleAlert, CircleCheck, Bell, Package, RefreshCw,
  MessageCircle, Flag, ShieldX, Radar, Key, AtSign,
} from 'lucide-react'
import { openEventSocket, type ApiConfig } from '../../lib/api'
import {
  hentNotifikationer, hentTidligere, afgoerNotifikation, setNotifikation,
  type Notifikation, type TidligereNotifikation,
} from '../../lib/notifikationerApi'
import { SettingsState, SettingsActionError } from '../settings/SettingsState'

const IKON: Record<string, typeof Bell> = {
  approval: ShieldAlert, question: ShieldAlert,
  run_failed: CircleAlert, run_done: CircleCheck,
  release: Package,
  // ── De seks router-ejede slags (routeren-foeder, 2026-09-22) ────────────
  reach_out: MessageCircle,
  central_flag: Flag,
  membrane_breach: ShieldX,
  infra_security: Radar,
  keymaker_key_earned: Key,
  moltbook_mention: AtSign,
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
 * Notifikations-feeden — to lister med hver sin skaebne.
 *
 * FOER (til 26/9-2026) var den én liste: har man handlet, er posten vaek.
 * Det gjorde en tom feed til en GOD nyhed — men ogsaa til en feed uden
 * hukommelse. Man kunne ikke se hvad man havde svaret, eller om man havde
 * svaret; svaret slettede sit eget spoer (Bjoern 26/9-2026: «jeg havde
 * forstillet mig noget mere hen efter notifikations feed de har i
 * facebook»).
 *
 * NU: to faner. «Venter på dig» er opgavelisten — handlingerne staar altid
 * fremme, og posten forsvinder naar man har svaret. «Tidligere» er ren
 * laesning: afgjort, intet at trykke paa, kun udfaldet. Fanerne baerer deres
 * tal, saa man kan se om der venter noget UDEN at aabne den.
 *
 * En fejlet hentning maa aldrig ligne en tom liste. Det gaelder nu BEGGE
 * faner, og de har hver sin fejl-tilstand: historikken kan vaere hentet
 * mens de aabne fejler, og omvendt.
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
  const [opdaterer, setOpdaterer] = useState(false)

  // To faner. «venter» er standarden: den er der hvor der ER noget at goere.
  const [fane, setFane] = useState<'venter' | 'tidligere'>('venter')
  const [tidligere, setTidligere] = useState<TidligereNotifikation[] | null>(null)
  const [fejlTidligere, setFejlTidligere] = useState(false)

  const hent = useCallback((manuel = false) => {
    if (!config) return
    if (manuel) setOpdaterer(true)
    void hentNotifikationer(config)
      .then((f) => { setPoster(f.poster); setFejl(false) })
      .catch(() => setFejl(true))
      .finally(() => { if (manuel) setOpdaterer(false) })
  }, [config])

  // Historikken hentes ogsaa ved mount — ikke foerst naar man klikker paa
  // fanen. Tallet paa fanen SKAL staa der foer man trykker: en fane der
  // foerst viser sit indhold bagefter kan ikke svare paa «er der noget
  // gammelt her?», og det er hele grunden til at den findes.
  const hentHistorik = useCallback(() => {
    if (!config) return
    void hentTidligere(config)
      .then((f) => { setTidligere(f.poster); setFejlTidligere(false) })
      .catch(() => setFejlTidligere(true))
  }, [config])

  useEffect(() => { hent(); hentHistorik() }, [hent, hentHistorik])

  // V5: ruden deler klokkens live-signal fremfor at staa stille mens den er
  // aaben. Samme WS-lytter som Klokke.tsx (samme bus, samme filter paa
  // `notifikation.*`) — en selvstaendig lytter her, ikke loeftet state fra
  // Klokke, fordi de to komponenter allerede hver isaer henter deres egen
  // liste (klokken tager kun `antal`, ruden hele `poster`), og en delt
  // lytter aendrer ikke ved det. At loefte state op ville kraeve at aendre
  // Klokkens snitflade og alle dens eksisterende tests for at undgaa et
  // dobbelt hent-kald — denne rude faar blot den samme selvstaendige lytter,
  // saa de to aldrig kan drive fra hinanden igen.
  //
  // Historikken lyttes der ogsaa paa: et svar sendt fra telefonen lukker
  // raekken, og uden dette ville den dukke op i «Venter» indtil nogen
  // genaabnede ruden.
  useEffect(() => {
    if (!config) return
    let ws: WebSocket | null = null
    try {
      ws = openEventSocket(config)
      ws.onmessage = (e) => {
        try {
          const kind = String(JSON.parse(String(e.data))?.kind || '')
          if (kind.startsWith('notifikation.')) { hent(); hentHistorik() }
        } catch { /* ikke-JSON paa bussen er ikke vores */ }
      }
      ws.onerror = () => { /* mount+handling daekker stadig */ }
    } catch { /* mount+handling daekker stadig */ }
    return () => { try { ws?.close() } catch { /* noop */ } }
  }, [config, hent, hentHistorik])

  // Efter et svar er posten flyttet fra «venter» til «tidligere» — begge
  // lister skal hentes igen, ellers staar den et sted og mangler det andet.
  const genindlaes = useCallback(() => { hent(); hentHistorik() }, [hent, hentHistorik])

  const afgoer = async (p: Notifikation, godkendt: boolean) => {
    if (!config) return
    setTravl(p.id); setHandlingFejl('')
    try {
      const svar = await afgoerNotifikation(config, p.id, godkendt)
      if (!svar.ok) { setHandlingFejl(svar.fejl || 'Svaret kunne ikke sendes.'); return }
      genindlaes()
    } catch {
      setHandlingFejl('Svaret kunne ikke sendes. Prøv igen.')
    } finally { setTravl('') }
  }

  const afslut = async (p: Notifikation) => {
    if (!config || p.foraeldet) return
    setTravl(p.id); setHandlingFejl('')
    try {
      await setNotifikation(config, p.id)
      genindlaes()
    } catch {
      setHandlingFejl('Notifikationen kunne ikke afsluttes. Prøv igen.')
    } finally { setTravl('') }
  }

  const aabn = (p: Notifikation) => {
    if (p.session_id) onAabnSession(p.session_id)
    // En `foraeldet` post (ejeren kunne ikke hydreres) maa ALDRIG lukkes med
    // /set — den venter stadig. Kun navigation er tilladt; et lukket kort kan
    // ikke komme igen gennem dedup'en paa serveren, saa en utilgaengelig ejer
    // maa ikke faa den til at ligne en klaret opgave (V1, 22/9-2026).
    if (config && !p.foraeldet && p.slags !== 'question') {
      void setNotifikation(config, p.id).then(genindlaes).catch(() => undefined)
    }
  }

  const venter = poster ?? []
  const afgjort = tidligere ?? []

  return (
    <div className="notif-feed" role="dialog" aria-label="Notifikationer">
      <div className="notif-head">
        <div className="notif-heading">
          <span>Notifikationer</span>
        </div>
        <button type="button" className="jobs-close notif-refresh" onClick={() => { hent(true); hentHistorik() }}
                disabled={opdaterer} aria-label="Opdater notifikationer">
          <RefreshCw size={14} className={opdaterer ? 'spinning' : ''} />
        </button>
        <button type="button" className="jobs-close" onClick={onLuk} aria-label="Luk">
          <X size={14} />
        </button>
      </div>

      {/* Fanerne baerer deres EGNE tal. «Venter» er fremhaevet naar den har
          noget — det er den eneste af de to hvor der er noget at goere. */}
      <div className="notif-faner" role="tablist" aria-label="Notifikationer">
        <button
          type="button" role="tab" aria-selected={fane === 'venter'}
          className={`notif-fane${fane === 'venter' ? ' aktiv' : ''}`}
          onClick={() => setFane('venter')}
        >
          Venter på dig
          {venter.length > 0 && <span className="notif-fane-tal er-venter">{venter.length}</span>}
        </button>
        <button
          type="button" role="tab" aria-selected={fane === 'tidligere'}
          className={`notif-fane${fane === 'tidligere' ? ' aktiv' : ''}`}
          onClick={() => setFane('tidligere')}
        >
          Tidligere
          {afgjort.length > 0 && <span className="notif-fane-tal">{afgjort.length}</span>}
        </button>
      </div>

      <SettingsActionError message={handlingFejl} />

      {fane === 'venter' ? (
        fejl ? (
          <div className="settings-feedback error" role="alert">
            <p>Notifikationerne kunne ikke hentes.</p>
            <button type="button" onClick={() => hent()}>Prøv igen</button>
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
                <li key={p.id} className={`notif-item tone-${p.slags}`}>
                  <div
                    className={`notif-post${p.foraeldet ? ' er-foraeldet' : ''}`}
                    data-testid={`notif-${p.id}`}
                    title={p.tekst || p.titel}
                    role="button"
                    tabIndex={0}
                    onClick={() => { if (!p.kan_afgoere) aabn(p) }}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !p.kan_afgoere) aabn(p) }}
                  >
                    <span className="notif-ikon-ramme"><Ikon size={15} className="notif-ikon" aria-hidden="true" /></span>
                    <span className="notif-titel">{p.titel}</span>
                    <span className="notif-tid">{siden(p.oprettet)}</span>
                  </div>
                  {p.tekst && p.tekst !== p.titel && <p className="notif-tekst">{p.tekst}</p>}
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
                  {!p.kan_afgoere && !p.foraeldet && p.slags !== 'question' && (
                    <div className="notif-handlinger">
                      <button type="button" disabled={travl === p.id} onClick={() => void afslut(p)}>Færdig</button>
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        )
      ) : (
        fejlTidligere ? (
          <div className="settings-feedback error" role="alert">
            <p>Notifikationerne kunne ikke hentes.</p>
            <button type="button" onClick={() => hentHistorik()}>Prøv igen</button>
          </div>
        ) : tidligere === null ? (
          <SettingsState status="loading" label="notifikationerne" onRetry={() => {}} />
        ) : tidligere.length === 0 ? (
          <p className="notif-tom">Intet afsluttet endnu.</p>
        ) : (
          <ul className="notif-liste">
            {tidligere.map((p) => {
              const Ikon = IKON[p.slags] ?? Bell
              return (
                <li key={p.id} className={`notif-item tone-${p.slags} er-afgjort`}>
                  {/* Ingen handlingsknapper her — det ER hele forskellen.
                      Er posten afgjort, er der intet at trykke paa; den er
                      laesning, ikke en opgave der venter. */}
                  <div
                    className="notif-post"
                    data-testid={`notif-tidligere-${p.id}`}
                    title={p.tekst || p.titel}
                    role="button"
                    tabIndex={0}
                    onClick={() => { if (p.session_id) onAabnSession(p.session_id) }}
                    onKeyDown={(e) => { if (e.key === 'Enter' && p.session_id) onAabnSession(p.session_id) }}
                  >
                    <span className="notif-ikon-ramme"><Ikon size={15} className="notif-ikon" aria-hidden="true" /></span>
                    <span className="notif-titel">{p.titel}</span>
                    <span className="notif-tid">{siden(p.oprettet)}</span>
                  </div>
                  {p.tekst && p.tekst !== p.titel && <p className="notif-tekst">{p.tekst}</p>}
                  <p className="notif-udfald">{p.udfald_tekst}</p>
                </li>
              )
            })}
          </ul>
        )
      )}
    </div>
  )
}
