import { useCallback, useEffect, useRef, useState, type ReactNode, type PointerEvent as ReactPointerEvent, type TouchEvent as ReactTouchEvent } from 'react'
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
import { markNotificationsRead, notificationAttention, NOTIFICATION_READ_EVENT } from '../../lib/notificationAttention'
import { updatesBridge } from '../../lib/updatesBridge'
import {
  getKontraktFeed, kvitterKontrakt, markerKontraktLaest, type FeedCard,
} from '../../lib/agentContractApi'
import { AgentFeedCardBody, agentKortIkon } from './AgentFeedCard'

function SwipeCard({ children, className, onRead, onDelete }: {
  children: ReactNode; className: string; onRead: () => void; onDelete?: () => void
}) {
  const start = useRef<{ x: number; y: number; pointerId?: number } | null>(null)
  const swiped = useRef(false)
  const captured = useRef(false)
  const [drag, setDrag] = useState(0)
  const down = (e: ReactPointerEvent<HTMLLIElement>) => {
    swiped.current = false
    captured.current = false
    // Touch events below are the fallback; handling both would commit twice.
    if (e.pointerType === 'touch') return
    // Gribes IKKE her. En fastholdt pointer sender det efterfølgende `click` til <li>, ikke til kortets knap — og
    // så åbner et almindeligt museklik intet (målt 7/10-2026 i Chromium: click:notif-swipe, aldrig notif-post).
    // Fastholdelsen sker først når bevægelsen er et vandret swipe (se `move`).
    start.current = { x: e.clientX, y: e.clientY, pointerId: e.pointerId }
  }
  const move = (e: ReactPointerEvent<HTMLLIElement>) => {
    if (!start.current || start.current.pointerId !== e.pointerId || !Number.isFinite(e.clientX)) return
    const dx = e.clientX - start.current.x
    if (Math.abs(e.clientY - start.current.y) >= Math.abs(dx)) { setDrag(0); return }
    if (dx < 0 && !onDelete) return
    if (!captured.current && Math.abs(dx) > 8) {
      captured.current = true
      e.currentTarget.setPointerCapture?.(e.pointerId)
    }
    setDrag(Math.max(-86, Math.min(86, dx)))
  }
  const finish = (x: number, y: number) => {
    if (!start.current) return
    const dx = x - start.current.x
    const dy = y - start.current.y
    start.current = null
    setDrag(0)
    if (Math.abs(dx) < 56 || Math.abs(dx) <= Math.abs(dy)) return
    if (dx < 0 && !onDelete) return
    swiped.current = true
    if (dx > 0) onRead()
    else onDelete?.()
  }
  return (
    <li className={`notif-swipe ${className}`} data-drag={drag < 0 ? 'left' : drag > 0 ? 'right' : undefined}
        onClickCapture={(e) => { if (swiped.current) { e.preventDefault(); e.stopPropagation(); swiped.current = false } }}
        onPointerDown={down} onPointerMove={move}
        onPointerUp={(e) => {
          if (start.current?.pointerId !== e.pointerId) return
          finish(e.clientX, e.clientY)
          e.currentTarget.releasePointerCapture?.(e.pointerId)
        }}
        onPointerCancel={() => { start.current = null; setDrag(0) }}
        onLostPointerCapture={() => { start.current = null; setDrag(0) }}
        onTouchStart={(e: ReactTouchEvent<HTMLLIElement>) => {
          swiped.current = false
          const touch = e.touches[0]
          if (touch) start.current = { x: touch.clientX, y: touch.clientY }
        }}
        onTouchMove={(e: ReactTouchEvent<HTMLLIElement>) => {
          const touch = e.touches[0]
          if (touch && start.current) {
            const dx = touch.clientX - start.current.x
            const dy = touch.clientY - start.current.y
            if (Math.abs(dx) > Math.abs(dy) && (dx >= 0 || onDelete))
              setDrag(Math.max(-86, Math.min(86, dx)))
            else setDrag(0)
          }
        }}
        onTouchEnd={(e: ReactTouchEvent<HTMLLIElement>) => {
          const touch = e.changedTouches[0]
          if (touch) finish(touch.clientX, touch.clientY)
        }}>
      <span className="notif-swipe-action" aria-hidden="true">{drag < 0 ? 'Slet' : 'Læst'}</span>
      <div className="notif-swipe-content" style={drag ? { transform: `translateX(${drag}px)` } : undefined}>
        {children}
      </div>
    </li>
  )
}

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

// Only completed, informational kinds are eligible for bulk cleanup.
// Questions, approvals, alerts and future unknown kinds stay visible.
const RYD_BARE = new Set(['run_done', 'release', 'keymaker_key_earned'])

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
export function NotifikationsFeed({ config, onLuk, onAabnSession, aktivSession, onAabnAgent }: {
  config: ApiConfig | null
  onLuk: () => void
  onAabnSession: (sessionId: string) => void
  /** Klik på et agentkort: åbn den OPRINDELIGE session og den rigtige AgentInspector — også når brugeren nu står
   *  i en anden session. Kortet injicerer aldrig noget i den åbne samtale. Uden handleren åbnes kun sessionen. */
  onAabnAgent?: (card: FeedCard) => void
  /**
   * Samtalen brugeren sidder i nu. Sendes til serveren, som springer svar
   * fra den over (Bjoern 26/9-2026): man laeser dem allerede i vinduet ved
   * siden af. Filtreringen ligger paa SERVEREN, saa klokkens tal og listen
   * bygger paa samme maengde — se notifikationerApi.hentNotifikationer.
   */
  aktivSession?: string | null
}) {
  const [poster, setPoster] = useState<Notifikation[] | null>(null)
  const [fejl, setFejl] = useState(false)
  // Agentkort (G): hydreret fra assignment/approval i DB. En fejlet hentning er IKKE «ingen agenter».
  const [agentKort, setAgentKort] = useState<FeedCard[] | null>(null)
  const [agentFejl, setAgentFejl] = useState(false)
  const [handlingFejl, setHandlingFejl] = useState('')
  const [travl, setTravl] = useState('')
  const [opdaterer, setOpdaterer] = useState(false)
  const [rydder, setRydder] = useState(false)
  const [bekraeftRyd, setBekraeftRyd] = useState(false)
  const [installerer, setInstallerer] = useState('')
  const hentVersion = useRef(0)
  const lokaltLukkede = useRef(new Set<string>())
  const [, setReadVersion] = useState(0)
  useEffect(() => {
    const changed = () => setReadVersion((n) => n + 1)
    window.addEventListener(NOTIFICATION_READ_EVENT, changed)
    return () => window.removeEventListener(NOTIFICATION_READ_EVENT, changed)
  }, [])

  // Tre faner. «venter» er standarden: den er der hvor der ER noget at goere.
  const [fane, setFane] = useState<'venter' | 'svar' | 'tidligere'>('venter')
  const [tidligere, setTidligere] = useState<TidligereNotifikation[] | null>(null)
  const [fejlTidligere, setFejlTidligere] = useState(false)

  const hentAgenter = useCallback(() => {
    if (!config) return
    void getKontraktFeed(config)
      .then((f) => { setAgentKort(f.cards); setAgentFejl(false) })
      .catch(() => setAgentFejl(true))
  }, [config])

  const hent = useCallback((manuel = false) => {
    if (!config) return
    hentAgenter()
    const version = ++hentVersion.current
    if (manuel) setOpdaterer(true)
    void hentNotifikationer(config, aktivSession)
      .then((f) => { if (version === hentVersion.current) {
        setPoster(f.poster.filter((p) => !lokaltLukkede.current.has(p.id)))
        setFejl(false)
      } })
      .catch(() => { if (version === hentVersion.current) setFejl(true) })
      .finally(() => { if (manuel) setOpdaterer(false) })
  }, [config, aktivSession, hentAgenter])

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
      markNotificationsRead([p.id])
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
      lokaltLukkede.current.add(p.id)
      setPoster((forrige) => forrige?.filter((kort) => kort.id !== p.id) ?? null)
      markNotificationsRead([p.id])
      genindlaes()
    } catch {
      setHandlingFejl('Notifikationen kunne ikke afsluttes. Prøv igen.')
    } finally { setTravl('') }
  }

  const aabn = (p: Notifikation) => {
    if (p.session_id) onAabnSession(p.session_id)
    // Laesning er ikke sletning. Kortet bliver i feedet indtil kryds/venstre-swipe.
    markNotificationsRead([p.id])
  }

  const laesAgent = (k: FeedCard) => {
    if (!config) return
    void markerKontraktLaest(config, k.ref_kind, k.ref_id).then(hentAgenter).catch(() => setAgentFejl(true))
  }
  const aabnAgentKort = (k: FeedCard) => {
    laesAgent(k)
    if (onAabnAgent) onAabnAgent(k)
    else if (k.origin_session_id) onAabnSession(k.origin_session_id)
  }
  const kvitterAgent = async (k: FeedCard) => {
    if (!config || !k.can_acknowledge) return
    setTravl(k.ref_id); setHandlingFejl('')
    try {
      await kvitterKontrakt(config, k.assignment_id)
      hentAgenter()
    } catch (reason) {
      setHandlingFejl(reason instanceof Error ? reason.message : 'Kortet kunne ikke kvitteres.')
    } finally { setTravl('') }
  }

  const agentKortRaekke = (k: FeedCard) => {
    const Ikon = agentKortIkon(k)
    return (
      <SwipeCard key={`${k.ref_kind}:${k.ref_id}`}
        className={`notif-item tone-agent${k.section === 'svar' ? ' er-svar' : ''}${k.state.read ? ' er-laest' : ''}`}
        onRead={() => laesAgent(k)} onDelete={k.can_acknowledge ? () => void kvitterAgent(k) : undefined}>
        {k.can_acknowledge && <button type="button" className="notif-dismiss" aria-label={`Kvittér ${k.title}`}
                disabled={travl === k.ref_id} onClick={() => void kvitterAgent(k)}><X size={13} /></button>}
        <div className="notif-post" data-testid={`notif-agent-${k.ref_id}`} title={k.title} role="button" tabIndex={0}
             onClick={() => aabnAgentKort(k)} onKeyDown={(e) => { if (e.key === 'Enter') aabnAgentKort(k) }}>
          <span className="notif-ikon-ramme"><Ikon size={15} className="notif-ikon" aria-hidden="true" /></span>
          <span className="notif-titel">{k.title}</span>
          <span className="notif-tid">{siden(k.updated_at)}</span>
        </div>
        {config && <AgentFeedCardBody config={config} card={k} onChanged={() => { hentAgenter(); hent() }}
                                      onError={setHandlingFejl} />}
      </SwipeCard>
    )
  }

  const installerRelease = async (p: Notifikation) => {
    const bridge = updatesBridge()
    if (!bridge) return
    setInstallerer(p.id); setHandlingFejl('')
    try {
      await bridge.installNow()
    } catch (e) {
      setHandlingFejl(`Opdateringen kunne ikke installeres: ${e instanceof Error ? e.message : String(e)}`)
    } finally { setInstallerer('') }
  }

  // Et svar er ikke en opgave, og de to skal ikke dele liste.
  //
  // Maalt 26/9-2026: 100 aabne `run_done` mod 24 poster der faktisk ventede.
  // Svarene druknede dem man skulle svare paa — og et svar i «Venter paa dig»
  // tilboed en «Faerdig»-knap for noget der allerede var faerdigt.
  //
  // Opdelingen sker HER og ikke i `poster`, saa begge lister bygger paa den
  // samme hentning. Serveren har allerede fjernet svar fra den aktive
  // samtale, saa «Svar» viser baggrunden — ikke det man har foran sig.
  const alle = poster ?? []
  const venter = alle.filter((p) => p.slags !== 'run_done')
  const svar = alle.filter((p) => p.slags === 'run_done')
  const afgjort = tidligere ?? []
  const kortListe = agentKort ?? []
  const agentVenter = kortListe.filter((k) => k.section === 'venter')
  const agentSvar = kortListe.filter((k) => k.section === 'svar')
  const agentAktiv = kortListe.filter((k) => k.section === 'aktiv')
  const rydBare = alle.filter((p) => RYD_BARE.has(p.slags) && !p.foraeldet &&
    !notificationAttention([p.id]).unread)

  const rydPoster = async (valgte: Notifikation[]) => {
    if (!config || valgte.length === 0 || rydder) return
    setRydder(true); setHandlingFejl('')
    const fjernet: string[] = []
    let fejlet = 0
    // Limit simultaneous requests when a long history of completed runs is cleared.
    for (let i = 0; i < valgte.length; i += 6) {
      const resultater = await Promise.allSettled(valgte.slice(i, i + 6).map(async (p) => {
        await setNotifikation(config, p.id)
        return p.id
      }))
      for (const resultat of resultater) {
        if (resultat.status === 'fulfilled') fjernet.push(resultat.value)
        else fejlet++
      }
    }
    if (fjernet.length) {
      fjernet.forEach((id) => lokaltLukkede.current.add(id))
      setPoster((forrige) => forrige?.filter((p) => !fjernet.includes(p.id)) ?? null)
      markNotificationsRead(fjernet)
      hent()
      hentHistorik()
    }
    if (fejlet) setHandlingFejl(`${fejlet} notifikationer kunne ikke ryddes. Prøv igen.`)
    setRydder(false)
  }

  return (
    <div className="notif-feed" role="dialog" aria-label="Notifikationer">
      <div className="notif-head">
        <div className="notif-heading">
          <span>Notifikationer</span>
        </div>
        {rydBare.length > 0 && <button type="button" className="notif-clear-read"
          disabled={rydder} onClick={() => void rydPoster(rydBare)}>
          {rydder ? 'Rydder…' : `Ryd læste (${rydBare.length})`}
        </button>}
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
          {venter.length + agentVenter.length > 0 && <span className="notif-fane-tal er-venter">{venter.length + agentVenter.length}</span>}
        </button>
        <button
          type="button" role="tab" aria-selected={fane === 'svar'}
          className={`notif-fane${fane === 'svar' ? ' aktiv' : ''}`}
          onClick={() => setFane('svar')}
        >
          Svar
          {svar.length + agentSvar.length > 0 && <span className="notif-fane-tal">{svar.length + agentSvar.length}</span>}
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

      {fane === 'venter' && venter.length > 0 && <div className="notif-clear-all-row">
        {bekraeftRyd ? <div className="notif-clear-confirm" role="group" aria-label="Bekræft ryd alle">
          <span>Ryd {venter.length} fra Venter? Uafklarede spørgsmål og godkendelser fjernes uden svar.</span>
          <button type="button" disabled={rydder} onClick={() => { setBekraeftRyd(false); void rydPoster(venter) }}>Ryd alle</button>
          <button type="button" onClick={() => setBekraeftRyd(false)}>Annuller</button>
        </div> : <button type="button" className="notif-clear-read" onClick={() => setBekraeftRyd(true)}>Ryd alle i Venter</button>}
      </div>}

      <SettingsActionError message={handlingFejl} />
      {agentFejl && (
        <div className="settings-feedback error" role="alert" data-testid="ac-feed-fejl">
          <p>Agentkortene kunne ikke hentes — listen er ukendt, ikke tom.</p>
          <button type="button" onClick={() => hentAgenter()}>Prøv igen</button>
        </div>
      )}

      {fane === 'svar' ? (
        fejl ? (
          <div className="settings-feedback error" role="alert">
            <p>Notifikationerne kunne ikke hentes.</p>
            <button type="button" onClick={() => hent()}>Prøv igen</button>
          </div>
        ) : poster === null ? (
          <SettingsState status="loading" label="notifikationerne" onRetry={() => {}} />
        ) : svar.length + agentSvar.length + agentAktiv.length === 0 ? (
          <p className="notif-tom">Ingen svar fra baggrunden endnu.</p>
        ) : (
          <ul className="notif-liste">
            {agentSvar.map(agentKortRaekke)}
            {svar.map((p) => {
              const Ikon = IKON[p.slags] ?? Bell
              return (
                <SwipeCard key={p.id} className={`notif-item tone-${p.slags} er-svar${notificationAttention([p.id]).unread ? '' : ' er-laest'}`}
                  onRead={() => markNotificationsRead([p.id])} onDelete={p.foraeldet ? undefined : () => void afslut(p)}>
                  {!p.foraeldet && <button type="button" className="notif-dismiss" aria-label="Fjern notifikation"
                          disabled={travl === p.id} onClick={() => void afslut(p)}><X size={13} /></button>}
                  {/* Et svar er LAESNING, ikke en opgave: ingen knapper her.
                      At trykke paa kortet aabner samtalen svaret kom fra —
                      den eneste handling der giver mening, og den samme som
                      «Tidligere» tilbyder. Forskellen er at svaret her er
                      AABENT: man kan svare i den samtale det kom fra. */}
                  <div
                    className="notif-post"
                    data-testid={`notif-svar-${p.id}`}
                    title={p.tekst || p.titel}
                    role="button"
                    tabIndex={0}
                    onClick={() => aabn(p)}
                    onKeyDown={(e) => { if (e.key === 'Enter') aabn(p) }}
                  >
                    <span className="notif-ikon-ramme"><Ikon size={15} className="notif-ikon" aria-hidden="true" /></span>
                    <span className="notif-titel">{p.titel}</span>
                    <span className="notif-tid">{siden(p.oprettet)}</span>
                  </div>
                  {p.tekst && p.tekst !== p.titel && (
                    <p className="notif-tekst notif-svar-tekst">{p.tekst}</p>
                  )}
                </SwipeCard>
              )
            })}
            {/* «I gang» står EFTER svarene: det er baggrund, ikke et svar man skal læse. */}
            {agentAktiv.length > 0 && <li className="ac-i-gang">Agenter i gang ({agentAktiv.length})</li>}
            {agentAktiv.map(agentKortRaekke)}
          </ul>
        )
      ) : fane === 'venter' ? (
        fejl ? (
          <div className="settings-feedback error" role="alert">
            <p>Notifikationerne kunne ikke hentes.</p>
            <button type="button" onClick={() => hent()}>Prøv igen</button>
          </div>
        ) : poster === null ? (
          <SettingsState status="loading" label="notifikationerne" onRetry={() => {}} />
        ) : venter.length + agentVenter.length === 0 ? (
          <p className="notif-tom">{agentFejl
            ? 'Kan ikke bekræfte at intet venter — agentkortene kunne ikke hentes.'
            : svar.length + agentSvar.length
              ? `Intet venter på dig. ${svar.length + agentSvar.length} svar under Svar.`
              : 'Ingen notifikationer — alt er klaret.'}</p>
        ) : (
          <ul className="notif-liste">
            {agentVenter.map(agentKortRaekke)}
            {venter.map((p) => {
              const Ikon = IKON[p.slags] ?? Bell
              return (
                <SwipeCard key={p.id} className={`notif-item tone-${p.slags}${notificationAttention([p.id]).unread ? '' : ' er-laest'}`}
                  onRead={() => markNotificationsRead([p.id])} onDelete={p.foraeldet ? undefined : () => void afslut(p)}>
                  {!p.foraeldet && <button type="button" className="notif-dismiss" aria-label="Fjern notifikation"
                          disabled={travl === p.id} onClick={() => void afslut(p)}><X size={13} /></button>}
                  <div
                    className={`notif-post${p.foraeldet ? ' er-foraeldet' : ''}`}
                    data-testid={`notif-${p.id}`}
                    title={p.tekst || p.titel}
                    role="button"
                    tabIndex={0}
                    onClick={() => aabn(p)}
                    onKeyDown={(e) => { if (e.key === 'Enter') aabn(p) }}
                  >
                    <span className="notif-ikon-ramme"><Ikon size={15} className="notif-ikon" aria-hidden="true" /></span>
                    <span className="notif-titel">{p.titel}</span>
                    <span className="notif-tid">{siden(p.oprettet)}</span>
                  </div>
                  {p.tekst && p.tekst !== p.titel && <p className="notif-tekst">{p.tekst}</p>}
                  {p.slags === 'release' && updatesBridge()?.installNow && <button type="button"
                    className="notif-install" disabled={installerer === p.id}
                    onClick={() => void installerRelease(p)}>{installerer === p.id ? 'Henter…' : 'Installér nu'}</button>}
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
                </SwipeCard>
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
