/**
 * Preload — eneste bro mellem renderer og main process.
 *
 * Vi udsætter et MINIMALT API via contextBridge. Renderer kan ikke
 * tilgå Node.js, ipcRenderer eller noget andet uden via dette API.
 */
import { contextBridge, ipcRenderer } from 'electron'

export interface ChannelPluginConfig {
  id: string
  name: string
  botToken: string
  serverId: string
}

export interface JarvisDeskBridge {
  config: {
    get: () => Promise<{ apiBaseUrl: string; authToken: string | null; appId?: string; channelPlugins?: ChannelPluginConfig[] }>
    set: (cfg: { apiBaseUrl?: string; authToken?: string | null; channelPlugins?: ChannelPluginConfig[] }) => Promise<boolean>
  }
  /** Jarvis' egen browser i panelet. Rendereren melder sit rektangel; main
   *  ejer visningen. Se electron/jarvisBrowser.ts. */
  browser: {
    saetRect: (r: { x: number; y: number; width: number; height: number }) => Promise<boolean>
    saetSynlig: (v: boolean) => Promise<boolean>
    faner: () => Promise<{ id: number; url: string; titel: string; aktiv: boolean }[]>
    vaelg: (id: number) => Promise<boolean>
    luk: (id: number) => Promise<boolean>
    aabn: (url: string) => Promise<{ id: number; url: string; titel: string; aktiv: boolean }>
    naviger: (url: string) => Promise<boolean>
  }
  /** Åbn et eksternt link i system-browseren (main filtrerer til http/https/mailto). */
  openExternal: (url: string) => Promise<void>
  /** Registrér aktivt run_id i main-process så det kan cancelles ved quit (R3). */
  setActiveRun: (runId: string | null) => Promise<void>
  /** Giv main-process auth så den kan kalde cancel-endpoint ved quit. */
  setRunAuth: (apiBaseUrl: string, authToken: string | null) => Promise<void>
  /** Registrér den aktuelt fremme session så operator_wakeup re-engagerer dér. */
  setActiveSession: (sessionId: string | null) => Promise<void>
  /** Tænd/sluk systray attention-prik (Jarvis vil noget mens vinduet er skjult). */
  setTrayAttention: (on: boolean) => Promise<void>
  /** Native OS-notifikation når et run slutter. */
  notifyTaskDone: (title: string, body: string) => Promise<void>
  /** Proaktiv device-awareness-notifikation (vises altid, også i fokus). */
  notifyShow: (kind: string, title: string, body: string) => Promise<void>
  /** Jarvis-figuren på skrivebordet (electron/figur.ts). Findes ikke i en
   *  browser-fane — alt der bruger den skal tåle at den mangler. */
  figur: {
    traekStart: (mx: number, my: number) => Promise<void>
    traek: (mx: number, my: number) => Promise<void>
    traekSlut: () => Promise<void>
    hoejde: (h: number, contentHeight?: number, figureCenter?: number, side?: 'over' | 'under', currentCenter?: number) => Promise<void>
    snapshot: () => Promise<{ cursor: { x: number; y: number }; bounds: { x: number; y: number }; side: 'over' | 'under' }>
    menu: () => Promise<void>
    aabnSamtale: (sessionId: string | null) => Promise<void>
    vist: () => Promise<boolean>
    saetVist: (vist: boolean) => Promise<boolean>
    /** Figurens udseende: 'ansigt' (den oprindelige krop) eller 'puls' (mærket). */
    skin: () => Promise<'ansigt' | 'puls'>
    saetSkin: (skin: 'ansigt' | 'puls') => Promise<'ansigt' | 'puls'>
    /** Figur-vinduet: udseendet blev skiftet et andet sted (indstillingerne). */
    paaSkin: (cb: (skin: 'ansigt' | 'puls') => void) => () => void
    /** Stemme-ikonet under figuren. */
    stemme: () => Promise<void>
    /** Hovedvinduet: figuren bad om samtale-mode. */
    paaStemme: (cb: () => void) => () => void
    /** Hovedvinduet: figuren bad om at åbne en samtale. */
    paaAabnSamtale: (cb: (sessionId: string) => void) => () => void
  }
  /** Vinduesstyring til vores egen ramme. Findes ikke i en browser-fane —
   *  knapperne skal derfor SKJULES naar den mangler, ikke fejle. */
  vindue: {
    minimer: () => Promise<void>
    vekselMaksimer: () => Promise<boolean>
    luk: () => Promise<void>
    erMaksimeret: () => Promise<boolean>
    paaMaksimeretAendret: (cb: (maksimeret: boolean) => void) => () => void
  }
  /** Er maskinen vågen (ikke i sleep)? Til device-presence. */
  isAwake: () => Promise<boolean>
  /** Geolocation-opslag (Nominatim/ip-api) via main — sætter korrekt User-Agent. */
  geo: {
    geocode: (address: string) => Promise<{ lat: number; lon: number; label: string } | null>
    reverse: (lat: number, lon: number, precise: boolean) => Promise<string>
    ip: () => Promise<{ lat: number; lon: number; label: string } | null>
  }
  /** Åbn native mappe-vælger; returnerer valgt sti eller null. */
  pickFolder: () => Promise<string | null>
  /** Eksportér markdown til en fil via native gem-dialog; true hvis gemt. */
  exportMarkdown: (markdown: string, suggestedName: string) => Promise<boolean>
  /** Code-mode terminal (§17): kør én kommando lokalt, stream output via onTerminalData. */
  terminal: {
    run: (id: string, command: string, cwd?: string) => Promise<{ ok: boolean; error?: string }>
    signal: (id: string, signal?: NodeJS.Signals) => Promise<{ ok: boolean }>
    /** Abonnér på output-chunks. Returnerer unsubscribe. */
    onData: (cb: (e: { id: string; stream: 'stdout' | 'stderr'; chunk: string }) => void) => () => void
    /** Abonnér på proces-exit. Returnerer unsubscribe. */
    onExit: (cb: (e: { id: string; code: number }) => void) => () => void
  }
  /** Den Intelligente Central: åbn `central`-CLI'en i et rigtigt OS-terminalvindue (owner). */
  central: {
    openCli: () => Promise<{ ok: boolean; error?: string }>
  }
  /** Stream-optagelse: raa SSE-rammer skrevet lokalt (kun hans egen maskine). */
  capture: {
    setEnabled: (on: boolean, days: number) => Promise<{ enabled: boolean; expiresAt: number }>
    status: () => Promise<{
      enabled: boolean; expiresAt: number; active: boolean
      dir: string; files: string[]; bytes: number
    }>
    append: (lines: string[]) => Promise<boolean>
    clear: () => Promise<boolean>
  }
  /** App auto-update (§22.5): lyt på tilgængelig/klar + styr download/install. */
  updates: {
    onAvailable: (cb: (info: { version?: string }) => void) => () => void
    onReady: (cb: (info: { version?: string }) => void) => () => void
    download: () => Promise<void>
    install: () => Promise<void>
  }
  /** Dependency-doctor: detektér + installér manglende værktøjer (git/gh/node/rg). */
  deps: {
    detect: () => Promise<{ tool: string; present: boolean }[]>
    install: (tool: string) => Promise<{ ok: boolean; log?: string }>
  }
  platform: NodeJS.Platform
}

const bridge: JarvisDeskBridge = {
  config: {
    get: () => ipcRenderer.invoke('config:get'),
    set: (cfg) => ipcRenderer.invoke('config:set', cfg),
  },
  browser: {
    saetRect: (r) => ipcRenderer.invoke('browser:rect', r),
    saetSynlig: (v) => ipcRenderer.invoke('browser:synlig', v),
    faner: () => ipcRenderer.invoke('browser:faner'),
    vaelg: (id) => ipcRenderer.invoke('browser:vaelg', id),
    luk: (id) => ipcRenderer.invoke('browser:luk', id),
    aabn: (url) => ipcRenderer.invoke('browser:aabn', url),
    naviger: (url) => ipcRenderer.invoke('browser:naviger', url),
  },
  openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url),
  setActiveRun: (runId) => ipcRenderer.invoke('run:setActive', runId),
  setRunAuth: (apiBaseUrl, authToken) => ipcRenderer.invoke('run:setAuth', apiBaseUrl, authToken),
  setActiveSession: (sessionId) => ipcRenderer.invoke('run:setSession', sessionId),
  setTrayAttention: (on) => ipcRenderer.invoke('tray:attention', on),
  notifyTaskDone: (title, body) => ipcRenderer.invoke('notify:taskDone', title, body),
  notifyShow: (kind, title, body) => ipcRenderer.invoke('notify:show', kind, title, body),
  isAwake: () => ipcRenderer.invoke('power:isAwake'),
  geo: {
    geocode: (address: string) => ipcRenderer.invoke('geo:geocode', address),
    reverse: (lat: number, lon: number, precise: boolean) => ipcRenderer.invoke('geo:reverse', lat, lon, precise),
    ip: () => ipcRenderer.invoke('geo:ip'),
  },
  pickFolder: () => ipcRenderer.invoke('dialog:pickFolder'),
  exportMarkdown: (markdown, suggestedName) => ipcRenderer.invoke('session:exportMarkdown', markdown, suggestedName),
  terminal: {
    run: (id, command, cwd) => ipcRenderer.invoke('terminal:run', { id, command, cwd }),
    signal: (id, signal) => ipcRenderer.invoke('terminal:signal', { id, signal }),
    onData: (cb) => {
      const handler = (_e: unknown, data: { id: string; stream: 'stdout' | 'stderr'; chunk: string }) => cb(data)
      ipcRenderer.on('terminal:data', handler)
      return () => ipcRenderer.removeListener('terminal:data', handler)
    },
    onExit: (cb) => {
      const handler = (_e: unknown, data: { id: string; code: number }) => cb(data)
      ipcRenderer.on('terminal:exit', handler)
      return () => ipcRenderer.removeListener('terminal:exit', handler)
    },
  },
  central: {
    openCli: () => ipcRenderer.invoke('central:openCli'),
  },
  // Stream-optagelse: raa SSE-rammer skrives lokalt paa hans egen maskine.
  // Se noten i main.ts for hvorfor den ligger i klienten og ikke paa serveren.
  capture: {
    setEnabled: (on: boolean, days: number) => ipcRenderer.invoke('capture:setEnabled', on, days),
    status: () => ipcRenderer.invoke('capture:status'),
    append: (lines: string[]) => ipcRenderer.invoke('capture:append', lines),
    clear: () => ipcRenderer.invoke('capture:clear'),
  },
  updates: {
    onAvailable: (cb) => {
      const handler = (_e: unknown, info: { version?: string }) => cb(info)
      ipcRenderer.on('update:available', handler)
      return () => ipcRenderer.removeListener('update:available', handler)
    },
    onReady: (cb) => {
      const handler = (_e: unknown, info: { version?: string }) => cb(info)
      ipcRenderer.on('update:ready', handler)
      return () => ipcRenderer.removeListener('update:ready', handler)
    },
    download: () => ipcRenderer.invoke('update:download'),
    install: () => ipcRenderer.invoke('update:install'),
  },
  deps: {
    detect: () => ipcRenderer.invoke('dep:detect'),
    install: (tool) => ipcRenderer.invoke('dep:install', tool),
  },
  platform: process.platform,
  figur: {
    traekStart: (mx: number, my: number) => ipcRenderer.invoke('figur:traekStart', mx, my),
    traek: (mx: number, my: number) => ipcRenderer.invoke('figur:traek', mx, my),
    traekSlut: () => ipcRenderer.invoke('figur:traekSlut'),
    hoejde: (h: number, contentHeight?: number, figureCenter?: number, side?: 'over' | 'under', currentCenter?: number) =>
      ipcRenderer.invoke('figur:hoejde', h, contentHeight, figureCenter, side, currentCenter),
    snapshot: () => ipcRenderer.invoke('figur:snapshot'),
    menu: () => ipcRenderer.invoke('figur:menu'),
    aabnSamtale: (sessionId: string | null) => ipcRenderer.invoke('figur:aabnSamtale', sessionId),
    vist: () => ipcRenderer.invoke('figur:vist'),
    saetVist: (vist: boolean) => ipcRenderer.invoke('figur:saetVist', vist),
    skin: () => ipcRenderer.invoke('figur:skin'),
    saetSkin: (skin: 'ansigt' | 'puls') => ipcRenderer.invoke('figur:saetSkin', skin),
    paaSkin: (cb: (skin: 'ansigt' | 'puls') => void) => {
      const handler = (_e: unknown, skin: 'ansigt' | 'puls') => cb(skin)
      ipcRenderer.on('figur:skin', handler)
      return () => ipcRenderer.removeListener('figur:skin', handler)
    },
    stemme: () => ipcRenderer.invoke('figur:stemme'),
    paaStemme: (cb: () => void) => {
      const handler = () => cb()
      ipcRenderer.on('figur:stemme', handler)
      return () => ipcRenderer.removeListener('figur:stemme', handler)
    },
    paaAabnSamtale: (cb: (sessionId: string) => void) => {
      const handler = (_e: unknown, sessionId: string) => cb(sessionId)
      ipcRenderer.on('figur:aabnSamtale', handler)
      return () => ipcRenderer.removeListener('figur:aabnSamtale', handler)
    },
  },
  vindue: {
    minimer: () => ipcRenderer.invoke('vindue:minimer'),
    vekselMaksimer: () => ipcRenderer.invoke('vindue:vekselMaksimer'),
    luk: () => ipcRenderer.invoke('vindue:luk'),
    erMaksimeret: () => ipcRenderer.invoke('vindue:erMaksimeret'),
    paaMaksimeretAendret: (cb: (maksimeret: boolean) => void) => {
      const handler = (_e: unknown, maksimeret: boolean) => cb(maksimeret)
      ipcRenderer.on('vindue:maksimeretAendret', handler)
      return () => ipcRenderer.removeListener('vindue:maksimeretAendret', handler)
    },
  },
}

contextBridge.exposeInMainWorld('jarvisDesk', bridge)
