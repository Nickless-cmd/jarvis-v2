import { useEffect, useMemo, useRef, useState, Fragment } from 'react'
import {
  Plus, MoreVertical, Pencil, Download, Trash2, Search, Images, Code, FileCode2,
  ChevronRight, ChevronDown, MessageSquare,
  LayoutDashboard, Blocks, Settings, Brain, Cpu,
  User, ShieldCheck, Bell, Palette, Languages, MapPin, Database, Folder, Plug, Bot, Info,
  Gauge, Users,
  type LucideIcon,
} from 'lucide-react'
import { useSessions } from '../../hooks/useSessions'
import { useSettings } from '../../hooks/useSettings'
import { useStream } from '../../hooks/useStream'
import { getActiveRuns } from '../../lib/api'
import { maaPolle } from '../../lib/ro'
import { COWORK_ZONES, emitZone, getCurrentZone, onZone, normalizeZone, type Zone } from '../../lib/coworkZone'
import { grupperSessioner, GRUPPER_I_MODE, grupperEfterProjekt, type SessionGruppe } from '../../lib/sessionGroups'
import { SidebarGreb } from './SidebarGreb'
import { ModeDropdown, type Mode } from './ModeDropdown'
import { ModeBladrer } from './ModeBladrer'
import { JarvisRing } from './JarvisRing'
import type { SecondarySurface } from './SecondaryNav'
import { Klokke } from './Klokke'
import { NotifikationsFeed } from './NotifikationsFeed'
import { KontoMenu } from './KontoMenu'

const ZONE_ICONS: Record<string, LucideIcon> = {
  LayoutDashboard, Blocks, Settings, Brain, Cpu,
  User, ShieldCheck, Bell, Palette, Languages, MapPin, Database, Folder, Plug, Bot, Info,
  Gauge, Users,
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
}: {
  surface: Surface
  onSurface: (s: Surface) => void
  userName: string
  /** Aabner Ctrl+K-paletten. Samme vej som genvejen — ét sted at rette. */
  onSearch?: () => void
}) {
  const { sessions, activeId, select, newChat } = useSessions()
  const { settings, auth, update } = useSettings()
  const { workingSessionId } = useStream()

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
  const [kontoAaben, setKontoAaben] = useState(false)
  const klokkeRef = useRef<HTMLDivElement>(null)
  const feedRef = useRef<HTMLDivElement>(null)
  const kontoRef = useRef<HTMLDivElement>(null)
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
            />
          </div>
        </div>
      </div>

      {feedAaben && (
        <div ref={feedRef}>
          <NotifikationsFeed
            config={apiConfig}
            onLuk={() => setFeedAaben(false)}
            onAabnSession={(id) => { select(id); setFeedAaben(false); onSurface('chat') }}
          />
        </div>
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
                    {!foldet && (
                      // KODE-gruppen deles yderligere op efter PROJEKT — som i
                      // CC, hvor overskriften er «jarvis-v2 · /media/projects».
                      // Chat-sessioner har intet workspace, saa dér ville en
                      // projekt-overskrift vaere en gruppe uden indhold.
                      g.gruppe === 'kode'
                        ? grupperEfterProjekt(g.sessioner).map((p) => (
                          <Fragment key={p.rod || 'uden'}>
                            <div className="sidebar-label sidebar-projekt">
                              <span className="sidebar-projekt-navn">{p.navn}</span>
                              {p.sti && (
                                <>
                                  <span className="sidebar-projekt-prik" aria-hidden="true">·</span>
                                  <span className="sidebar-projekt-sti" title={p.rod}>{p.sti}</span>
                                </>
                              )}
                            </div>
                            {p.sessioner.map((s) => (
                              <SessionItem
                                key={s.id}
                                id={s.id}
                                title={s.title || 'Uden titel'}
                                active={s.id === activeId}
                                working={isWorking(s.id)}
                                workspaceKind={s.workspace_kind}
                                onSelect={() => { select(s.id); onSurface(s.workspace_kind ? 'code' : 'chat') }}
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
                            workspaceKind={s.workspace_kind}
                            onSelect={() => { select(s.id); onSurface(s.workspace_kind ? 'code' : 'chat') }}
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
            <span>{userName}</span>
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

/** Session-række med "..."-menu (omdøb / eksportér / slet) — vises ved hover. */
function SessionItem({
  id,
  title,
  active,
  working,
  workspaceKind,
  onSelect,
}: {
  id: string
  title: string
  active: boolean
  working?: boolean
  workspaceKind?: string | null
  onSelect: () => void
}) {
  const { rename, remove } = useSessions()
  const { settings } = useSettings()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(title)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!open) return
    const close = () => { setOpen(false); setConfirmDelete(false) }
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
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
          {workspaceKind
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
      <div className="session-menu-anchor" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="session-more" aria-label="Mere" onClick={() => { setOpen((o) => !o); setConfirmDelete(false) }}>
          {/* Oprejst, ikke liggende (Bjørn 20/9-2026). Den liggende form er
              den samme glyf lagt ned; den oprejste er konventionen for en
              menu der folder NEDAD, og den fylder mindre i en smal række. */}
          <MoreVertical size={15} />
        </button>
        {open && (
          <div className="session-menu">
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
