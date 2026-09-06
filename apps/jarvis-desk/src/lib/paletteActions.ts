/**
 * Handlinger til Cmd+K-paletten (6/9-2026, Codex' punkt 6).
 *
 * Paletten søgte kun i samtaler. Store apps føles hurtige fordi navigationen
 * ikke kun hænger i sidebaren — man skal kunne skrive «arbejde» og lande der.
 *
 * Hver handling peger på noget der FAKTISK findes. En palette der tilbyder
 * destinationer som ikke er der, er værre end en der kun kan samtaler:
 * den lærer én at lade være med at bruge den.
 */
export interface PaletteHandling {
  id: string
  navn: string
  /** Hvad man ser når man lander — så valget ikke er et gæt. */
  hvad?: string
  /** Ord der også skal ramme den. Dansk OG engelsk: man skriver begge dele. */
  ord: string[]
  /** Kun for owner? */
  ejer?: boolean
}

export const PALETTE_HANDLINGER: PaletteHandling[] = [
  { id: 'zone:mc', navn: 'Arbejde', hvad: 'Kø, kørsler og godkendelser',
    ord: ['work', 'cowork', 'queue', 'kø', 'godkend', 'runs'] },
  { id: 'surface:memory', navn: 'Hukommelse', hvad: 'Det han husker',
    ord: ['memory', 'huske', 'minder'] },
  { id: 'surface:gallery', navn: 'Galleri', hvad: 'Billeder og artifacts',
    ord: ['gallery', 'billeder', 'artifacts', 'images'] },
  { id: 'surface:scheduling', navn: 'Planlagt', hvad: 'Opgaver på klokken',
    ord: ['scheduling', 'planlagt', 'cron', 'schedule', 'wakeup'] },
  { id: 'zone:workspace', navn: 'Arbejdsbænk', hvad: 'Operator-kanal, fortryd, kontakter',
    ord: ['workbench', 'operator', 'kanal', 'checkpoint', 'fortryd', 'sandbox'],
    ejer: true },
  { id: 'zone:connections', navn: 'Forbindelser', hvad: 'MCP-servere og apps',
    ord: ['mcp', 'apps', 'connections', 'plugins', 'forbind'] },
  { id: 'zone:privacy', navn: 'Privatliv & tilladelser', hvad: 'Hvad han må',
    ord: ['privacy', 'permission', 'tilladelse', 'privat'] },
  { id: 'zone:konto', navn: 'Konto', hvad: 'Bruger, kvote, adgang',
    ord: ['account', 'konto', 'kvote', 'quota', 'login'] },
  { id: 'zone:notifications', navn: 'Notifikationer', ord: ['notif', 'push', 'besked'] },
  { id: 'zone:appearance', navn: 'Udseende', ord: ['tema', 'theme', 'dark', 'lys'] },
]

/** Simpel delstrengs-match på navn og synonymer. Tom søgning → alt. */
export function filtrerHandlinger(
  q: string, erEjer: boolean, handlinger = PALETTE_HANDLINGER,
): PaletteHandling[] {
  const synlige = handlinger.filter((h) => !h.ejer || erEjer)
  const s = q.trim().toLowerCase()
  if (!s) return synlige
  return synlige.filter(
    (h) => h.navn.toLowerCase().includes(s)
      || (h.hvad ?? '').toLowerCase().includes(s)
      || h.ord.some((o) => o.includes(s)),
  )
}
