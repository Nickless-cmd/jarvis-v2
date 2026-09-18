/**
 * De mapper på DIN maskine der er valgt i desk (Bjørn 18/9-2026: «trusted
 * folder i workstation er på min maskine, altså den trusted folder der allerede
 * er valgt på min maskine»).
 *
 * Første udgave af vælgeren læste `workspace_trust`-tabellen på serveren. Det
 * var forkert kilde: den havde ti rækker fra juni-juli med `C:\`, `C:\Jarvis`
 * og `/Users/bjornslot/Documents` — poster fra andre maskiner og et andet
 * styresystem. Den ville have vist en liste over mapper der ikke findes.
 *
 * Sandheden om hvilken mappe der er valgt bor i browserens eget lager, hvor
 * CodeView i forvejen gemmer `{kind, root, wsPath}`. Her holdes historikken
 * over de mapper der HAR været valgt, så man kan skifte tilbage uden at gå
 * gennem den native vælger hver gang.
 */
const NOEGLE = 'jarvis-desk:code-ws-historik'
const MAKS = 8

export function laesArbejdsmapper(): string[] {
  try {
    const raa = localStorage.getItem(NOEGLE)
    if (!raa) return []
    const v = JSON.parse(raa)
    return Array.isArray(v) ? v.map(String).filter(Boolean).slice(0, MAKS) : []
  } catch {
    return []
  }
}

export function husArbejdsmappe(sti: string): string[] {
  const rent = (sti || '').trim()
  if (!rent) return laesArbejdsmapper()
  // Nyeste først, ingen dubletter — listen er et genbrugs-greb, ikke et arkiv.
  const ud = [rent, ...laesArbejdsmapper().filter((x) => x !== rent)].slice(0, MAKS)
  try { localStorage.setItem(NOEGLE, JSON.stringify(ud)) } catch { /* ignore */ }
  return ud
}

export function glemArbejdsmappe(sti: string): string[] {
  const ud = laesArbejdsmapper().filter((x) => x !== sti)
  try { localStorage.setItem(NOEGLE, JSON.stringify(ud)) } catch { /* ignore */ }
  return ud
}

/** Sidste led i stien — det man genkender en mappe på. */
export function mappeNavn(sti: string): string {
  const dele = (sti || '').replace(/[\\/]+$/, '').split(/[\\/]/)
  return dele[dele.length - 1] || sti
}
