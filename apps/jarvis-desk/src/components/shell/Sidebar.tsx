import { useEffect, useLayoutEffect, useMemo, useRef, useState, Fragment } from 'react'
import {
  Plus, MoreVertical, Pencil, Download, Trash2, Search, Images, Code, FileCode2,
  Pin, Archive, ArchiveRestore, FolderInput, FolderMinus, FolderPlus,
  ChevronRight, ChevronDown, MessageSquare,
  LayoutDashboard, Blocks, Settings, Brain, Cpu,
  User, ShieldCheck, Bell, Palette, Languages, MapPin, Database, Folder, Plug, Bot, Info,
  Gauge, Users, Bug,
  type LucideIcon,
} from 'lucide-react'
import { useSessions } from '../../hooks/useSessions'
import { useSettings } from '../../hooks/useSettings'
import { useStreamUdsnit } from '../../hooks/useStream'
import { getActiveRuns } from '../../lib/api'
import { maaPolle } from '../../lib/ro'
import { COWORK_ZONES, emitZone, getCurrentZone, onZone, normalizeZone, type Zone } from '../../lib/coworkZone'
import { grupperSessioner, GRUPPER_I_MODE, grupperEfterProjekt, erKodeSamtale, type SessionGruppe } from '../../lib/sessionGroups'
import { SidebarGreb } from './SidebarGreb'
import { ModeDropdown, type Mode } from './ModeDropdown'
import { ModeBladrer } from './ModeBladrer'
import { JarvisRing } from './JarvisRing'
import type { SecondarySurface } from './SecondaryNav'
import { Klokke } from './Klokke'
import { NotifikationsFeed } from './NotifikationsFeed'
import type { AgentReference } from '../../lib/environmentEvidence'
import { NotifikationSessionPanel } from './NotifikationSessionPanel'
import { KontoMenu } from './KontoMenu'
import '../../styles/notification-feed.css'
import { hasHostCapability } from '../../lib/host'

const ZONE_ICONS: Record<string, LucideIcon> = {
  LayoutDashboard, Blocks, Settings, Brain, Cpu,
  User, ShieldCheck, Bell, Palette, Languages, MapPin, Database, Folder, Plug, Bot, Info,
  Gauge, Users,
}

/** Rollen som den står i foden. Værdierne kommer fra `users.json` — Bjørn er
 *  `owner`, Michelle er `partner`, Mikkel/Lotte/Rune er `member`. ÉN rolle, ikke
 *  både role og tier: det er samme oplysning to gange. (Bjørn 29/9-2026.) */
const ROLLE_NAVN: Record<string, string> = {
  owner: 'owner', partner: 'partner', member: 'member', guest: 'gæst',
}

export type Surface = Mode | SecondarySurface | 'gallery' | 'artifacts'

/**
 * Hvilken mode en flade hører til.
 *
 * Artefakt-fladen er en del af code mode (18/9-2026). Uden denne regel faldt
 * begge mode-vælgere tilbage til «chat» for en ukendt flade, og sessionslisten
 * skiftede til chat-grupper i samme øjeblik man åbnede artefakterne — man
 * forlod code uden at have bedt om det.
 */
export function modeFor(surface: Surface): Mode {
  if (surface === 'artifacts') return 'code'
  return (['chat', 'cowork', 'code'] as const).includes(surface as Mode) ? (surface as Mode) : 'chat'
}

/** Sidebar: app-navn, mode-slider, session-liste, sekundær-nav + bruger-fod. */
export function Sidebar({
  surface,
  onSurface,
  userName,
  onSearch,
  onOpenBug,
  onOpenAgent,
}: {
  surface: Surface
  onSurface: (s: Surface) => void
  userName: string
  /** Åbner AgentInspector i sidepanelet — bruges af agentkort i notifikationsfeedet. */
  onOpenAgent?: (agent: AgentReference) => void
  /** Aabner Ctrl+K-paletten. Samme vej som genvejen — ét sted at rette. */
  onSearch?: () => void
  /** Aabner fejl-rapporten MIDT PAA SKAERMEN. Rapporten sendes til
   *  `/chat/inbox/flag`, ikke til skrivefeltet. (Bjørn 4/10-2026.) */
  onOpenBug?: () => void
}) {
  const { sessions, activeId, select, newChat } = useSessions()
  const { settings, auth, update } = useSettings()
  // Udsnit, ikke hele vaerdien: ellers rendrer hele sessionslisten (566 hos
  // Bjoern) om ved HVER stream-chunk. Maalt 30,2 ms per chunk mod et
  // frame-budget paa 16,7 ms — se `useStreamUdsnit`.
  const workingSessionId = useStreamUdsnit((s) => s.workingSessionId)

  // Inddeling af sessions-listen (8/9-2026). Bjørn: «sessioner i side panelet
  // er rodet». 278 chat + 181 autonome + 1 proaktiv i én flad liste.
  const alleGrupper = useMemo(() => grupperSessioner(sessions), [sessions])

  // Vis kun de grupper der hører til den aktive mode. Alt andet end code-fladen
  // regnes som chat — hukommelse, planlagt og galleriet har ingen egne
  // sessioner, og dér er hans samtaler det rigtige at have ved hånden.
  const grupper = useMemo(() => {
    const tilladte = GRUPPER_I_MODE[modeFor(surface) === 'code' ? 'code' : 'chat']
    return alleGrupper.filter((g) => tilladte.includes(g.gruppe))
  }, [alleGrupper, surface])
  const [foldedeGrupper, setFoldedeGrupper] =
    useState<Partial<Record<SessionGruppe, boolean>>>({})

  const [feedAaben, setFeedAaben] = useState(false)
  const [notifikationSession, setNotifikationSession] = useState<string | null>(null)
  const [kontoAaben, setKontoAaben] = useState(false)
  const klokkeRef = useRef<HTMLDivElement>(null)
  const feedRef = useRef<HTMLDivElement>(null)
  const kontoRef = useRef<HTMLDivElement>(null)

  // HVOR feedet lander (Bjoern 26/9-2026: «notifikations feed skal aabne til
  // hoejre»).
  //
  // Det kan ikke klares i CSS alene. `.sidebar` har `overflow: hidden`, saa
  // et barn der voksede ud over de 290 px blev KLIPPET — popoveren var laast
  // til panelets bredde, uanset hvad man skrev i dens egen regel. Ankeret
  // her er derfor `position: fixed` og maales fra klokken, uden for
  // klipningen, og kan brede sig ind over indholdet.
  //
  // Bredden regnes fra vinduets kant, ikke som et fast tal: en 440 px-rude
  // forankret langt til hoejre ville stikke ud over skaermen paa et smalt
  // vindue.
  const [feedPos, setFeedPos] = useState<{ top: number; left: number; bredde: number } | null>(null)
  useEffect(() => {
    if (!feedAaben) { setFeedPos(null); return }
    const maal = () => {
      const r = klokkeRef.current?.getBoundingClientRect()
      if (!r) return
      const left = Math.max(8, Math.round(r.left))
      setFeedPos({
        top: Math.round(r.bottom + 8),
        left,
        bredde: Math.max(300, Math.min(440, window.innerWidth - left - 16)),
      })
    }
    maal()
    window.addEventListener('resize', maal)
    return () => window.removeEventListener('resize', maal)
  }, [feedAaben])

  useEffect(() => {
    if (!feedAaben && !kontoAaben) return
    const lukUdenfor = (e: PointerEvent) => {
      const target = e.target as Node
      if (!klokkeRef.current?.contains(target) && !feedRef.current?.contains(target)) setFeedAaben(false)
      if (!kontoRef.current?.contains(target)) setKontoAaben(false)
    }
    const lukEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setFeedAaben(false); setKontoAaben(false) }
    }
    window.addEventListener('pointerdown', lukUdenfor)
    window.addEventListener('keydown', lukEscape)
    return () => {
      window.removeEventListener('pointerdown', lukUdenfor)
      window.removeEventListener('keydown', lukEscape)
    }
  }, [feedAaben, kontoAaben])

  // V3: ÉT config-objekt, ikke et nyt pr. render. Klokkens `hentNu` er
  // `useCallback([config])`, og dens WS-effekt afhaenger af `[config, hentNu]`
  // — et inline-literal i JSX laver et nyt objekt hver eneste gang Sidebar
  // rendrer, og saa aabner effekten en NY socket hver gang. Maalt med en
  // probe: 6 renders → 6 sockets, fordi Sidebar rendrer mindst hvert 4.
  // sekund (activeRunSessions-pollet) og langt oftere mens et run streamer.
  // Memoiseret paa de to STRENGE, ikke paa `settings` selv — saa den er
  // stabil ogsaa hvis `useSettings()` en dag begynder at returnere et nyt
  // objekt hver render.
  const apiConfig = useMemo(
    () => (settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : null),
    [settings?.apiBaseUrl, settings?.authToken],
  )

  // #8: poll backend for sessioner med aktivt run (også autonome baggrunds-runs
  // som klienten ikke selv driver). Union'es med workingSessionId fra streamen.
  const [activeRunSessions, setActiveRunSessions] = useState<Set<string>>(new Set())
  useEffect(() => {
    if (!settings) return
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    let cancelled = false
    const tick = () => {
      // Ingen kigger -> sjaeldnere (ro.ts). Prikken der viser «arbejder» maa
      // gerne vaere 30s gammel naar maskinen har staaet uroert i tre minutter.
      if (!maaPolle('sidebar-active-runs', 4000)) return
      void getActiveRuns(cfg)
        .then((ids) => { if (!cancelled) setActiveRunSessions(new Set(ids)) })
        .catch(() => { /* behold sidste — ingen flicker ved netværks-blip */ })
    }
    tick()
    const id = setInterval(tick, 4000)
    return () => { cancelled = true; clearInterval(id) }
  }, [settings])
  const isWorking = (id: string) => id === workingSessionId || activeRunSessions.has(id)

  // Søgningen bor nu ÉT sted: Ctrl+K-paletten (SessionSearch), som kalder
  // samme `searchSessions`. Debounce-effekten her var den anden halvdel af
  // dubletten og er væk med feltet.

  return (
    <aside className="sidebar">
      <SidebarGreb />
      {/* Mode-vaelger + de to handlinger man bruger oftest. Slideren brugte hele
          bredden paa at vise tre valg; dropdown'en viser det aktive og frigoer
          plads ved siden af. */}
      <div className="sidebar-top">
        <ModeDropdown
          active={modeFor(surface)}
          onChange={(m) => onSurface(m)}
        />
        {/* Egen gruppe i hoejre side: mode-vaelgeren siger HVOR man er,
            ikonerne er ting man GOER. To slags, hver sin ende. */}
        <div className="sidebar-top-actions">
          <ModeBladrer
            active={modeFor(surface)}
            onChange={(m) => onSurface(m)}
          />
          <button
            type="button"
            className="icon-btn"
            title="Søg (Ctrl+K)"
            aria-label="Søg (Ctrl+K)"
            onClick={() => onSearch?.()}
          >
            <Search size={15} />
          </button>
          <div ref={klokkeRef} className="sidebar-klokke-anchor">
            <Klokke
              config={apiConfig}
              onAaben={() => setFeedAaben((aaben) => !aaben)}
              aktivSession={activeId}
            />
          </div>
        </div>
      </div>

      {feedAaben && (
        <div
          ref={feedRef}
          className="notif-anker"
          style={feedPos
            ? { top: feedPos.top, left: feedPos.left, width: feedPos.bredde }
            : undefined}
        >
          <NotifikationsFeed
            config={apiConfig}
            onLuk={() => setFeedAaben(false)}
            onAabnSession={(id) => { setNotifikationSession(id); setFeedAaben(false) }}
            // Et agentkort åbner ALTID den oprindelige session (i sit eget sidepanel — aldrig i den åbne samtale)
            // og den rigtige inspector, også når brugeren nu står i en anden session.
            onAabnAgent={(card) => {
              if (card.origin_session_id) setNotifikationSession(card.origin_session_id)
              setFeedAaben(false)
              onOpenAgent?.({ agentId: card.agent_id, role: '', goal: card.title, status: String(card.bucket),
                              dispatchToolUseId: '' })
            }}
            aktivSession={activeId}
          />
        </div>
      )}

      {notifikationSession && apiConfig && (
        <NotifikationSessionPanel key={notifikationSession} config={apiConfig}
          sessionId={notifikationSession} isOwner={auth?.role === 'owner'}
          onClose={() => setNotifikationSession(null)}
          onOpenFull={(targetSurface) => { select(notifikationSession); onSurface(targetSurface); setNotifikationSession(null) }} />
      )}

      {surface === 'cowork' ? (
        <CoworkMenu />
      ) : (
      <div className="sessions">
        <button className="new-chat" type="button" onClick={() => newChat()}>
          <Plus size={14} /> Ny samtale
        </button>

        <button
          type="button"
          className={`sidebar-nav-row ${surface === 'gallery' ? 'active' : ''}`}
          onClick={() => onSurface('gallery')}
        >
          <Images size={14} /> Billeder
        </button>

        {/* Artefakter — kun i code mode, hvor de hører hjemme: de filer Jarvis
            har skrevet og rettet i den valgte mappe, på tværs af samtaler
            (Bjørn 18/9-2026). Samme mønster som Billeder: en destination der
            ikke er en session. */}
        {modeFor(surface) === 'code' && (
          <button
            type="button"
            className={`sidebar-nav-row ${surface === 'artifacts' ? 'active' : ''}`}
            onClick={() => onSurface('artifacts')}
          >
            <FileCode2 size={14} /> Artefakter
          </button>
        )}

        {/* Søgefeltet er væk 8/9-2026. Det gjorde nøjagtig det samme som
            Ctrl+K-paletten — samme `searchSessions`, samme uddrag — og
            paletten kan desuden navigere. To indgange til én funktion, hvor
            den ene tog fast plads i et panel der i forvejen er fyldt.
            Søge-ikonet i toppen åbner paletten. */}
        {(
          grupper.length > 0 && (
            <>
              {grupper.map((g) => {
                // Baggrunds-gruppen er foldet sammen som udgangspunkt: 181
                // autonome kørsler ville ellers drukne hans egne samtaler.
                const foldet = foldedeGrupper[g.gruppe] ?? (g.gruppe === 'baggrund')
                return (
                  <Fragment key={g.gruppe}>
                    <div className="sidebar-group-raekke">
                      <button
                        type="button"
                        className="sidebar-label sidebar-group"
                        aria-expanded={!foldet}
                        onClick={() => setFoldedeGrupper((f) => ({ ...f, [g.gruppe]: !foldet }))}
                      >
                        {foldet ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                        <span>{g.navn}</span>
                        <span className="sidebar-group-count">{g.sessioner.length}</span>
                      </button>
                      {/* Plusset staar KUN paa kode-gruppen (Bjoern 4/10-2026:
                          «projekt fold ud linjen mangler et plus i enden til at
                          oprette nyt projekt»). Et projekt findes udelukkende
                          som en faelles `workspace_root` — se `fjernProjekt`
                          nedenfor — saa «nyt projekt» ER en kode-samtale med en
                          mappe. Paa chat- og baggrunds-grupperne ville knappen
                          ikke kunne lave noget. */}
                      {g.gruppe === 'kode' && hasHostCapability('folder-picker') && <NytProjektKnap />}
                    </div>
                    {!foldet && (
                      // KODE-gruppen deles yderligere op efter PROJEKT — som i
                      // CC, hvor overskriften er «jarvis-v2 · /media/projects».
                      // Chat-sessioner har intet workspace, saa dér ville en
                      // projekt-overskrift vaere en gruppe uden indhold.
                      g.gruppe === 'kode'
                        ? grupperEfterProjekt(g.sessioner).map((p) => (
                          <Fragment key={p.rod || 'uden'}>
                            <ProjektOverskrift navn={p.navn} sti={p.sti} rod={p.rod} sessioner={p.sessioner.map((s) => s.id)} />
                            {p.sessioner.map((s) => (
                              <SessionItem
                                key={s.id}
                                id={s.id}
                                title={s.title || 'Uden titel'}
                                active={s.id === activeId}
                                working={isWorking(s.id)}
                                erKode={erKodeSamtale(s)}
                                pinned={s.pinned}
                                archived={s.archived}
                                onSelect={() => { select(s.id); onSurface(erKodeSamtale(s) ? 'code' : 'chat') }}
                              />
                            ))}
                          </Fragment>
                        ))
                        : g.sessioner.map((s) => (
                          <SessionItem
                            key={s.id}
                            id={s.id}
                            title={s.title || 'Uden titel'}
                            active={s.id === activeId}
                            working={isWorking(s.id)}
                            erKode={erKodeSamtale(s)}
                            pinned={s.pinned}
                            archived={s.archived}
                            onSelect={() => { select(s.id); onSurface(erKodeSamtale(s) ? 'code' : 'chat') }}
                          />
                        ))
                    )}
                  </Fragment>
                )
              })}
            </>
          )
        )}
      </div>
      )}

      {/* Opmaerksomhedslinjen bor nu nederst til HOEJRE i vinduet — se
          OpmaerksomhedsVaert i App.tsx (Bjørn 21/9-2026). */}
      <div className="sidebar-foot">
        <div ref={kontoRef} className="sidebar-account-anchor">
          <button type="button" className="who" aria-label="Åbn konto-menu"
                  aria-expanded={kontoAaben} onClick={() => setKontoAaben((aaben) => !aaben)}>
            <span className="avatar">{userName.charAt(0).toUpperCase()}</span>
            <span className="who-navn">{userName}</span>
            {/* Rollen står EFTER navnet med en streg imellem, og fold-ud-pilen
                følger lige efter teksten — ikke ude i kanten. Rollen er ÉN
                oplysning: både «member» og en tier ville sige det samme to
                gange. (Bjørn 29/9-2026.) */}
            <span className="who-rolle">- {ROLLE_NAVN[auth?.role ?? 'guest'] ?? auth?.role ?? 'gæst'}</span>
            <ChevronDown size={14} className="sidebar-account-arrow" />
          </button>
          {kontoAaben && (
            <KontoMenu
              userName={userName} role={auth?.role ?? 'guest'} config={apiConfig}
              onClose={() => setKontoAaben(false)}
              onSettings={() => onSurface('settings')}
              onLogout={() => { void update({ authToken: null }) }}
            />
          )}
        </div>
        {/* Bug-ikonet bor i fodens HØJRE side. Det åbner fejl-rapporten MIDT
            PÅ SKÆRMEN, og rapporten går til `/chat/inbox/flag` — altså til
            indbakken, hvor den har et id og kan ses og lukkes.
            (Bjørn 4/10-2026: «bug icon laves om til et felt midt på skærmen
            hvor man kan melde faktisk bug til dit bug endpoint». Før lagde
            ikonet sin tekst i skrivefeltet via `jarvis-bug` — en nødløsning
            fra 29/9, hvor der ingen rute fandtes. Den findes nu.) */}
        <button type="button" className="sidebar-bug" aria-label="Rapportér en fejl"
                title="Rapportér en fejl" onClick={() => onOpenBug?.()}>
          <Bug size={14} />
        </button>
      </div>
    </aside>
  )
}

/** Cowork-menu i venstre panel (mode-bevidst): en FLAD liste af klare destinationer —
 *  hver indstillings-sektion sit eget punkt, grupperet med scanbare overskrifter (Bjørn
 *  2026-07-01: simpelhed slår kompakthed; Mikkel skal bæres igennem). Zone-skift via emitZone. */
function CoworkMenu() {
  const [zone, setZone] = useState<Zone>(getCurrentZone)
  const { auth } = useSettings()
  const isOwner = auth?.role === 'owner'
  // Hold lokal markering i sync med Jarvis-styret zone-skift (open_ui_panel); 'settings' → 'konto'.
  useEffect(() => onZone((z) => setZone(normalizeZone(z))), [])
  const visible = COWORK_ZONES.filter((z) => isOwner || !z.ownerOnly)
  let lastGroup = ''
  return (
    <div className="sessions cowork-menu">
      {visible.map((z) => {
        const Icon = ZONE_ICONS[z.icon] ?? Blocks
        const header = z.group !== lastGroup ? z.group : null
        lastGroup = z.group
        return (
          <Fragment key={z.id}>
            {header && <div className="sidebar-label">{header}</div>}
            <button
              type="button"
              className={`sidebar-nav-row ${normalizeZone(zone) === z.id ? 'active' : ''}`}
              onClick={() => { setZone(z.id); emitZone(z.id) }}
            >
              <Icon size={14} /> {z.label}
            </button>
          </Fragment>
        )
      })}
    </div>
  )
}

/** Projekt-overskrift i sidepanelet — «jarvis-v2 · /media/projects», som i CC.
 *
 *  Den var en ren <div> indtil 29/9-2026, og DERFOR kunne der ikke sidde en menu
 *  i dens ende: der var ingen knap at hænge den på. Nu er den en række med
 *  samme «⋮» som samtalerne — usynlig indtil musen er der.
 *
 *  Menuen tilbyder det der KAN gøres uden en projekt-tabel. «Omdøb projekt»
 *  kræver et navn der ikke er en mappesti og er derfor ikke bygget — den skal
 *  ikke stå i en menu der ikke kan holde den.
 *
 *  «Fjern projekt» ER bygget (29/9-2026). Projektet findes kun som den fælles
 *  `workspace_root`, så at løsne samtalerne fra mappen ER at fjerne projektet.
 *  Der er ingen tabel at slette en række i — og derfor heller ikke to
 *  handlinger: «Løsn alle samtaler» ville være samme knap med et andet navn. */
/** «+» i kode-gruppens fold-ud-linje: vælg en mappe, få et projekt.
 *
 *  Et projekt er ikke en post nogen steder — det findes udelukkende som den
 *  `workspace_root` en eller flere samtaler deler (`grupperEfterProjekt`
 *  grupperer på netop den, og `fjernProjekt` fjerner et projekt ved at løsne
 *  hver samtale fra mappen). «Opret nyt projekt» er derfor præcis:
 *  opret en kode-samtale, og peg den på en mappe.
 *
 *  Mappen vælges med husets EGEN vælger — `jarvisDesk.pickFolder`, samme
 *  bro CodeView bruger. En egen dialog her ville være en anden vej til
 *  samme valg, og de to ville kunne drive fra hinanden.
 *
 *  Rækkefølgen er vigtig: mappen FØRST, samtalen bagefter. Oprettede vi
 *  samtalen først og brugeren fortrød i mappe-dialogen, stod der en tom
 *  «Ny samtale» tilbage i listen som ingen havde bedt om.
 */
function NytProjektKnap() {
  const { create, setWorkspace } = useSessions()
  const [arbejder, setArbejder] = useState(false)
  if (!hasHostCapability('folder-picker')) return null

  const nytProjekt = async () => {
    // Ingen `stopPropagation` her, og det er MÅLT frem for antaget: en
    // mutation der fjernede den ændrede ingen adfærd. Plusset er SØSKENDE
    // til gruppe-knappen inde i `.sidebar-group-raekke`, ikke et barn af
    // den, så et klik kan ikke boble op i overskriften. Havde jeg lagt
    // knappen inde i overskriften, var den nødvendig — og så havde det
    // været en knap i en knap, hvilket heller ikke er gyldigt HTML.
    if (arbejder) return
    const bro = (window as unknown as {
      jarvisDesk?: { pickFolder?: () => Promise<string | null> }
    }).jarvisDesk
    if (!bro?.pickFolder) return
    setArbejder(true)
    try {
      const mappe = await bro.pickFolder()
      if (!mappe) return
      const sess = await create('Ny samtale', 'code')
      await setWorkspace(sess.id, 'workstation', mappe)
    } finally {
      setArbejder(false)
    }
  }

  return (
    <button type="button" className="sidebar-group-plus" onClick={nytProjekt}
            disabled={arbejder} title="Nyt projekt — vælg en mappe"
            aria-label="Nyt projekt — vælg en mappe">
      <Plus size={13} />
    </button>
  )
}


function ProjektOverskrift({ navn, sti, rod, sessioner }: {
  navn: string; sti: string; rod: string; sessioner: string[]
}) {
  const { create, setWorkspace, releaseWorkspace } = useSessions()
  const [open, setOpen] = useState(false)
  const menuAnkerRef = useRef<HTMLDivElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const [menuOpad, setMenuOpad] = useState(false)

  useEffect(() => {
    if (!open) return
    const close = () => setOpen(false)
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [open])

  // Samme vending som samtale-raekkerne: projekt-overskriften kan staa nederst
  // i listen, og dér blev menuen klippet af `.sessions`.
  useLayoutEffect(() => {
    if (!open) { setMenuOpad(false); return }
    const anker = menuAnkerRef.current?.getBoundingClientRect()
    const menu = menuRef.current?.getBoundingClientRect()
    if (!anker || !menu) return
    const beholder = menuAnkerRef.current?.closest('.sessions') as HTMLElement | null
    const bund = beholder ? beholder.getBoundingClientRect().bottom : window.innerHeight
    setMenuOpad(bund - anker.bottom < menu.height + 12)
  }, [open])

  const nySamtaleHer = async () => {
    setOpen(false)
    const sess = await create('Ny samtale', 'code')
    void setWorkspace(sess.id, 'workstation', rod)
  }

  // «Fjern projekt»: løsn hver samtale i gruppen fra mappen. Projektet findes
  // kun som den fælles `workspace_root`, så det er den eneste måde at fjerne
  // det på — og den eneste vej UD af et forkert mappevalg.
  const fjernProjekt = async () => {
    setOpen(false)
    await Promise.all(sessioner.map((id) => releaseWorkspace(id)))
  }

  return (
    <div className="sidebar-label sidebar-projekt">
      <span className="sidebar-projekt-navn">{navn}</span>
      {sti && (
        <>
          <span className="sidebar-projekt-prik" aria-hidden="true">·</span>
          <span className="sidebar-projekt-sti" title={rod}>{sti}</span>
        </>
      )}
      {/* «Uden projekt» har ingen sti og faar ingen menu — der er intet projekt
          at oprette en samtale i. */}
      {rod && (
        <div ref={menuAnkerRef} className="session-menu-anchor" onClick={(e) => e.stopPropagation()}>
          <button type="button" className="session-more" aria-label="Projekt-handlinger"
                  onClick={() => setOpen((o) => !o)}>
            <MoreVertical size={14} />
          </button>
          {open && (
            <div ref={menuRef} className={`session-menu${menuOpad ? ' opad' : ''}`}>
              <button type="button" onClick={nySamtaleHer}>
                <FolderPlus size={13} /> Ny samtale her
              </button>
              <button type="button" className="danger" onClick={fjernProjekt}>
                <FolderMinus size={13} /> Fjern projekt
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/** Session-række med "..."-menu (omdøb / eksportér / slet) — vises ved hover. */
function SessionItem({
  id,
  title,
  active,
  working,
  erKode,
  pinned,
  archived,
  onSelect,
}: {
  id: string
  title: string
  active: boolean
  working?: boolean
  erKode?: boolean
  /** 1/0 fra basen. Serveren sorterer fastgjorte oeVerst, saa raekken skal
   *  bare vise tilstanden — ikke flytte sig selv. */
  pinned?: number | null
  /** 1/0 fra basen. Arkiverede staar i deres egen gruppe nederst og har
   *  «Gendan» i stedet for «Arkivér» — de er skjult server-side som standard,
   *  men panelet henter dem med, saa de kan findes igen. */
  archived?: number | null
  onSelect: () => void
}) {
  const { rename, remove, setPinned, setArchived, setWorkspace } = useSessions()
  const { settings } = useSettings()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(title)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const menuAnkerRef = useRef<HTMLDivElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  /** Vender menuen OPAD naar der ikke er plads nedad (Bjoern 29/9-2026:
   *  «folder ud under sessionerne, den skal vaere oven paa»). `.sessions` har
   *  `overflow-y: auto`, saa en menu der aabnede nedad fra en raekke naer
   *  bunden blev KLIPPET af listen — den var der, men man kunne ikke se den.
   *  Samme faelde som notifikations-feedet ramte; her vendes menuen i stedet. */
  const [menuOpad, setMenuOpad] = useState(false)

  useEffect(() => {
    if (!open) return
    const close = () => { setOpen(false); setConfirmDelete(false) }
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [open])

  // Maales FOER browseren maler (useLayoutEffect), saa menuen ikke naar at
  // blinke nedad og hoppe op. Hoejden laeses fra menuen selv — ingen magisk
  // konstant der skal holdes i takt med hvor mange punkter den har.
  useLayoutEffect(() => {
    if (!open) { setMenuOpad(false); return }
    const anker = menuAnkerRef.current?.getBoundingClientRect()
    const menu = menuRef.current?.getBoundingClientRect()
    if (!anker || !menu) return
    const beholder = menuAnkerRef.current?.closest('.sessions') as HTMLElement | null
    const bund = beholder ? beholder.getBoundingClientRect().bottom : window.innerHeight
    setMenuOpad(bund - anker.bottom < menu.height + 12)
  }, [open])

  useEffect(() => {
    if (editing) { setDraft(title); inputRef.current?.focus(); inputRef.current?.select() }
  }, [editing, title])

  // Omdøb via INLINE edit — window.prompt() er ikke understøttet i Electron.
  const commitRename = () => {
    const next = draft.trim()
    if (next && next !== title) void rename(id, next)
    setEditing(false)
  }
  const doExport = async () => {
    setOpen(false)
    if (!settings) return
    const { exportSessionMarkdown } = await import('../../lib/exportSession')
    await exportSessionMarkdown({ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }, id, title)
  }
  // Slet via to-trins INLINE bekræft — window.confirm() er upålidelig i Electron.
  const doDelete = () => {
    if (!confirmDelete) { setConfirmDelete(true); return }
    setOpen(false)
    setConfirmDelete(false)
    void remove(id)
  }

  // «Flyt til projekt» = bind samtalen til en mappe. Projektet ER
  // `workspace_root` — der er intet at flytte i en tabel, saa selve valget af
  // mappe ER flytningen. Native dialog: window.prompt() virker ikke i Electron.
  const doFlytTilProjekt = async () => {
    setOpen(false)
    const bridge = (window as unknown as { jarvisDesk?: { pickFolder?: () => Promise<string | null> } }).jarvisDesk
    const sti = await bridge?.pickFolder?.()
    if (!sti) return
    void setWorkspace(id, 'workstation', sti)
  }

  return (
    <div className={`session-item ${active ? 'active' : ''} ${working ? 'working' : ''}`}>
      {editing ? (
        <input
          ref={inputRef}
          className="session-rename-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); commitRename() }
            else if (e.key === 'Escape') { e.preventDefault(); setEditing(false) }
          }}
          onBlur={commitRename}
        />
      ) : (
        <button type="button" className="session-item-label" onClick={onSelect}>
          {/* Typen staar FAST til venstre (20/9-2026). Foer havde chat intet tag
              — raekken saa tom ud — og de tre prikker kom og gik FORAN titlen,
              saa den rykkede hver gang en session begyndte at arbejde. */}
          {/* Arten kommer fra `kind`, ikke fra arbejdstraeet. Ikonet laeste
              `workspace_kind` — samme stedfortraeder som grupperingen brugte,
              og rettet samme sted (29/9-2026). Uden det her ville en
              kode-samtale UDEN bundet arbejdstrae staa i kode-listen med et
              chat-ikon: gruppen sagde ét, maerket sagde noget andet. */}
          {erKode
            ? <Code size={12} className="session-mode-icon" />
            : <MessageSquare size={12} className="session-mode-icon" />}
          <span className="session-titel">{title}</span>
          {/* Aktiviteten har sin EGEN plads til hoejre, hvor der er raad til at
              maerket kan laeses. Ved 12px — prikkernes gamle plads — er de tre
              bjaelker 2,3px med 0,84px luft og smelter sammen til én klat. */}
          {working && (
            <span className="session-aktiv" aria-label="Jarvis arbejder" title="Jarvis arbejder her">
              <JarvisRing size={14} spinning tone="working" />
            </span>
          )}
        </button>
      )}
      <div ref={menuAnkerRef} className="session-menu-anchor" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="session-more" aria-label="Mere" onClick={() => { setOpen((o) => !o); setConfirmDelete(false) }}>
          {/* Oprejst, ikke liggende (Bjørn 20/9-2026). Den liggende form er
              den samme glyf lagt ned; den oprejste er konventionen for en
              menu der folder NEDAD, og den fylder mindre i en smal række. */}
          <MoreVertical size={15} />
        </button>
        {open && (
          <div ref={menuRef} className={`session-menu${menuOpad ? ' opad' : ''}`}>
            {/* Fastgoer og arkivér. Begge har ligget i basen og paa serveren
                hele tiden (`PATCH /sessions/{id}/flags`); det var kun denne
                menu der ikke tilbød dem (Bjørn 29/9-2026). */}
            <button type="button" onClick={() => { setOpen(false); void setPinned(id, !pinned) }}>
              <Pin size={13} /> {pinned ? 'Frigør' : 'Fastgør'}
            </button>
            {/* Arkiverede har «Gendan» i stedet for «Arkivér». Uden den var
                arkivering en sletning man ikke kunne fortryde (29/9-2026). */}
            {archived ? (
              <button type="button" onClick={() => { setOpen(false); void setArchived(id, false) }}>
                <ArchiveRestore size={13} /> Gendan
              </button>
            ) : (
              <button type="button" onClick={() => { setOpen(false); void setArchived(id, true) }}>
                <Archive size={13} /> Arkivér
              </button>
            )}
            {!archived && hasHostCapability('folder-picker') && (
              <button type="button" onClick={doFlytTilProjekt}>
                <FolderInput size={13} /> Flyt til projekt
              </button>
            )}
            <button type="button" onClick={() => { setOpen(false); setEditing(true) }}><Pencil size={13} /> Omdøb</button>
            <button type="button" onClick={doExport}><Download size={13} /> Eksportér</button>
            <button type="button" className="danger" onClick={doDelete}>
              <Trash2 size={13} /> {confirmDelete ? 'Slet for altid?' : 'Slet'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
