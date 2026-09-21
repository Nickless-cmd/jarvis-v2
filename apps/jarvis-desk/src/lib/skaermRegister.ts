/**
 * Hvad står på skærmen lige nu — til Jarvis' desk-værktøjer (Claude Desktops
 * `ccd_view`: get_layout / show_pane / close_pane, 19/9-2026).
 *
 * Den synlige samtale-visning (ChatView eller CodeView) skriver sig ind her med
 * sin samtale, sine åbne paneler og hvordan de åbnes/lukkes. `ViewRequestWatcher`
 * slår op her når serveren spørger. Modul-niveau af samme grund som
 * `aendringsFokus`: afsender og modtager deler ingen provider-gren.
 */
export type Panel = 'diff' | 'file' | 'terminal' | 'tasks' | 'browser' | 'artifact' | 'pr' | 'plan'

export interface Skaerm {
  sessionId: string
  /** Hvilken flade samtalen står i — «chat» eller «code». */
  flade: 'chat' | 'code'
  /** De paneler der er åbne nu (CC's `open_panes`; desk tilføjer «preview»). */
  aabne: () => string[]
  /** Vis et panel. Returnerer en fejltekst hvis det ikke kan lade sig gøre, ellers null. */
  vis: (panel: Panel, args: { path?: string; line?: number }) => string | null
  luk: (panel: Panel) => string | null
}

let skaerme: Skaerm[] = []

export function registrerSkaerm(s: Skaerm): () => void {
  skaerme = [...skaerme.filter((x) => x !== s), s]
  return () => { skaerme = skaerme.filter((x) => x !== s) }
}

/** Skærmen der viser DENNE samtale, hvis nogen gør. */
export function skaermFor(sessionId: string): Skaerm | undefined {
  return [...skaerme].reverse().find((s) => s.sessionId === sessionId)
}

/** CC's egne ord, hvor det giver mening: fejlen siger HVAD der mangler. */
export const IKKE_I_DESK: Record<'artifact' | 'pr' | 'plan', string> = {
  artifact: 'Artefakter er ikke et panel ved samtalen i desk — de ligger under «Artefakter» i sidebaren.',
  pr: 'Desk har intet pull request-panel.',
  plan: 'Desk har intet plan-panel.',
}
