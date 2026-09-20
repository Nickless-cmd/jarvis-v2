/**
 * Liveness-linjens sektioner — værktøjsarbejdet talt sammen pr. familie.
 *
 * Bjørn 19/9-2026: «Der var mere end 4 ting i den første liste du viste mig.»
 * Han havde ret. Første udgave af linjen bar kun de fire statiske tal
 * (varighed · tokens · tænke-tid · jobs). Claude Codes linje bærer også
 * SEKTIONER: hvad der faktisk blev lavet, talt sammen pr. familie — i nutid
 * mens det kører, i datid når det er sket.
 *
 * Læst ud af Claude Code 2.1.271 (Bun-ELF, React i klartekst); noten ligger i
 * `shared/jarvis_brain/reference/2026-09-19-claude-code-s-aktivitetslinje-…`.
 * Derfra er formen lånt, ikke indholdet:
 *
 *  - ÉN boolean styrer HELE linjens grammatik: «editing» mens den kører,
 *    «edited» når den er færdig. Samme skift for alle sektioner.
 *  - En sektion vises kun hvis dens tæller er > 0, i en fast rækkefølge.
 *  - Første ord i første sektion får stort begyndelsesbogstav.
 *  - «andet» fanger værktøjer uden familie, så intet arbejde bliver usynligt.
 *
 * Familienavnene er VORES. CC's «scratchpad», «workshop», «frame» og «repl»
 * findes ikke hos os, og vi har familier CC ikke har (Centralen, hukommelsen,
 * broen til Bjørns maskine). Formen er lånt; indholdet er vores eget.
 */
import type { ContentBlock } from './sseProtocol'

type ToolUse = Extract<ContentBlock, { type: 'tool_use' }>

export interface Sektion {
  key: string
  tekst: string
}

interface Familie {
  key: string
  /** Eksplicitte værktøjsnavne. Eksplicit frem for præfiks: `operator_read_file`
   *  og `read_file` hører sammen, men `operator_run_in_background` gør ikke. */
  navne: string[]
  nutid: string
  datid: string
  /** Udelades for familier uden antal («tjekkede git»). */
  ental?: string
  flertal?: string
}

/** Rækkefølgen er CC's: den mest fortællende handling først, den mest
 *  generiske sidst. `andet` ligger fast til allersidst. */
const FAMILIER: Familie[] = [
  {
    key: 'edit',
    navne: ['write_file', 'edit_file', 'operator_write_file', 'operator_edit_file', 'operator_multi_edit', 'checkpoint'],
    nutid: 'redigerer', datid: 'redigerede', ental: 'fil', flertal: 'filer',
  },
  {
    key: 'git',
    navne: ['git_log', 'git_diff', 'git_status'],
    nutid: 'tjekker git', datid: 'tjekkede git',
  },
  {
    key: 'search',
    navne: ['search', 'operator_grep', 'grep'],
    nutid: 'søger efter', datid: 'søgte efter', ental: 'mønster', flertal: 'mønstre',
  },
  {
    key: 'read',
    navne: ['read_file', 'operator_read_file', 'phone_read_file', 'pdf_read', 'slides_read', 'read_attachment'],
    nutid: 'læser', datid: 'læste', ental: 'fil', flertal: 'filer',
  },
  {
    key: 'find',
    navne: ['find_files', 'operator_glob', 'glob', 'operator_list_dir', 'list_dir'],
    nutid: 'finder', datid: 'fandt', ental: 'fil', flertal: 'filer',
  },
  {
    key: 'web',
    navne: ['web_search', 'web_fetch', 'drive_search'],
    nutid: 'henter fra nettet', datid: 'hentede fra nettet', ental: 'side', flertal: 'sider',
  },
  {
    key: 'see',
    navne: ['analyze_image', 'operator_screenshot', 'phone_photo', 'read_visual_memory', 'openrouter_image', 'openrouter_image_edit'],
    nutid: 'ser', datid: 'så', ental: 'billede', flertal: 'billeder',
  },
  {
    key: 'mcp',
    navne: ['mcp'],
    nutid: 'kalder', datid: 'kaldte', ental: 'MCP-værktøj', flertal: 'MCP-værktøjer',
  },
  {
    key: 'agent',
    navne: ['scout_agent', 'dispatch_code_mode_task'],
    nutid: 'sender', datid: 'sendte', ental: 'agent', flertal: 'agenter',
  },
  {
    key: 'msg',
    navne: ['send_telegram_message', 'discord_channel', 'phone_speak', 'phone_bubble'],
    nutid: 'sender', datid: 'sendte', ental: 'besked', flertal: 'beskeder',
  },
  {
    key: 'bash',
    navne: ['bash', 'operator_bash', 'bash_session_run', 'operator_run_in_background', 'operator_bash_output'],
    nutid: 'kører', datid: 'kørte', ental: 'kommando', flertal: 'kommandoer',
  },
  {
    key: 'memory',
    navne: ['remember_this', 'memory_upsert_section', 'search_jarvis_brain', 'search_memory', 'recall', 'search_sessions', 'set_flag', 'get_flag'],
    nutid: 'husker', datid: 'huskede', ental: 'ting', flertal: 'ting',
  },
  {
    key: 'central',
    navne: ['central_query', 'read_self_state', 'daemon_status', 'nudge_inspect', 'nudge_dismiss'],
    nutid: 'spørger Centralen', datid: 'spurgte Centralen',
  },
  {
    key: 'plan',
    navne: ['todo_list', 'todo_add', 'todo_set', 'todo_update_status', 'todo_remove', 'goal_create', 'decision_create', 'predict_outcome', 'resolve_prediction'],
    nutid: 'fører regnskab', datid: 'førte regnskab', ental: 'punkt', flertal: 'punkter',
  },
  {
    key: 'skill',
    navne: ['skill_invoke', 'propose_new_skill', 'load_more_tools'],
    nutid: 'bruger', datid: 'brugte', ental: 'evne', flertal: 'evner',
  },
]

/** Alt uden familie samles her — så ingen handling bliver usynlig på linjen. */
const ANDET: Familie = {
  key: 'andet',
  navne: [],
  nutid: 'kalder', datid: 'kaldte', ental: 'værktøj', flertal: 'værktøjer',
}

/** Opslag fra værktøjsnavn → familie, bygget én gang. */
const NAVNE_OPSLAG: Map<string, Familie> = (() => {
  const m = new Map<string, Familie>()
  for (const f of FAMILIER) for (const n of f.navne) m.set(n, f)
  return m
})()

function familieFor(navn: string): Familie {
  return NAVNE_OPSLAG.get(navn) ?? ANDET
}

/**
 * Tæl værktøjskaldene sammen pr. familie og form dem som sektioner.
 *
 * @param blocks   runnets content-blokke (kun `tool_use` tælles)
 * @param working  true = nutid («læser»), false = datid («læste»)
 */
export function sektioner(blocks: ContentBlock[] | undefined | null, working: boolean): Sektion[] {
  const antal = new Map<string, number>()
  for (const b of blocks ?? []) {
    if (!b || b.type !== 'tool_use') continue
    const fam = familieFor((b as ToolUse).name)
    antal.set(fam.key, (antal.get(fam.key) ?? 0) + 1)
  }
  if (antal.size === 0) return []

  const ud: Sektion[] = []
  const byg = (f: Familie, n: number) => {
    const verbum = working ? f.nutid : f.datid
    const enhed = n === 1 ? f.ental : f.flertal
    ud.push({ key: f.key, tekst: enhed ? `${verbum} ${n} ${enhed}` : verbum })
  }
  for (const f of FAMILIER) {
    const n = antal.get(f.key)
    if (n) byg(f, n)
  }
  const rest = antal.get(ANDET.key)
  if (rest) byg(ANDET, rest)

  // CC sætter stort begyndelsesbogstav på FØRSTE sektion — og kun der.
  const foerste = ud[0]
  if (foerste) {
    ud[0] = { key: foerste.key, tekst: foerste.tekst.charAt(0).toUpperCase() + foerste.tekst.slice(1) }
  }
  return ud
}

/** Sektionerne som én sætning, adskilt med «, » — CC's separator. */
export function sektionerTekst(blokke: Sektion[]): string {
  return blokke.map((s) => s.tekst).join(', ')
}

/**
 * Hvor mange sektioner linjen viser, før resten samles i «og N andre».
 *
 * Bjørn 20/9-2026: «under et langt run kan den godt udvide sig meget».
 * Målt i den rigtige CSS: et run med otte familier gjorde linjen 69px høj —
 * tre linjer i stedet for én. Sektionerne akkumulerer gennem HELE runnet
 * (der er 15 familier + «andet»), så længden vokser med arbejdet.
 *
 * Tre er valgt efter måling, ikke smag: med varighed + tokens + tænke-tid
 * foran holder linjen sig på én linje ved 820px. Resten samles i ét tal —
 * samme greb som «andet»-familien bruger for værktøjer uden familie.
 *
 * MÅLT 20/9-2026 i den rigtige CSS: med de fire tal foran ombryder linjen ved
 * TRE sektioner (50px = to linjer). Ved to holder den 31px = én linje. Tallet
 * er derfor 2 — det er den bredde linjen faktisk har, ikke den jeg gættede på.
 */
export const MAKS_SEKTIONER = 2

/** Klip sektionerne til det linjen kan bære. `rest` er antallet der blev skjult. */
export function klippSektioner(
  blokke: Sektion[],
  maks: number = MAKS_SEKTIONER,
): { viste: Sektion[]; rest: number } {
  if (blokke.length <= maks) return { viste: blokke, rest: 0 }
  return { viste: blokke.slice(0, maks), rest: blokke.length - maks }
}
