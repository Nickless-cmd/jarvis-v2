/**
 * Rundens arbejdstrin — de FAKTISKE kald, ikke en fortegnelse over dem.
 *
 * ## Hvorfor den er et eget modul
 *
 * Bjørn 15/11-2026: «den aktive runde viser processen, afsluttede runder viser
 * resultatet». Rækkevisningen kunne i forvejen fortælle HVAD der blev gjort
 * (én linje, se `toolRound.summarizeRound`), men ikke hvordan arbejdet skred
 * frem: de enkelte trin lå bag folden. Modulet her oversætter rundens
 * `ArbejdsElement[]` til den liste fladen tegner under overskriften.
 *
 * ## Reglen
 *
 * Et trin findes KUN hvis serveren sendte et `tool_use` for det. Der er ingen
 * tælling, ingen udledning af «cirka tre trin» og ingen reserverede pladser:
 * en runde med to kald har to trin, og en runde der ikke har kaldt noget har
 * ingen. Det er hele forskellen mellem en statusflade og teater.
 *
 * ## Den ærlige fjerde tilstand
 *
 * `status: 'running'` betyder to forskellige ting. Mens runden er AKTIV betyder
 * det «i gang». Når runden ikke længere er aktiv betyder det at kaldet aldrig
 * fik et svar — og så må det ikke se ud som om det lykkedes. `afslutForladteKald`
 * (BlocksRenderer) retter den samme tilstand for bobblevisningen; her får den
 * sit eget udfald, fordi trinnet skal kunne SES som afbrudt frem for at ligne
 * et kald der stadig arbejder.
 */
import type { ArbejdsElement } from './raekkeModel'
import { describeTool } from './toolRound'

export type TrinStatus = 'done' | 'active' | 'failed' | 'afbrudt'

export interface ArbejdsTrin {
  /** `tool_use`-blokkens id fra serveren. Aldrig et indeks: listen må ikke
   *  genopbygges når et trin skifter status midt i en strøm. */
  id: string
  /** Menneskets ord for handlingen — «Læste RaekkeTranskript.tsx». */
  tekst: string
  status: TrinStatus
  tool: string
  /** Kort, ærlig tilføjelse når udfaldet ikke er et svar. */
  note?: string
}

/**
 * Runde-elementerne → trin, i den rækkefølge de blev kaldt.
 *
 * `aktiv` er rundens tilstand, ikke trinnets: den afgør om et `running`-kald
 * er i gang eller efterladt.
 */
export function arbejdsTrin(elementer: readonly ArbejdsElement[], aktiv: boolean): ArbejdsTrin[] {
  const ud: ArbejdsTrin[] = []
  for (const e of elementer) {
    if (e.slags !== 'blok') continue
    const b = e.blok
    if (b.type !== 'tool_use') continue
    const raa = b.status ?? 'running'
    // `anomali` er husets eget stempel på et kald der aldrig fik et svar
    // (`afslutForladteKald`). Det er den ærlige kilde: persisterede kald bærer
    // ingen `status`, så uden den blev et historisk kald læst som «kører» →
    // «afbrudt» — og kald MED et resultat blev meldt uden (målt 15/11-2026).
    const forladt = b.anomali === 'uden-resultat'
    const status: TrinStatus = raa === 'error'
      ? 'failed'
      : forladt
        ? 'afbrudt'
        : raa === 'running'
          ? (aktiv ? 'active' : 'afbrudt')
          : 'done'
    // Nutid kun for det trin der faktisk kører. Et efterladt kald får
    // datid som de andre — dets tilstand står i `status` og i `note`, ikke i
    // en verbalform der lover at det stadig arbejder.
    const tekst = describeTool(
      b.name, b.input, status === 'active', b.partialJson, b.result, b.status,
    )
    ud.push({
      id: b.id,
      tekst,
      status,
      tool: b.name,
      ...(status === 'afbrudt' ? { note: 'uden resultat' } : {}),
    })
  }
  return ud
}

/** Antal trin der ikke endte med et svar — til den ærlige metatekst. */
export function uafsluttede(trin: readonly ArbejdsTrin[]): number {
  return trin.filter((t) => t.status === 'afbrudt').length
}

/** Antal trin der fejlede. */
export function fejlede(trin: readonly ArbejdsTrin[]): number {
  return trin.filter((t) => t.status === 'failed').length
}

/** De ærlige advarsler på en AFLUTTET runde — eller tom når alt gik som det
 *  skulle.
 *
 *  Bjørn 15/11-2026: «1 arbejdstrin · Fold ud — denne del skal væk fra selve
 *  rundelinjen». Antallet og fold-vejledningen var staffage: pilen i rækken
 *  viser allerede at den kan foldes ud, og tallet sagde intet om udfaldet.
 *  Tilbage står kun det man ikke kan se af sig selv — at noget fejlede eller
 *  aldrig fik et svar. */
export function trinMeta(trin: readonly ArbejdsTrin[]): string {
  const uaf = uafsluttede(trin)
  const fejl = fejlede(trin)
  const dele: string[] = []
  if (uaf > 0) dele.push(uaf === trin.length ? 'uden resultat' : `${uaf} uden resultat`)
  if (fejl > 0) dele.push(fejl === 1 ? '1 fejlede' : `${fejl} fejlede`)
  return dele.join(' · ')
}
