import {
  Wrench, Terminal, FileText, FilePen, FilePlus, FolderTree, Search, Globe,
  Database, MessageSquare, Cpu, PanelRight, Image, Brain, Bell, Calendar,
  Activity, Bot, ListChecks, AlarmClock, GitBranch, RotateCw, Monitor,
  CloudSun, Home, Plug, FileCheck, Users,
  type LucideIcon,
} from 'lucide-react'

export interface ToolMeta {
  label: string
  Icon: LucideIcon
  summarize: (args: Record<string, unknown>, result?: string) => string
}

function firstStr(args: Record<string, unknown>, keys: string[]): string {
  for (const k of keys) {
    const v = args[k]
    if (typeof v === 'string' && v.trim()) return v
  }
  return ''
}

function pathOf(args: Record<string, unknown>): string {
  return String(args.path || args.target_path || args.file_path || args.dir || '')
}

/** Shell-støj: nøgleord, navigation og overskrifter der ikke siger hvad der
 *  skete. `exit` er med fordi «exit 0» aldrig er svaret på hvad der skete. */
const SHELL_STOEJ = /^(for|while|until|if|then|else|elif|fi|do|done|case|esac|in|cd|echo|exit|export|set|unset)\b/

/**
 * Den første kommando i en shell-streng der faktisk siger hvad der skete.
 *
 * Bjørn 23/9-2026: en kommando der begyndte med
 * `for id in 29360132 …; do echo -n "$id -> "; xdotool getwindowname $id; done`
 * blev vist som «Bash for id» — første ord af et loop, som ikke fortæller
 * noget. Vi splitter på shell-operatorer, springer nøgleord, `cd` og
 * `echo`-overskrifter over og tager den første rigtige kommando. Er der ingen
 * tilbage, vises hele strengen som før — vi skjuler aldrig noget.
 */
export function kommandoEmne(cmd: string): string {
  const dele = cmd
    .split(/;|&&|\|\||\||\n/)
    .map((d) => d.trim())
    .filter(Boolean)
  const rigtig = dele.find((d) => !SHELL_STOEJ.test(d) && !/^[A-Za-z_][A-Za-z0-9_]*=/.test(d))
  return (rigtig ?? cmd).trim()
}

/** Kuraterede entries for de mest sete tools. Alle andre dækkes af lookupTool-fallback. */
export const TOOL_REGISTRY: Record<string, ToolMeta> = {
  // Kerne fil/shell
  bash: { label: 'Terminal', Icon: Terminal, summarize: (a) => kommandoEmne(String(a.command ?? '')) },
  operator_bash: { label: 'Terminal', Icon: Terminal, summarize: (a) => kommandoEmne(String(a.command ?? '')) },
  read_file: { label: 'Læs fil', Icon: FileText, summarize: pathOf },
  operator_read_file: { label: 'Læs fil', Icon: FileText, summarize: pathOf },
  write_file: { label: 'Skriv fil', Icon: FilePlus, summarize: pathOf },
  operator_write_file: { label: 'Skriv fil', Icon: FilePlus, summarize: pathOf },
  edit_file: { label: 'Rediger fil', Icon: FilePen, summarize: pathOf },
  operator_edit_file: { label: 'Rediger fil', Icon: FilePen, summarize: pathOf },
  operator_glob: { label: 'Find filer', Icon: Search, summarize: (a) => firstStr(a, ['pattern', 'glob']) },
  operator_grep: { label: 'Søg i kode', Icon: Search, summarize: (a) => firstStr(a, ['pattern', 'query']) },
  operator_list_dir: { label: 'List mappe', Icon: FolderTree, summarize: pathOf },
  // Web + internt
  web_search: { label: 'Websøgning', Icon: Globe, summarize: (a) => firstStr(a, ['query', 'q']) },
  operator_webfetch: { label: 'Hent webside', Icon: Globe, summarize: (a) => firstStr(a, ['url']) },
  internal_api: { label: 'Internt API-kald', Icon: Cpu, summarize: (a) => firstStr(a, ['endpoint', 'path', 'method', 'name']) },
  // UI
  open_ui_panel: { label: 'Panel', Icon: PanelRight, summarize: (a) => (String(a.action) === 'close' ? 'luk' : String(a.panel ?? 'preview')) },
  request_app_action: { label: 'App-handling', Icon: PanelRight, summarize: (a) => String(a.action ?? '') },
  // Hukommelse / brain
  search_memory: { label: 'Søg i hukommelse', Icon: Brain, summarize: (a) => firstStr(a, ['query', 'q', 'text']) },
  search_jarvis_brain: { label: 'Søg i hukommelsen', Icon: Brain, summarize: (a) => firstStr(a, ['query', 'q']) },
  remember_this: { label: 'Minde', Icon: Brain, summarize: (a) => firstStr(a, ['title']) },
  read_brain_entry: { label: 'Læs minde', Icon: Brain, summarize: (a) => firstStr(a, ['title', 'id', 'key']) },
  list_side_tasks: { label: 'Flaggede opgaver', Icon: Calendar, summarize: () => '' },
  flag_side_task: { label: 'Flag til senere', Icon: Calendar, summarize: (a) => firstStr(a, ['title', 'task', 'goal']) },
  // Kanaler / besked
  discord_channel: { label: 'Discord', Icon: MessageSquare, summarize: (a) => firstStr(a, ['action', 'query', 'channel']) },
  // Billede / medie
  openrouter_image: { label: 'Generér billede', Icon: Image, summarize: (a) => firstStr(a, ['prompt']) },
  // Tid / planlægning
  list_scheduled_tasks: { label: 'Planlagte opgaver', Icon: Calendar, summarize: () => '' },
  // Notifikation
  notify_user: { label: 'Notifikation', Icon: Bell, summarize: (a) => firstStr(a, ['message', 'text']) },
  // Dispatch
  dispatch_to_claude_code: { label: 'Kode-dispatch', Icon: Cpu, summarize: (a) => firstStr(a, ['task', 'prompt', 'goal']) },
  dispatch_code_mode_task: { label: 'Kode-opgave', Icon: Cpu, summarize: (a) => firstStr(a, ['task', 'prompt', 'goal']) },
  read_model_config: { label: 'Model-konfig', Icon: Database, summarize: () => '' },
  // Shell-sessioner
  bash_session_run: { label: 'Terminal', Icon: Terminal, summarize: (a) => kommandoEmne(String(a.command ?? '')) },
  operator_bash_session_run: { label: 'Terminal', Icon: Terminal, summarize: (a) => kommandoEmne(String(a.command ?? '')) },
  bash_session_open: { label: 'Åbn shell', Icon: Terminal, summarize: () => '' },
  operator_bash_session_open: { label: 'Åbn shell', Icon: Terminal, summarize: () => '' },
  bash_session_close: { label: 'Luk shell', Icon: Terminal, summarize: () => '' },
  operator_bash_output: { label: 'Shell-output', Icon: Terminal, summarize: () => '' },
  operator_run_in_background: { label: 'Baggrundskørsel', Icon: Terminal, summarize: (a) => kommandoEmne(String(a.command ?? '')) },
  phone_adb_shell: { label: 'Telefon-shell', Icon: Terminal, summarize: (a) => kommandoEmne(String(a.command ?? '')) },
  // Søgning
  search: { label: 'Søg i kode', Icon: Search, summarize: (a) => firstStr(a, ['pattern', 'query']) },
  find_files: { label: 'Find filer', Icon: Search, summarize: (a) => firstStr(a, ['pattern', 'glob']) },
  semantic_search_code: { label: 'Semantisk søgning', Icon: Search, summarize: (a) => firstStr(a, ['query', 'q']) },
  search_sessions: { label: 'Søg i samtaler', Icon: Search, summarize: (a) => firstStr(a, ['query', 'q']) },
  search_chat_history: { label: 'Søg i chat', Icon: Search, summarize: (a) => firstStr(a, ['query', 'q']) },
  // Hukommelse
  recall: { label: 'Husk', Icon: Brain, summarize: (a) => firstStr(a, ['query', 'q']) },
  recall_memories: { label: 'Husk sanseindtryk', Icon: Brain, summarize: (a) => firstStr(a, ['query', 'q']) },
  read_memory_topic: { label: 'Læs emne', Icon: Brain, summarize: (a) => firstStr(a, ['slug', 'topic', 'name']) },
  read_chronicles: { label: 'Læs krønike', Icon: Brain, summarize: () => '' },
  memory_upsert_section: { label: 'Skriv minde', Icon: Brain, summarize: (a) => firstStr(a, ['heading', 'title']) },
  // Filer
  verify_file_contains: { label: 'Verificér fil', Icon: FileCheck, summarize: pathOf },
  publish_file: { label: 'Udgiv fil', Icon: FilePlus, summarize: (a) => firstStr(a, ['filename', 'name']) },
  web_fetch: { label: 'Hent webside', Icon: Globe, summarize: (a) => firstStr(a, ['url']) },
  // Status / system
  central_query: { label: 'Centralen', Icon: Activity, summarize: (a) => firstStr(a, ['action', 'nerve']) },
  db_query: { label: 'Database', Icon: Database, summarize: (a) => firstStr(a, ['sql', 'query']) },
  daemon_status: { label: 'Dæmoner', Icon: Activity, summarize: () => '' },
  read_self_state: { label: 'Egen tilstand', Icon: Activity, summarize: () => '' },
  read_mood: { label: 'Stemning', Icon: Activity, summarize: () => '' },
  heartbeat_status: { label: 'Hjerteslag', Icon: Activity, summarize: () => '' },
  service_status: { label: 'Tjenester', Icon: Activity, summarize: () => '' },
  list_signal_surfaces: { label: 'Signaler', Icon: Activity, summarize: () => '' },
  eventbus_recent: { label: 'Hændelser', Icon: Activity, summarize: () => '' },
  restart_self: { label: 'Genstart', Icon: RotateCw, summarize: () => '' },
  get_weather: { label: 'Vejr', Icon: CloudSun, summarize: (a) => firstStr(a, ['city', 'location']) },
  home_assistant: { label: 'Hjem', Icon: Home, summarize: (a) => firstStr(a, ['entity_id', 'action']) },
  mcp: { label: 'MCP', Icon: Plug, summarize: (a) => firstStr(a, ['server', 'tool']) },
  // Git
  git_log: { label: 'Git-log', Icon: GitBranch, summarize: () => '' },
  // Agenter / opgaver
  spawn_agent_task: { label: 'Send agent', Icon: Bot, summarize: (a) => firstStr(a, ['task', 'prompt', 'goal']) },
  list_agents: { label: 'Agenter', Icon: Bot, summarize: () => '' },
  scout_agent: { label: 'Spejder', Icon: Bot, summarize: (a) => firstStr(a, ['query', 'question', 'task']) },
  convene_council: { label: 'Råd', Icon: Users, summarize: (a) => firstStr(a, ['question', 'topic']) },
  todo_set: { label: 'Opgaveliste', Icon: ListChecks, summarize: () => '' },
  todo_update_status: { label: 'Opdater opgave', Icon: ListChecks, summarize: (a) => firstStr(a, ['todo_id', 'status']) },
  schedule_self_wakeup: { label: 'Planlæg vækning', Icon: AlarmClock, summarize: (a) => firstStr(a, ['prompt', 'reason']) },
  list_self_wakeups: { label: 'Vækninger', Icon: AlarmClock, summarize: () => '' },
  mark_wakeup_consumed: { label: 'Kvittér vækning', Icon: AlarmClock, summarize: (a) => firstStr(a, ['wakeup_id']) },
  // Operator-kanal
  operator_channel: { label: 'Operatør-kanal', Icon: Monitor, summarize: (a) => String(a.action ?? '') },
  operator_session_run: { label: 'Operatør-shell', Icon: Monitor, summarize: (a) => kommandoEmne(String(a.command ?? '')) },
  // Billede
  analyze_image: { label: 'Analysér billede', Icon: Image, summarize: (a) => firstStr(a, ['image_path', 'image_url', 'prompt']) },
  // Værktøjer
  load_more_tools: { label: 'Flere værktøjer', Icon: Wrench, summarize: (a) => firstStr(a, ['query', 'names']) },
  skill_gate: { label: 'Færdighed', Icon: Wrench, summarize: (a) => firstStr(a, ['skill', 'name']) },
}

/**
 * Gamle navne → de nuværende.
 *
 * Et omdøbt værktøj skal MAPPES, ikke slettes. Gemte ture bærer det gamle
 * navn: uden dette falder de til Title Case og den generiske dump, og hele
 * historikken ser dårligere ud end den dag den blev skrevet.
 *
 * 23/9-2026 ryddede vi døde navne ud af `TOOL_REGISTRY` og `KENDTE`. Det var
 * rigtigt — ingen af dem findes i registrets 482 værktøjer. Men `explore`
 * fandtes: den hedder `scout_agent` nu (omdøbt 17/9-2026). Forskellen er
 * hele pointen — et dødt navn skal ud, et OMDØBT skal pege videre.
 *
 * Kun omdøbninger hvor stammen er mekanisk indlysende er med her. Navne hvor
 * vi ikke kan vide om de blev omdøbt eller slettet (fx `channel`,
 * `generate_image`) står bevidst udenfor: et gæt ville tegne en form der
 * lyver om hvad værktøjet gør — værre end den generiske dump.
 */
export const GAMLE_NAVNE: Record<string, string> = {
  // omdøbt 17/9-2026 — samme værktøj, nyt navn
  explore: 'scout_agent',
  // `_run` tilføjet for at skelne kald fra åbn/luk af sessionen
  bash_session: 'bash_session_run',
  operator_bash_session: 'operator_bash_session_run',
  // ordstillingen byttet
  memory_search: 'search_memory',
  search_files: 'search',
  // `operator_`-præfiks tilføjet da værktøjerne fik to spor
  glob: 'operator_glob',
  grep: 'operator_grep',
  list_dir: 'operator_list_dir',
  multi_edit: 'operator_multi_edit',
  // navnet gjort konkret
  notify: 'notify_user',
  memory_write: 'memory_upsert_section',
}

const GENERIC_KEYS = ['query', 'q', 'command', 'path', 'file_path', 'pattern', 'text', 'url', 'name', 'topic', 'prompt', 'action']

/** snake_case → Title Case. operator_-præfiks humaniseres væk. */
function titleCase(name: string): string {
  const base = name.replace(/^operator_/, '')
  return base
    .split('_')
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

/** Slår et tool op. Ukendte tools får en Title-Case-label + generisk opsummering,
 *  så intet tool nogensinde står som rå funktionsnavn. Et gammelt navn slås
 *  op på sit nuværende (se `GAMLE_NAVNE`), så gemte ture beholder deres form. */
export function lookupTool(name: string): ToolMeta {
  const nu = GAMLE_NAVNE[name]
  const hit = TOOL_REGISTRY[name] ?? (nu ? TOOL_REGISTRY[nu] : undefined)
  if (hit) return hit
  return {
    label: titleCase(nu ?? name),
    Icon: Wrench,
    summarize: (a) => firstStr(a, GENERIC_KEYS),
  }
}
