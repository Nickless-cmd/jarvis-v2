import type { ContentBlock } from './sseProtocol'

/** Agent-tidslinje: hvad skete der egentlig i den tur?
 *
 *  Bygget af transskriptets EGNE blokke, ikke af events. Serveren har ingen
 *  ordnet fase-historik pr. run — `visible_runs` har én række, og
 *  `tool.invoked`/`tool.completed` bærer slet ikke run_id, så en
 *  server-tidslinje ville kræve tidsmatch mellem tabeller. Det har givet
 *  forkerte konklusioner før. Blokkene er derimod rigtige pr. konstruktion:
 *  de ER turen, i rækkefølge.
 */

export type FaseSlags =
  | 'taenkte' | 'laeste' | 'soegte' | 'aendrede' | 'koerte' | 'testede' | 'svarede'

export type Fase = {
  slags: FaseSlags
  label: string
  antal: number
  status: 'ok' | 'fejl' | 'koerer'
  /**
   * Hvad der FAKTISK skete: kommandoen, filstien, søgemønstret — plus Jarvis'
   * egen narration undervejs (`progress`-blokke).
   *
   * Bjørn 8/9-2026: «forløbet er rimelig ubrugeligt uden metadata … de viser
   * bare "kørt kommando bash", ikke hvad de faktisk lavede.» Han havde ret:
   * kun testkørsler bar en detalje, resten stod som rene tællinger. Dataen lå
   * i `input` hele tiden.
   */
  detaljer: string[]
}

/** Højst så mange detaljer pr. fase. En fase der slog ti læsninger sammen skal
 *  kunne nævne de første — ikke fylde skærmen med dem. */
const MAX_DETALJER = 6

const LABEL: Record<FaseSlags, (n: number) => string> = {
  taenkte: () => 'Tænkte sig om',
  laeste: (n) => (n === 1 ? 'Læste en fil' : `Læste ${n} filer`),
  soegte: (n) => (n === 1 ? 'Søgte' : `Søgte ${n} gange`),
  aendrede: (n) => (n === 1 ? 'Ændrede en fil' : `Ændrede ${n} filer`),
  koerte: (n) => (n === 1 ? 'Kørte en kommando' : `Kørte ${n} kommandoer`),
  testede: () => 'Kørte tests',
  svarede: () => 'Svarede',
}

/** Er kommandoen en testkørsel? Så fortjener den sin egen fase — «kørte tests
 *  og de fejlede» er det mest interessante et run kan fortælle. */
function erTest(kommando: string): boolean {
  return /\b(pytest|vitest|jest|npm (run )?test|go test|cargo test|tox)\b/.test(kommando)
}

/**
 * Den ENE oplysning der gør fasen læsbar. Rækkefølgen af felter er ikke
 * tilfældig: værktøjerne hedder forskellige ting på tværs af server og
 * operator-sættet, men bærer de samme felter.
 */
function detaljeFor(slags: FaseSlags, input: Record<string, unknown>): string | undefined {
  const tekst = (v: unknown) => {
    const s = String(v ?? '').trim()
    return s ? s.replace(/\s+/g, ' ').slice(0, 120) : ''
  }
  if (slags === 'koerte' || slags === 'testede') return tekst(input.command) || undefined
  if (slags === 'laeste' || slags === 'aendrede') {
    const sti = tekst(input.file_path ?? input.path ?? input.dir_path ?? input.notebook_path)
    // Kun filnavnet: den fulde sti er sjældent det man leder efter, og den
    // skubber alt andet ud af linjen.
    return sti ? sti.split('/').filter(Boolean).slice(-2).join('/') : undefined
  }
  if (slags === 'soegte') {
    return tekst(input.pattern ?? input.query ?? input.q ?? input.glob) || undefined
  }
  return undefined
}

function slagsFor(navn: string, input: Record<string, unknown>): FaseSlags | null {
  const n = navn.toLowerCase()
  if (n.includes('bash') || n.includes('exec')) {
    return erTest(String(input.command ?? '')) ? 'testede' : 'koerte'
  }
  if (n.includes('write_file') || n.includes('edit_file') || n.includes('multi_edit')) return 'aendrede'
  if (n.includes('read_file') || n.includes('list_dir')) return 'laeste'
  if (n.includes('grep') || n.includes('glob') || n.includes('find_files')
      || n === 'search' || n.includes('explore')) return 'soegte'
  return null   // resten er ikke en fase — de ville sløre linjen
}

export function byggeTidslinje(blokke: ContentBlock[]): Fase[] {
  const faser: Fase[] = []

  // Slå ens naboer sammen: seks read_file i træk er ÉN fase «læste 6 filer»,
  // ikke seks linjer man skal scrolle forbi.
  const put = (slags: FaseSlags, status: Fase['status'], detalje?: string) => {
    const sidste = faser[faser.length - 1]
    if (sidste && sidste.slags === slags) {
      sidste.antal += 1
      if (detalje && sidste.detaljer.length < MAX_DETALJER) sidste.detaljer.push(detalje)
      if (status === 'fejl') sidste.status = 'fejl'
      else if (status === 'koerer' && sidste.status === 'ok') sidste.status = 'koerer'
      return
    }
    faser.push({ slags, label: '', antal: 1, status, detaljer: detalje ? [detalje] : [] })
  }

  for (const b of blokke) {
    if (b.type === 'thinking') {
      if (b.thinking.trim()) put('taenkte', 'ok')
    } else if (b.type === 'tool_use') {
      const slags = slagsFor(b.name, b.input ?? {})
      if (!slags) continue
      const status = b.status === 'error' ? 'fejl' : b.status === 'running' ? 'koerer' : 'ok'
      put(slags, status, detaljeFor(slags, b.input ?? {}))
    } else if (b.type === 'progress') {
      // Jarvis' egen narration undervejs («Analyserede billede…»). Den stod før
      // i sit EGET «Forløb»-felt oven over dette — to forløb på samme besked
      // (Bjørn 8/9-2026). Den hører til her: det er netop den metadata linjen
      // manglede. Hænger den på den fase der lige er lagt, ellers falder den
      // ned som sin egen note.
      const m = (b.message || '').trim()
      if (!m) continue
      const sidste = faser[faser.length - 1]
      if (sidste && sidste.slags !== 'svarede' && sidste.detaljer.length < MAX_DETALJER) {
        sidste.detaljer.push(m)
      }
      // Ellers: DROP den. Foerste forsoeg lavede en «Taenkte sig om»-fase af
      // narration der ikke kunne haenge paa noget — og saa stod der en falsk
      // fase fuld af raa vaerktoejsnavne, som var vaerre end at mangle linjen.
      // En narration uden en fase at hoere til beskriver ikke noget nyt.
    } else if (b.type === 'text') {
      if (b.text.trim()) put('svarede', 'ok')
    }
  }

  // Sammenfaldende «svarede» undervejs er støj — kun den sidste tæller som svar.
  const rensede = faser.filter((f, i) => f.slags !== 'svarede' || i === faser.length - 1)
  for (const f of rensede) f.label = LABEL[f.slags](f.antal)
  return rensede
}
