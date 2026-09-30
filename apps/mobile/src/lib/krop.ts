/**
 * Hvilken FORM et værktøjskald har — ikke hvilket værktøj det er.
 *
 * ## Hvorfor former og ikke visere
 *
 * Desk målte det 22/9-2026: 63 værktøjer, 17 med en dedikeret viser (~25 %),
 * og under dem kun 7 delte kort-primitiver. Vores værktøjskasse er 366 navne.
 * Skrev vi én krop pr. værktøj, ville det aldrig blive færdigt. Vi vælger
 * derfor krop pr. RESULTATFORM, og lader faldbacken bære halen.
 *
 * Familien følger resultatets form: et bash-kald giver stdout + exit-kode
 * (terminal), en fil-læsning giver linjer (fil), en skrivning giver en diff.
 * Alt andet falder til rå tekst — og det er ikke en fejl: for små
 * status-objekter ER den rå tekst den rigtige form.
 *
 * ## Navnene skal findes
 *
 * Desk havde otte navne i sin tabel der ikke fandtes i registret (målt
 * 23/9-2026). Det er værre end ubrugeligt — et navn der ikke findes giver en
 * form der LYVER, hvis navnet en dag tages i brug til noget andet. Kilden til
 * sandheden er `core/tools/simple_tools.py::get_tool_definitions`, og
 * vagt-testen i `krop.test.ts` holder denne liste mod den.
 */

export type KropFamilie = 'terminal' | 'fil' | 'diff' | 'fald'

const TERMINAL = new Set([
  'bash', 'operator_bash',
  'bash_session_run', 'operator_bash_session_run',
  'bash_session_open', 'operator_bash_session_open',
  'bash_session_close', 'operator_bash_output',
  'operator_run_in_background', 'operator_session_run',
  'phone_adb_shell',
])

const FIL = new Set(['read_file', 'operator_read_file'])

const DIFF = new Set([
  'edit_file', 'operator_edit_file', 'operator_multi_edit',
  'write_file', 'operator_write_file',
])

/**
 * Et gammelt navn skal pege videre, ikke dø.
 *
 * Desk fandt det med `explore` → `scout_agent` (omdøbt 17/9-2026): uden
 * opslaget faldt hver gemt spejder-tur til den generiske dump, selv om formen
 * stod klar. Vi har endnu ikke et omdøbt navn i disse fire familier — tabellen
 * står her fordi den skal kunne tage imod det uden at nogen skal huske hvor.
 */
const GAMLE: Record<string, string> = {}

/** `operator_read_file` og `read_file` er samme handling for læseren. */
export function kropFor(navn: string): KropFamilie {
  const nu = GAMLE[navn] ?? navn
  if (TERMINAL.has(nu)) return 'terminal'
  if (FIL.has(nu)) return 'fil'
  if (DIFF.has(nu)) return 'diff'
  return 'fald'
}

/* ══ Udtræk af resultatet ═══════════════════════════════════════════════ */

type Data = Record<string, unknown>
const objekt = (v: unknown): v is Data => typeof v === 'object' && v !== null && !Array.isArray(v)
const streng = (v: unknown): string => (typeof v === 'string' ? v : '')

/**
 * Intern hale fra serveren.
 *
 * Hver runde hæfter serveren en kort instruks på det SIDSTE værktøjs-resultat
 * (`visible_followup_results._NUDGE` — statisk og append-only, så
 * prompt-cachen ikke ryger). Den er skrevet til MODELLEN, men gemmes med i
 * turen. Uden klip fejler `JSON.parse` på halen, og kroppen dumper hele JSON'en
 * råt i stedet for stdout — og exit-koden kunne ikke læses.
 *
 * Mærket er `⟳`-parentesen; den skrives ingen andre steder i systemet.
 */
const INTERN_HALE = /\s*\(⟳[\s\S]*\)\s*$/

export function udenHale(tekst: string): string {
  return tekst.replace(INTERN_HALE, '')
}

/** Serverens resultat kan være et JSON-objekt med en eller flere `result`-skaller. */
export function pakUd(result: string | undefined): { vaerdi: unknown; ramme: Data | null } {
  if (!result) return { vaerdi: '', ramme: null }
  const renset = udenHale(result)
  let vaerdi: unknown = renset
  try {
    vaerdi = JSON.parse(renset)
  } catch {
    return { vaerdi, ramme: null }
  }
  const ramme = objekt(vaerdi) ? vaerdi : null
  for (let i = 0; i < 3 && objekt(vaerdi) && 'result' in vaerdi; i++) {
    vaerdi = vaerdi.result
  }
  return { vaerdi, ramme }
}

export function visTekst(v: unknown): string {
  if (typeof v === 'string') return v
  if (v === undefined || v === null) return ''
  return JSON.stringify(v, null, 2)
}

/**
 * Stdout hvis resultatet er vores pakkede form; ellers hele strengen.
 *
 * Vores værktøjer er ikke enige om feltnavnet — `bash_session` har `exit_code`,
 * den almindelige `bash` pakker et objekt med `stdout`, og de fleste har slet
 * ingen. Vi leder efter flere navne frem for at gætte ét.
 */
export function udDel(result: string | undefined): string {
  if (!result) return ''
  const { vaerdi } = pakUd(result)
  if (objekt(vaerdi)) {
    const ud = [vaerdi.stdout, vaerdi.stderr]
      .filter((x) => typeof x === 'string' && x)
      .join('\n')
    if (ud) return ud
  }
  return visTekst(vaerdi)
}

/**
 * Exit-koden — eller 0 når ingen kan findes.
 *
 * Vi læser `exit_code`/`returncode`/`exit_status`/`code` fra JSON, og falder
 * tilbage på tekstmærket `[exit code: N]` som serveren skriver når resultatet
 * ikke er JSON.
 */
export function exitKode(result: string | undefined, fejl: boolean): number {
  if (result) {
    try {
      const o = JSON.parse(udenHale(result)) as Record<string, unknown>
      const r = (o.result ?? o) as Record<string, unknown>
      for (const k of ['exit_code', 'returncode', 'exit_status', 'code']) {
        const v = r[k]
        if (typeof v === 'number') return v
      }
    } catch {
      // ikke JSON — prøv tekstmærket, som serveren bruger
    }
    const m = /\[exit code: (\d+)\]\s*$/.exec(udenHale(result))
    if (m?.[1]) return Number(m[1])
  }
  return fejl ? 1 : 0
}

/**
 * Filens indhold ud af et resultat.
 *
 * `read_file` svarer med filens tekst — nogle gange råt, nogle gange pakket i
 * et objekt. Vi leder efter de feltnavne huset bruger og falder tilbage til
 * hele strengen, så en fil altid kan læses uanset indpakningen.
 */
export function filTekst(result: string | undefined): string {
  if (!result) return ''
  const { vaerdi } = pakUd(result)
  if (objekt(vaerdi)) {
    for (const k of ['content', 'text', 'indhold', 'indhold_tekst']) {
      const v = streng(vaerdi[k])
      if (v) return v
    }
  }
  return visTekst(vaerdi)
}

/** Sidste led af en sti — til filnavnet over linjenumrene. */
export function filnavn(sti: string): string {
  return sti.replace(/\\/g, '/').split('/').filter(Boolean).at(-1) || sti
}
