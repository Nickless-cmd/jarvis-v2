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
  { id: 'zone:mc', navn: 'Mission Control', hvad: 'Kø, kørsler og godkendelser',
    ord: ['arbejde', 'work', 'cowork', 'queue', 'kø', 'godkend', 'runs'] },
  { id: 'zone:agentPool', navn: 'Agent pool', hvad: 'Agenter, mål og seneste arbejde',
    ord: ['agent', 'agents', 'dispatch', 'råd'], ejer: true },
  { id: 'zone:capacity', navn: 'Modeller og kapacitet', hvad: 'Cheap Lane og udbydere',
    ord: ['cheap', 'lane', 'model', 'provider', 'udbyder', 'kapacitet'], ejer: true },
  { id: 'zone:integrations', navn: 'Værktøjer og forbindelser', hvad: 'Marketplace, apps, MCP og plugins',
    ord: ['marketplace', 'mcp', 'apps', 'connections', 'plugins', 'forbind'] },
  { id: 'zone:general', navn: 'Generelt', hvad: 'Udseende, sprog, notifikationer og lokation',
    ord: ['tema', 'theme', 'dark', 'lys', 'sprog', 'svarstil', 'notif', 'notifikationer', 'push', 'besked', 'lokation', 'placering'] },
  { id: 'zone:account', navn: 'Konto og sikkerhed', hvad: 'Profil, kvote, privatliv og tilladelser',
    ord: ['account', 'konto', 'kvote', 'quota', 'login', 'privacy', 'permission', 'tilladelse', 'privatliv', '2fa'] },
  { id: 'zone:workspace', navn: 'Arbejdsområde', hvad: 'Mapper, filer og arbejdskontrol',
    ord: ['workbench', 'operator', 'kanal', 'checkpoint', 'fortryd', 'sandbox', 'workspace'] },
  { id: 'zone:jarvis', navn: 'Jarvis og hukommelse', hvad: 'Hukommelse, tilstedeværelse og Jarvis',
    ord: ['memory', 'huske', 'minder', 'presence', 'tilstedeværelse'] },
  { id: 'zone:system', navn: 'Systemstatus', hvad: 'Central og Jarvis Mind',
    ord: ['central', 'mind', 'runtime', 'system'], ejer: true },
  { id: 'zone:about', navn: 'Om og hjælp', hvad: 'Version, genveje og forbindelse',
    ord: ['about', 'help', 'hjælp', 'genvej'] },
  { id: 'surface:memory', navn: 'Hukommelse', hvad: 'Det han husker',
    ord: ['memory', 'huske', 'minder'] },
  // «og artifacts» stod her, men galleriet har aldrig vist andet end billeder
  // (det henter kun `listImages`). Artefakterne har deres egen flade nu.
  { id: 'surface:gallery', navn: 'Galleri', hvad: 'Billeder',
    ord: ['gallery', 'billeder', 'images'] },
  { id: 'surface:artifacts', navn: 'Artefakter', hvad: 'Filer Jarvis har skrevet og rettet i mappen',
    ord: ['artifacts', 'artefakter', 'filer', 'ændringer', 'diff'] },
  { id: 'surface:scheduling', navn: 'Planlagt', hvad: 'Opgaver på klokken',
    ord: ['scheduling', 'planlagt', 'cron', 'schedule', 'wakeup'] },
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
