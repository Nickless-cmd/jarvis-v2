/**
 * Inddeling af sessioner i sidepanelet.
 *
 * Bjørn 8/9-2026: «sessioner i panelet bør ligge i katalog chat mode, code mode
 * og proaktive/autonome runs.. sessioner i side panelet er rodet».
 *
 * Rodet var reelt: 278 chat-sessioner, 181 autonome og én proaktiv lå i én
 * flad liste — og indtil samme dag hed chat-sessionerne alle sammen «Ny
 * samtale», så navnene hjalp heller ikke.
 *
 * Inddelingen bruger data klienten allerede får (`id` og `workspace_kind`), så
 * der skal ikke en API-ændring til. Og den bruger appens EGEN definition af en
 * kode-session — `workspace_kind` sat — frem for at indføre en ny: sidebaren
 * åbner i forvejen en session i kode-fladen på præcis det kriterium
 * (`onSurface(s.workspace_kind ? 'code' : 'chat')`). To definitioner af det
 * samme ville drive fra hinanden.
 */

export type SessionGruppe = 'chat' | 'kode' | 'baggrund'

export interface GrupperbarSession {
  id: string
  workspace_kind?: string | null
}

/** Autonome kørsler og den proaktive kanal. Præfikserne er runtime'ens egne:
 *  `auto-dream-*`, `auto-recurring-*`, `auto-heartbeat-*`, `auto-wakeup-*`,
 *  `auto-work-*`, `auto-autonomous-*` — plus den ene faste `proactivity-bridge`. */
export function erBaggrund(id: string): boolean {
  const s = (id || '').toLowerCase()
  return s.startsWith('auto-') || s === 'proactivity-bridge'
}

export function grupperAf(s: GrupperbarSession): SessionGruppe {
  if (erBaggrund(s.id)) return 'baggrund'
  return s.workspace_kind ? 'kode' : 'chat'
}

export const GRUPPE_NAVN: Record<SessionGruppe, string> = {
  chat: 'samtaler',
  kode: 'kode',
  baggrund: 'proaktive & autonome',
}

/**
 * Hvilke grupper hører til hvilken mode (Bjørn 8/9-2026: «istedet for at vise
 * chat samtale i code mode og omvendt … sådan de samtaler der hører til det
 * pågældende mode kun bliver vist»).
 *
 * Baggrunds-kørslerne ligger under chat, ikke kode: de er samtaler Jarvis selv
 * har startet, og de har ingen workspace. Havde de ligget begge steder, ville
 * de være dukket op to gange — og det er præcis den slags rod inddelingen blev
 * lavet for at fjerne.
 */
export const GRUPPER_I_MODE: Record<'chat' | 'code', SessionGruppe[]> = {
  chat: ['chat', 'baggrund'],
  code: ['kode'],
}

/** Rækkefølgen er fast og betyder noget: det han selv har skrevet står øverst,
 *  maskinens egne kørsler nederst. */
export const GRUPPE_ORDEN: SessionGruppe[] = ['chat', 'kode', 'baggrund']

/**
 * Del listen op uden at ændre rækkefølgen inden for hver gruppe — serveren
 * sorterer allerede på `updated_at`, og en anden sortering her ville betyde at
 * "øverst" holdt op med at betyde "senest".
 */
export function grupperSessioner<T extends GrupperbarSession>(
  sessioner: T[],
): { gruppe: SessionGruppe; navn: string; sessioner: T[] }[] {
  const bunker: Record<SessionGruppe, T[]> = { chat: [], kode: [], baggrund: [] }
  for (const s of sessioner || []) bunker[grupperAf(s)].push(s)
  return GRUPPE_ORDEN
    .filter((g) => bunker[g].length > 0)
    .map((g) => ({ gruppe: g, navn: GRUPPE_NAVN[g], sessioner: bunker[g] }))
}

/* ── Projekt-gruppering ───────────────────────────────────────────────────
   Bjørn 16/9-2026: «det kunne være fint hvis man kunne projekt gruppere
   sessionerne.. du kan se hvorn det ser ud i cc».

   I CC hedder grupperne efter projektet: «jarvis-v2 · /media/projects». Det
   er præcis den oplysning der HAR ligget i basen hele tiden — kolonnen
   `workspace_root` — men som listningen aldrig sendte med. Endnu et tilfælde
   af at mekanismen fandtes og kalderen manglede.

   Kun kode-sessioner har et projekt. Chat-sessioner har intet workspace, og
   at opfinde et til dem ville være en gruppe uden indhold. */

export interface ProjektSession extends GrupperbarSession {
  workspace_root?: string | null
}

/** «/media/projects/jarvis-v2» → { navn: 'jarvis-v2', sti: '/media/projects' }
 *
 *  Windows-stier deles på «\» — «C:\Jarvis» findes i hans egne data, og en
 *  deling der kun kender «/» ville give hele strengen som navn. */
export function projektNavn(rod: string): { navn: string; sti: string } {
  const r = String(rod || '').trim().replace(/[/\\]+$/, '')
  if (!r) return { navn: '', sti: '' }
  const skille = r.includes('\\') ? '\\' : '/'
  const dele = r.split(/[/\\]/).filter(Boolean)
  if (dele.length === 0) return { navn: r, sti: '' }
  const navn = dele[dele.length - 1]!
  const sti = dele.slice(0, -1).join(skille)
  return { navn, sti: sti ? (skille === '/' ? `/${sti}` : sti) : '' }
}

export interface ProjektGruppe<T> {
  /** Stien — gruppens identitet. Tom = sessioner uden projekt. */
  rod: string
  /** «jarvis-v2» */
  navn: string
  /** «/media/projects» — vises dæmpet efter navnet, som i CC. */
  sti: string
  sessioner: T[]
}

/**
 * Del sessionerne op efter PROJEKT.
 *
 * Rækkefølgen inden for en gruppe røres ikke (serveren sorterer på
 * `updated_at`). Grupperne selv står efter deres nyeste session, så det
 * projekt man sidst arbejdede i står øverst — ikke alfabetisk, som ville
 * lade et gammelt projekt ligge og fylde foran det man er i gang med.
 */
export function grupperEfterProjekt<T extends ProjektSession>(
  sessioner: T[],
): ProjektGruppe<T>[] {
  const bunker = new Map<string, T[]>()
  for (const s of sessioner || []) {
    const rod = String(s.workspace_root || '').trim()
    const liste = bunker.get(rod)
    if (liste) liste.push(s); else bunker.set(rod, [s])
  }
  return [...bunker.entries()]
    .map(([rod, liste]) => {
      const { navn, sti } = projektNavn(rod)
      return { rod, navn: navn || 'Uden projekt', sti, sessioner: liste }
    })
    // Sessioner uden projekt sidst: de hører ikke til noget, og en gruppe
    // uden navn øverst ville skubbe det man arbejder i nedad.
    .sort((a, b) => (a.rod ? 0 : 1) - (b.rod ? 0 : 1))
}
