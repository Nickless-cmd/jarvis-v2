import { useEffect } from 'react'
import { onRefAabn, aabnJobs, SIDE_OPGAVE_AABN_PANEL_EVENT, type RefAabnDetail } from '../lib/refAabn'
import { aabnSideOpgave } from '../lib/sideOpgaveHighlight'
import { emitHighlight } from '../lib/fileTreeHighlight'
import { usePanel } from '../hooks/usePanel'
import type { Surface } from './shell/Sidebar'

/**
 * Modtager klik på referencer i markdown og åbner den flade der kan vise dem.
 *
 * Ligger i App fordi det er det eneste sted der både har `setSurface` og er
 * inde i `PanelProvider` (så `usePanel` virker). Selve klikket sendes som en
 * CustomEvent fra `MarkdownRenderer` — se lib/refAabn.ts for hvorfor det ikke
 * er en prop.
 *
 * 27/10-2026 (Bjørn): `asg-…`, `wt-…`, `wake-…`, `run-…` og filnavne var døde
 * kode-badges. Nu har hver type en destination:
 *   - `asg`/`run` → Jobs-panelet, hvor `AgentJobRows` allerede viser dem
 *   - `fil`      → fil-træet i code mode (samme vej som open_ui_panel bruger)
 *   - `wt`/`wake`→ preview-panelet med id'et, fordi de INGEN flade har endnu
 *   - `side-…`   → det eksisterende side-opgave-panel
 */
export function RefAabnHost({ setSurface }: { setSurface: (s: Surface) => void }) {
  const panel = usePanel()

  useEffect(() => {
    const aabn = panel.open_
    return onRefAabn(({ kind, vaerdi }: RefAabnDetail) => {
      switch (kind) {
        case 'sideopgave':
          // To lyttere med hver sit ansvar: denne åbner panelet (den manglede
          // før), og `aabnSideOpgave` får SideOpgaveListe til at fremhæve og
          // scrolle til rækken. Uden den første var klikket usynligt når
          // panelet var lukket.
          window.dispatchEvent(new CustomEvent(SIDE_OPGAVE_AABN_PANEL_EVENT))
          aabnSideOpgave(vaerdi)
          return
        case 'agent':
        case 'run':
          setSurface('code')
          aabnJobs(vaerdi)
          return
        case 'fil':
          setSurface('code')
          // Stien er repo-relativ når den indeholder '/', ellers er det bare et
          // filnavn — filtræet kan stadig scrolle til det hvis filen ligger i
          // roden, og ellers viser preview-panelet hvad der blev klikket på.
          emitHighlight(vaerdi, 'repo')
          return
        default:
          // `wt-` og `wake-` har ingen flade i desk endnu (målt 27/10-2026).
          // Preview viser id'et, så det i det mindste kan kopieres — et link
          // der påstår at åbne noget der ikke findes er værre end ét der
          // ærligt viser sig selv.
          aabn({
            kind: 'markdown',
            title: `Reference: ${vaerdi}`,
            content:
              `**${vaerdi}**\n\n` +
              (kind === 'worktree'
                ? 'Et worktree-id. Desk har endnu ingen flade der viser worktrees — ' +
                  'id\'et kan kopieres herfra og slås op i repoet.\n'
                : 'Et selv-væknings-id. Desk har endnu ingen flade der viser ' +
                  'selv-vækninger — id\'et kan kopieres herfra.\n'),
          })
      }
    })
  }, [setSurface, panel.open_])

  return null
}
