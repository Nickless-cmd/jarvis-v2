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
