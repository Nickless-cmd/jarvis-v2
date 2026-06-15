import {
  Wrench, Terminal, FileText, FilePen, FilePlus, FolderTree, Search, Globe,
  Database, MessageSquare, Cpu, PanelRight, Image, Brain, Bell, Calendar,
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

/** Kuraterede entries for de mest sete tools. Alle andre dækkes af lookupTool-fallback. */
export const TOOL_REGISTRY: Record<string, ToolMeta> = {
  // Kerne fil/shell
  bash: { label: 'Terminal', Icon: Terminal, summarize: (a) => String(a.command ?? '') },
  operator_bash: { label: 'Terminal', Icon: Terminal, summarize: (a) => String(a.command ?? '') },
  read_file: { label: 'Læs fil', Icon: FileText, summarize: pathOf },
  operator_read_file: { label: 'Læs fil', Icon: FileText, summarize: pathOf },
  write_file: { label: 'Skriv fil', Icon: FilePlus, summarize: pathOf },
  operator_write_file: { label: 'Skriv fil', Icon: FilePlus, summarize: pathOf },
  edit_file: { label: 'Rediger fil', Icon: FilePen, summarize: pathOf },
  operator_edit_file: { label: 'Rediger fil', Icon: FilePen, summarize: pathOf },
  glob: { label: 'Find filer', Icon: Search, summarize: (a) => firstStr(a, ['pattern', 'glob']) },
  operator_glob: { label: 'Find filer', Icon: Search, summarize: (a) => firstStr(a, ['pattern', 'glob']) },
  grep: { label: 'Søg i kode', Icon: Search, summarize: (a) => firstStr(a, ['pattern', 'query']) },
  operator_grep: { label: 'Søg i kode', Icon: Search, summarize: (a) => firstStr(a, ['pattern', 'query']) },
  list_dir: { label: 'List mappe', Icon: FolderTree, summarize: pathOf },
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
  search_jarvis_brain: { label: 'Søg i brain', Icon: Brain, summarize: (a) => firstStr(a, ['query', 'q']) },
  remember_this: { label: 'Husk', Icon: Brain, summarize: (a) => firstStr(a, ['text', 'content', 'note']) },
  read_brain_entry: { label: 'Læs brain-entry', Icon: Brain, summarize: (a) => firstStr(a, ['id', 'key']) },
  // Kanaler / besked
  discord_channel: { label: 'Discord', Icon: MessageSquare, summarize: (a) => firstStr(a, ['action', 'query', 'channel']) },
  // Billede / medie
  generate_image: { label: 'Generér billede', Icon: Image, summarize: (a) => firstStr(a, ['prompt']) },
  // Tid / planlægning
  list_scheduled_tasks: { label: 'Planlagte opgaver', Icon: Calendar, summarize: () => '' },
  // Notifikation
  notify: { label: 'Notifikation', Icon: Bell, summarize: (a) => firstStr(a, ['message', 'text']) },
  // Dispatch
  dispatch_to_claude_code: { label: 'Kode-dispatch', Icon: Cpu, summarize: (a) => firstStr(a, ['task', 'prompt', 'goal']) },
  dispatch_code_mode_task: { label: 'Kode-opgave', Icon: Cpu, summarize: (a) => firstStr(a, ['task', 'prompt', 'goal']) },
  read_model_config: { label: 'Model-konfig', Icon: Database, summarize: () => '' },
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
 *  så intet tool nogensinde står som rå funktionsnavn. */
export function lookupTool(name: string): ToolMeta {
  const hit = TOOL_REGISTRY[name]
  if (hit) return hit
  return {
    label: titleCase(name),
    Icon: Wrench,
    summarize: (a) => firstStr(a, GENERIC_KEYS),
  }
}
