/**
 * Arbejdslinjen — hvad Jarvis laver lige nu, i HANS egen stemme.
 *
 * ## Hvorfor den findes
 *
 * Serveren sender `working_step` med både det rå værktøjsnavn (`action`) og
 * den færdige label (`detail`) — `detail` er `_tool_label(...)`, altså
 * «Læser fil: useChatScroll.ts». Mobilens reducer kastede `action` væk og
 * beholdt kun strengen, så linjen kun kunne være maskinens.
 *
 * Bjørn 29/9-2026: «Læser en fil: eller køre en kommando er tamt». Han har
 * ret — «fil» gentager hvad filnavnet allerede siger. Desk bærer det samme
 * problem: `LivenessIndicator` skifter til sine egne verber når labelen er
 * boilerplate, men viser den rå label når den er ægte. Det er den søm der
 * lukkes her: handlingsordet kommer fra Jarvis, genstanden fra serveren.
 *
 * ## Hvorfor ét map og ikke to
 *
 * Det frister at lægge et reserve-map på serverens LABEL («Læser fil» →
 * «Læser»). Det gør `visible_tool_labels.py` selv opmærksom på faren ved:
 * desk's `kommandoEmne` fik en liste 23/9, denne kopi gjorde ikke, og «de to
 * sagde hver sit om samme kald». To tabeller der kan drive fra hinanden er
 * værre end én der mangler en post. Derfor: nøglen er værktøjets RÅ navn, og
 * kender vi det ikke, står serverens label uændret. Vi viser aldrig mindre
 * end i dag.
 *
 * ## Ærindet er IKKE her
 *
 * «Læser useChatScroll.ts — hvem skriver til scrollTop?» kan ikke udledes af
 * et værktøjsnavn og en filsti. Serveren kender hvad, ikke hvorfor. Den del
 * venter på at Jarvis selv kan skrive den; indtil da bærer linjen handling og
 * genstand, og intet opdigtet.
 *
 * Rene funktioner — ingen React, ingen I/O. Kan måles uden at rendere.
 */

/** Handlingsord der tager en GENSTAND: «Læser useChatScroll.ts». */
const MED_GENSTAND: Record<string, string> = {
  // Filer
  read_file: 'Læser',
  read_archive: 'Læser',
  write_file: 'Skriver',
  edit_file: 'Retter',
  multi_edit: 'Retter',
  find_files: 'Leder efter',
  glob: 'Leder efter',
  list_dir: 'Ser i',
  search: 'Søger efter',
  grep: 'Søger efter',
  publish_file: 'Lægger op',
  verify_file_contains: 'Tjekker',
  // System
  bash: 'Kører',
  bash_session_run: 'Kører',
  internal_api: 'Kalder',
  db_query: 'Forespørger',
  update_setting: 'Retter',
  // Web
  web_fetch: 'Henter',
  web_scrape: 'Henter',
  web_search: 'Søger efter',
  get_weather: 'Henter vejret for',
  get_news: 'Henter nyheder om',
  // Hukommelse
  search_memory: 'Søger i hukommelsen efter',
  memory_search: 'Søger i hukommelsen efter',
  recall: 'Genkalder',
  remember_this: 'Noterer',
  // Sanser
  analyze_image: 'Ser på',
  read_visual_memory: 'Kigger på rummet',
  // Opgaver
  todo_set: 'Sætter',
  todo_add: 'Tilføjer',
  schedule_task: 'Planlægger',
  // Kode og forslag
  propose_source_edit: 'Foreslår en rettelse i',
  // Kommunikation
  send_discord_dm: 'Skriver til',
  discord_channel: 'Skriver i',
  notify_user: 'Siger til',
  send_telegram_message: 'Skriver til',
  // Agenter
  scout_agent: 'Sender en spejder efter',
  spawn_agent_task: 'Sender en agent efter',
  // Git
  git_log: 'Kigger i historikken',
  git_diff: 'Ser hvad der er ændret i',
  git_status: 'Tjekker arbejdstræet',
  // Værktøjer
  load_more_tools: 'Henter flere værktøjer',
  skill_invoke: 'Bruger en skill',
}

/** Hele sætninger der IKKE tager en genstand — «Indkalder rådet». */
const UDEN_GENSTAND: Record<string, string> = {
  compact_context: 'Komprimerer konteksten',
  look_around: 'Kigger rundt',
  daemon_status: 'Tjekker daemons',
  heartbeat_status: 'Tjekker hjerteslaget',
  central_query: 'Spørger Centralen',
  read_chronicles: 'Læser krønikerne',
  read_dreams: 'Læser drømmene',
  read_self_state: 'Læser selvtilstanden',
}

/** `operator_read_file` og `read_file` er samme handling for læseren. */
function grundNavn(navn: string): string {
  return navn.startsWith('operator_') ? navn.slice('operator_'.length) : navn
}

/**
 * Emnet ud af serverens label.
 *
 * Formatet er `f"{base}: {emne}"` (se `_tool_label` i
 * `core/services/visible_tool_labels.py`). Vi tager emnet — det er allerede
 * gjort rigtigt der, også for bash, hvor `_bash_hint` springer scene-sætningen
 * over så «cd … && npm test» bliver «npm test» og ikke «cd».
 */
function emneFraDetail(detail: string): string {
  const i = detail.indexOf(': ')
  return i < 0 ? '' : detail.slice(i + 2).trim()
}

/**
 * Linjens tekst — eller null når der ikke er noget at vise.
 *
 * @param workingStep serverens `detail`, fx «Læser fil: useChatScroll.ts»
 * @param workingAction værktøjets rå navn, fx `read_file`
 */
export function arbejdslinjeTekst(
  workingStep: string | null | undefined,
  workingAction?: string | null,
): string | null {
  const detail = (workingStep ?? '').trim()
  if (!detail) return null

  const navn = grundNavn((workingAction ?? '').trim())

  const uden = UDEN_GENSTAND[navn]
  if (uden) return uden

  const med = MED_GENSTAND[navn]
  // Ukendt værktøj: serverens label er bedre end ingenting, og bedre end et
  // gæt. Den står uændret — også selv om den er «tam».
  if (!med) return detail

  const emne = emneFraDetail(detail)
  return emne ? `${med} ${emne}` : med
}

/* ══ Tallene i linjen ═════════════════════════════════════════════════════ */

/**
 * Klokken: «12s», «1m 5s», «1h 2m 3s» (Claude Desktops `BS`).
 *
 * Flyttet hertil fra `InlineToolGroup` 30/9-2026, sammen med uret: tal-formen
 * hører til den linje der viser tallet. Desk har samme regel i `varighed`
 * (`lib/jobsApi.ts`), blot med `t` for timer — mobilen har altid skrevet `h`,
 * og det bliver den ved med.
 */
export function formatTid(sek: number): string {
  const s = Math.max(0, Math.floor(sek))
  const t = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const r = s % 60
  return t > 0 ? `${t}h ${m}m ${r}s` : m > 0 ? `${m}m ${r}s` : `${r}s`
}

/**
 * Kort token-tal: 1234 → «1.2k». Desk's regel, ord for ord
 * (`LivenessIndicator.tsx`), så de to klienter skriver samme tal ens.
 */
export function kortTokens(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)
}
