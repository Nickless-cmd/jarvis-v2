/**
 * Kroppene i rækkevisningen — de få former, ikke de mange værktøjer.
 *
 * ## Hvorfor det er syv former og ikke 366 visere
 *
 * Målt i DSH 22/9-2026: 63 værktøjer, 17 med dedikeret viser (~25 %), og
 * under dem kun 7 delte kort-primitiver. Resten går til en faldback der ikke
 * er fattig — den kører de samme kortmodeller.
 *
 * Vores værktøjskasse er 366 navne. Skrev vi en krop pr. værktøj, ville det
 * aldrig blive færdigt. Vi vælger derfor krop pr. RESULTATFORM, og lader
 * faldbacken bære halen. Det er den beslutning der gør visningen mulig.
 *
 * ## Etiketterne er engelske med vilje
 *
 * Bjørn 22/9-2026: «jeg kan godt li det står på eng. Altså rækkerne».
 * `TOOL_REGISTRY` er dansk og bruges af bobblevisningen — den rører vi ikke.
 * Rækkevisningen har derfor sin egen etiket-tabel og falder tilbage på
 * registrets label for alt vi ikke har navngivet.
 */
import type { ReactNode } from 'react'
import { lookupTool } from '../../lib/toolRegistry'

export type Familie = 'terminal' | 'diff' | 'io' | 'liste' | 'web' | 'spoergsmaal' | 'billede' | 'fald'

interface Post { etiket: string; familie: Familie }

/** Kun det vi har set i produktion. Alt andet falder igennem med vilje. */
const KENDTE: Record<string, Post> = {
  bash: { etiket: 'Bash', familie: 'terminal' },
  operator_bash: { etiket: 'Bash', familie: 'terminal' },
  bash_session: { etiket: 'Bash', familie: 'terminal' },
  operator_bash_session: { etiket: 'Bash', familie: 'terminal' },
  read_file: { etiket: 'Read', familie: 'io' },
  operator_read_file: { etiket: 'Read', familie: 'io' },
  write_file: { etiket: 'Write', familie: 'io' },
  operator_write_file: { etiket: 'Write', familie: 'io' },
  publish_file: { etiket: 'Write', familie: 'io' },
  remember_this: { etiket: 'Write', familie: 'io' },
  edit_file: { etiket: 'Edit', familie: 'diff' },
  operator_edit_file: { etiket: 'Edit', familie: 'diff' },
  find_files: { etiket: 'Glob', familie: 'liste' },
  operator_list_dir: { etiket: 'Glob', familie: 'liste' },
  grep: { etiket: 'Grep', familie: 'liste' },
  memory_search: { etiket: 'Search', familie: 'liste' },
  web_search: { etiket: 'Search', familie: 'web' },
  web_fetch: { etiket: 'Fetch', familie: 'web' },
  analyze_image: { etiket: 'Read image', familie: 'billede' },
  verify_file_contains: { etiket: 'Verify', familie: 'io' },
}

export function postFor(navn: string): Post {
  return KENDTE[navn] ?? { etiket: lookupTool(navn).label, familie: 'fald' }
}

/**
 * Exit-koden. Vores 366 værktøjer er ikke enige om feltnavnet — `bash_session`
 * har `exit_code`, den almindelige `bash` pakker et objekt med `stdout`, og de
 * fleste har slet ingen. Derfor leder vi efter flere navne og falder tilbage
 * på fejlflaget frem for at gætte et tal.
 *
 * Målt i DSH: `exit 0` tegner INGEN pille — kun ikke-nul markeres. Det er
 * halvdelen af forskellen mellem «rolig» og «terminal-agtig».
 */
export function exitKode(result: string | undefined, fejl: boolean): number {
  if (result) {
    try {
      const o = JSON.parse(result) as Record<string, unknown>
      const r = (o.result ?? o) as Record<string, unknown>
      for (const k of ['exit_code', 'returncode', 'exit_status', 'code']) {
        const v = r[k]
        if (typeof v === 'number') return v
      }
    } catch {
      // ikke JSON — proev tekstmarkoeren, som DSH bruger
    }
    const m = /\[exit code: (\d+)\]\s*$/.exec(result)
    if (m?.[1]) return Number(m[1])
  }
  return fejl ? 1 : 0
}

/** Stdout hvis resultatet er vores pakkede form; ellers hele strengen. */
export function udDel(result: string | undefined): string {
  if (!result) return ''
  try {
    const o = JSON.parse(result) as Record<string, unknown>
    const r = (o.result ?? o) as Record<string, unknown>
    const ud = [r.stdout, r.stderr].filter((x) => typeof x === 'string' && x).join('\n')
    if (ud) return ud
  } catch { /* ikke JSON */ }
  return result
}

/* ══ De syv former ══════════════════════════════════════════════════════ */

export function Terminal({ cmd, ud, exit }: { cmd: string; ud: string; exit: number }) {
  return (
    <div className="rv-kort rv-term" data-exit={exit}>
      <div className="rv-kh">
        <span>{cmd}</span>
        <span className="rv-exit">exit code {exit}</span>
      </div>
      <pre>{ud}</pre>
    </div>
  )
}

export function Diff({ linjer }: { linjer: { k: 'add' | 'del' | 'ctx'; t: string }[] }) {
  return (
    <div className="rv-kort rv-diff">
      <pre>{linjer.map((l, i) => <span key={i} className="rv-l" data-k={l.k}>{l.t}{'\n'}</span>)}</pre>
    </div>
  )
}

export function IndUd({ ind, ud }: { ind: string; ud: string }) {
  return (
    <div className="rv-kort">
      <div className="rv-par"><div className="rv-mrk">IN</div><div className="rv-v">{ind}</div></div>
      <div className="rv-par"><div className="rv-mrk">OUT</div><div className="rv-v">{ud}</div></div>
    </div>
  )
}

export function Liste({ raekker }: { raekker: { p?: string; v: string }[] }) {
  return (
    <div className="rv-kort rv-liste">
      {raekker.map((r, i) => (
        <div key={i} className="rv-i">
          {r.p && <span className="rv-p">{r.p}</span>}
          <span>{r.v}</span>
        </div>
      ))}
    </div>
  )
}

export function Web({ traef }: { traef: { dom: string; titel: string }[] }) {
  return (
    <div className="rv-kort rv-web">
      {traef.map((t, i) => (
        <div key={i} className="rv-i">
          <div className="rv-dom">{t.dom}</div>
          <div className="rv-t">{t.titel}</div>
        </div>
      ))}
    </div>
  )
}

export function Spoergsmaal({ q, svar }: { q: string; svar: string }) {
  return (
    <div className="rv-kort rv-sp">
      <div className="rv-q">{q}</div>
      <div className="rv-a"><span className="rv-m">svar</span><span>{svar}</span></div>
    </div>
  )
}

export function Billede({ src, navn, meta }: { src?: string; navn: string; meta: string }) {
  return (
    <div className="rv-kort rv-bill">
      {src && <img src={src} alt={navn} />}
      <div>
        <div className="rv-n">{navn}</div>
        <div className="rv-m2">{meta}</div>
      </div>
    </div>
  )
}

/** Faldbacken. Ikke fattig: navn, argumenter og resultat, læsbart fra dag ét. */
export function Faldback({ navn, ind, ud }: { navn: string; ind: string; ud: string }) {
  return (
    <div className="rv-kort rv-fald">
      <div className="rv-kh">{navn}</div>
      <div className="rv-par"><div className="rv-mrk">IN</div><div className="rv-v">{ind}</div></div>
      <div className="rv-par"><div className="rv-mrk">OUT</div><div className="rv-v">{ud}</div></div>
    </div>
  )
}

/** Vælg krop ud fra familie. Én indgang, så rækken ikke kender formerne. */
export function kropFor(
  navn: string,
  input: Record<string, unknown>,
  result: string | undefined,
  fejl: boolean,
): ReactNode {
  const { familie } = postFor(navn)
  const ind = JSON.stringify(input, null, 2)
  const ud = udDel(result)

  if (familie === 'terminal') {
    return <Terminal cmd={String(input.command ?? navn)} ud={ud} exit={exitKode(result, fejl)} />
  }
  if (familie === 'diff') {
    // Serveren sender ikke en struktureret diff. Vi viser den raa patch og
    // farver de linjer der ER markeret — bedre end at opdigte en diff.
    const linjer = ud.split('\n').map((t) => ({
      k: t.startsWith('+') ? ('add' as const) : t.startsWith('-') ? ('del' as const) : ('ctx' as const),
      t: t.replace(/^[+-]/, ''),
    }))
    return <Diff linjer={linjer} />
  }
  if (familie === 'web') {
    return <div className="rv-kort"><pre>{ud}</pre></div>
  }
  if (familie === 'billede') {
    const sti = String(input.path ?? input.image_path ?? '')
    return <Billede navn={sti || navn} meta={ud.slice(0, 120)} />
  }
  if (familie === 'io' || familie === 'liste') {
    return <IndUd ind={ind} ud={ud} />
  }
  return <Faldback navn={navn} ind={ind} ud={ud} />
}
