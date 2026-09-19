import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { JarvisRing } from '../shell/JarvisRing'
import { LiveVerb } from '../shell/LiveVerb'
import { varighed } from '../../lib/jobsApi'
import { sektioner, type Sektion } from '../../lib/livenessSektioner'
import type { ContentBlock } from '../../lib/sseProtocol'

/** Skiftende status-verber i Jarvis' stemme (når der ikke er en konkret tool-
 *  handling). Roterer hvert par sekunder så det føles levende. */
const VERBS = ['tænker', 'grunder', 'samler trådene', 'regner den ud', 'vejer mulighederne', 'kigger nærmere']

/** Kort token-tal: 1234 → "1.2k". */
function fmtTokens(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)
}

/** Vedvarende liveness-linje — Jarvis' svar på Claude Codes linje over composeren.
 *
 *  Samme oplysninger, samme rækkefølge: varighed · tokens · tænke-tid ·
 *  hvad der blev lavet (talt sammen pr. familie) · baggrundsjob — og så hvad
 *  han laver lige nu. Formen er lånt fra Claude Code 2.1.271 (se
 *  `lib/livenessSektioner.ts` for kilden); to forskelle er bevidste:
 *
 *  1. Ikonet er Jarvis' egen ring, ikke et stjernemotiv. Vi viser de samme
 *     ting som CC; vi klæder os ikke ud som CC.
 *  2. Tidsformatet kommer fra `varighed()` i jobsApi — samme funktion panelet
 *     bruger, så linjen og panelet aldrig viser to forskellige tal for samme
 *     job. (Bjørn 19/9-2026: «vi for den 1:1 og viser de samme ting».)
 *
 *  Bjørn 19/9-2026, senere samme aften: «Der var mere end 4 ting i den første
 *  liste du viste mig.» Han havde ret — sektionerne manglede. Nu er de med.
 */
export function LivenessIndicator({
  status,
  elapsedMs,
  density,
  workingStep,
  tokens = 0,
  thoughtMs = null,
  thoughtAfsluttet = false,
  runningJobs = 0,
  blocks,
}: {
  status: string
  elapsedMs: number
  density: 'compact' | 'full'
  workingStep?: string | null
  /** Kontekst-størrelsen: input + cacheHit + cacheMiss + output. */
  tokens?: number
  /** Tænke-tid i ms for den seneste/aktive tanke — «Thought for 2s». */
  thoughtMs?: number | null
  /** true = tanken er afsluttet → teksten gennemstreges, som hos CC. */
  thoughtAfsluttet?: boolean
  /** Antal kørende baggrundsjobs (server + Bjørns maskine + agenter). */
  runningJobs?: number
  /** Runnets blokke — grundlaget for sektionerne («Læste 3 filer, kørte 2 …»). */
  blocks?: ContentBlock[]
}) {
  const working = status === 'working'
  const tone = working ? 'working' : status === 'error' || status === 'interrupted' ? 'error' : 'idle'

  // Roter verbum hvert 2,5s mens han arbejder.
  const [verbIdx, setVerbIdx] = useState(0)
  useEffect(() => {
    if (!working) return
    const id = setInterval(() => setVerbIdx((i) => (i + 1) % VERBS.length), 2500)
    return () => clearInterval(id)
  }, [working])

  // Sektionerne: nutid mens han arbejder, datid når turen er slut — CC's
  // én-boolean-greb. Memoiseret på blokkene så vi ikke tæller for hver tick.
  const arbejde = useMemo(() => sektioner(blocks, working), [blocks, working])

  // Sektionerne i CC's rækkefølge. Tænke-tiden er den FØRSTE af dem, derefter
  // arbejdet — hver vises kun hvis den har indhold, så der ikke står tomme
  // skilletegn.
  const dele: ReactNode[] = []
  if (working) {
    const sek = Math.floor(elapsedMs / 1000)
    if (sek > 0) dele.push(varighed(sek))
  }
  if (tokens > 0) dele.push(`${fmtTokens(tokens)} tokens`)
  if (thoughtMs != null && thoughtMs > 0) {
    dele.push(
      <span
        key="tanke"
        className={`liveness-thought${thoughtAfsluttet ? ' afsluttet' : ''}`}
      >
        Thought for {varighed(Math.floor(thoughtMs / 1000))}{thoughtAfsluttet ? '.' : ''}
      </span>,
    )
  }
  for (const s of arbejde as Sektion[]) {
    dele.push(<span key={s.key} className="liveness-arbjede">{s.tekst}</span>)
  }
  if (runningJobs > 0) {
    dele.push(runningJobs === 1 ? '1 job kører' : `${runningJobs} jobs kører`)
  }

  // Konkret tool-handling beholdes; model-boilerplate ("Thinking via …") droppes
  // til fordel for et skiftende verbum.
  const step = (workingStep || '').trim()
  const isBoilerplate = !step || /^thinking via/i.test(step) || /^arbejder$/i.test(step)
  const action = working ? (isBoilerplate ? (VERBS[verbIdx] ?? 'tænker') : step) : tone === 'error' ? 'afbrudt' : 'klar'

  return (
    <div className={`liveness liveness-${density} ${working ? 'is-working' : 'is-idle'}`}>
      <JarvisRing size={14} spinning={working} tone={tone} />
      <span className="liveness-label">
        {dele.length > 0 && (
          <>
            {dele.map((d, i) => (
              <span key={i}>{i > 0 ? ' · ' : ''}{d}</span>
            ))}
            {' · '}
          </>
        )}
        {working ? <LiveVerb text={action} /> : action}
      </span>
    </div>
  )
}
