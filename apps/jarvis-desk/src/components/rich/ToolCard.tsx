import { useEffect, useState } from 'react'
import { Check, X, Loader, FileDiff } from 'lucide-react'
import type { ContentBlock } from '../../lib/sseProtocol'
import { lookupTool } from '../../lib/toolRegistry'
import { visAendring } from '../../lib/aendringsFokus'
import { diffFraResultat, diffStat } from '../../lib/diffStat'
import { DiffView } from './DiffView'
import { PauseAndAskCard } from './PauseAndAskCard'
import { parsePauseAsk } from '../../lib/pauseAsk'
import { memoryWriteOutcome } from '../../lib/toolRound'
import { hentVaerktoejsResultat, type ApiConfig } from '../../lib/api'

/** Density-aware, værktøjs-specifik tool-kald-visning (Claude Desktop-stil).
 *  bash → terminal-blok, write/edit → fil-header + diff, read/glob/grep → kompakt.
 *  Argumenter og resultat rendres INERT via <pre> — aldrig markdown/HTML — så
 *  fjendtligt tool-output ikke kan injicere klikbare elementer. */
export function ToolCard({
  block,
  density,
  aabenFraStart = false,
  beskedId,
  config,
}: {
  block: Extract<ContentBlock, { type: 'tool_use' }>
  density: 'compact' | 'full'
  /** Visningen «Alt»: åbent fra start, men kan stadig foldes. */
  aabenFraStart?: boolean
  /** Beskeden kaldet hører til — nødvendig for at hente et afkortet resultat. */
  beskedId?: string
  config?: ApiConfig
}) {
  const [open, setOpen] = useState(density === 'full' || aabenFraStart)
  const expanded = density === 'full' || open

  // Et langt resultat sendes afkortet med samtalen (serveren: de første 2.000
  // tegn). Resten hentes FØRST når linjen foldes ud — samme greb som
  // tænke-blokkens hale. Uden config eller besked-id viser vi det vi har.
  const [resten, setResten] = useState<string | null>(null)
  const [henter, setHenter] = useState(false)
  useEffect(() => {
    if (!expanded || !block.resultAfkortet || resten || henter) return
    if (!config || !beskedId) return
    setHenter(true)
    hentVaerktoejsResultat(config, beskedId, block.id)
      .then((fuldt) => setResten(fuldt))
      .catch(() => { /* behold det afkortede — bedre end en tom linje */ })
      .finally(() => setHenter(false))
  }, [expanded, block.resultAfkortet, block.id, beskedId, config, resten, henter])

  const resultat = resten ?? block.result

  const args = parseArgs(block)
  const fam = toolFamily(block.name)
  const meta = lookupTool(block.name)
  const summary = meta.summarize(args, block.result)
  // Serverens MAALTE tal foerst: den har filen i haanden lige foer den
  // skriver og kan derfor sige hvor meget en overskrivning FJERNEDE — noget
  // klienten umuligt kan vide af argumenterne alene. Gaettet bliver som
  // faldback, fordi et kald der stadig koerer ikke HAR et resultat endnu.
  const ds = diffFraResultat(block.result) ?? diffStat(block.name, args)
  const memoryOutcome = block.name.replace(/^operator_/, '') === 'remember_this'
    ? memoryWriteOutcome(block.status, block.result) : undefined
  const status = memoryOutcome === 'error' ? 'error' : block.status ?? 'running'
  const anomali = block.anomali ?? (memoryOutcome === 'unknown' ? 'uden-resultat' : undefined)
  const ask = parsePauseAsk(block.result)
  const Icon = meta.Icon

  return (
    <div className={`toolcard fam-${fam} status-${status}`}>
      <div className="toolcard-headrow">
      <button
        type="button"
        className="toolcard-head"
        onClick={() => density === 'compact' && setOpen((o) => !o)}
      >
        <Icon size={13} className="toolcard-icon" />
        <span className="toolcard-name">{meta.label}</span>
        {summary && <span className="toolcard-summary">{summary}</span>}
        {ds && (
          <span className="toolcard-diffstat">
            <span className="git-add">+{ds.add}</span> <span className="git-del">−{ds.del}</span>
          </span>
        )}
        <StatusBadge status={status} anomali={anomali} />
      </button>
      {/* Claude Desktop §9: «Click a filename on an Edited or Wrote row to open
          that file in the diff pane». Sin egen knap — en knap i en knap er
          ugyldig og kan ikke nås med tastaturet. */}
      {(fam === 'edit' || fam === 'write') && filSti(args) ? (
        <button
          type="button"
          className="toolcard-aabn"
          title={`Vis ${filSti(args)} i Ændringer`}
          aria-label={`Vis ${filSti(args)} i Ændringer`}
          onClick={() => visAendring(filSti(args)!)}
        >
          <FileDiff size={13} />
        </button>
      ) : null}
      </div>
      {anomali && (
        // Siges i klartekst, ikke kun med et ikon: det er netop den slags
        // man ellers ikke ville opdage.
        <div className="toolcard-anomali" role="note">
          {anomali === 'uden-kald'
            ? 'Et resultat uden det kald det hører til — kaldet findes ikke i beskeden.'
            : 'Intet resultat blev gemt for dette kald — udfaldet er ukendt.'}
        </div>
      )}
      {/* Et spørgsmål er ikke tool-output man folder ud — det skal ses med
          det samme, også i kompakt tilstand. */}
      {ask
        ? <div className="toolcard-body"><PauseAndAskCard ask={ask} /></div>
        : expanded && (
        <div className="toolcard-body">
          {renderBody(fam, args, resultat)}
          {block.resultAfkortet && !resten && (
            <div className="toolcard-afkortet">
              {henter
                ? 'henter resten …'
                : `viser de første ${(block.result?.length ?? 0).toLocaleString('da-DK')} af ${(block.resultTegnIAlt ?? 0).toLocaleString('da-DK')} tegn`}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/** Stien et redigerings-/skrive-kald rørte. */
function filSti(args: Record<string, unknown>): string | undefined {
  const v = args.file_path ?? args.path
  return typeof v === 'string' && v.trim() ? v : undefined
}

type Fam = 'bash' | 'write' | 'edit' | 'read' | 'glob' | 'grep' | 'list' | 'other'

function toolFamily(name: string): Fam {
  const n = name.toLowerCase()
  if (n.includes('bash')) return 'bash'
  if (n.includes('write_file')) return 'write'
  if (n.includes('edit_file')) return 'edit'
  if (n.includes('read_file')) return 'read'
  if (n.includes('glob') || n.includes('find_files')) return 'glob'
  if (n.includes('grep') || n === 'search') return 'grep'
  if (n.includes('list_dir')) return 'list'
  return 'other'
}

function parseArgs(block: Extract<ContentBlock, { type: 'tool_use' }>): Record<string, unknown> {
  if (block.input && Object.keys(block.input).length) return block.input
  try { return JSON.parse(block.partialJson || '{}') } catch { return {} }
}

function StatusBadge({ status, anomali }: { status: string; anomali?: string }) {
  // Et ukendt udfald må hverken ligne en succes (flueben) eller en fejl (kryds).
  if (anomali === 'uden-resultat') return <span className="toolcard-status ukendt" title="Ukendt udfald">?</span>
  if (status === 'done') return <span className="toolcard-status ok"><Check size={11} /></span>
  if (status === 'error') return <span className="toolcard-status err"><X size={11} /></span>
  return <span className="toolcard-status run"><Loader size={11} /></span>
}

function renderBody(fam: Fam, args: Record<string, unknown>, result?: string) {
  if (fam === 'bash') {
    return (
      <div className="tc-term">
        <div className="tc-term-cmd">$ {String(args.command || '')}</div>
        {result && <pre className="tc-term-out">{result}</pre>}
      </div>
    )
  }
  if (fam === 'edit') {
    // `edit_file` sender old_text/new_text (målt 18/9-2026 — samme fejl som
    // diffStat havde): med kun *_string faldt HVER redigering igennem til den
    // rå resultat-visning, og diff'en blev aldrig vist (19/9-2026).
    const oldS = String(args.old_text ?? args.old_string ?? args.old ?? '')
    const newS = String(args.new_text ?? args.new_string ?? args.new ?? '')
    if (oldS || newS) {
      const file = String(args.file_path ?? args.path ?? '') || undefined
      return <DiffView oldText={oldS} newText={newS} filename={file} />
    }
  }
  if (fam === 'write') {
    const content = String(args.content ?? '')
    const lines = content ? content.split('\n').length : 0
    return (
      <div className="tc-write">
        <div className="tc-write-stat">Skrev {lines} linjer</div>
        {content && <pre className="tc-write-body">{content.length > 4000 ? content.slice(0, 4000) + '\n…' : content}</pre>}
      </div>
    )
  }
  // read / glob / grep / list / other: vis resultat (og args for 'other')
  return (
    <>
      {fam === 'other' && Object.keys(args).length > 0 && (
        <pre className="toolcard-args">{JSON.stringify(args, null, 2)}</pre>
      )}
      {result && <pre className="toolcard-result">{result}</pre>}
    </>
  )
}
