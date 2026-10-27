/** Gør referencer jeg skriver som inline code til rigtige links.
 *
 * BAGGRUND (målt 25/10-2026, Bjørn): commit-hashes som `442b3bc85` blev vist
 * som grå kode-badges — korrekt formateret, men døde. Han skulle kopiere dem
 * manuelt for at slå dem op. Samme gælder en URL skrevet i backticks:
 * remark-gfm autolinker KUN prosa (målt: `Se https://srvlab.dk` → link,
 * `` `https://srvlab.dk` `` → inlineCode uden link).
 *
 * Chat mode får oftere commit-hashes som bar tekst end code mode. Derfor
 * genkendes nu også fritstående hex-tokens med både bogstav og tal. CSS-farver
 * (#a371f7), UUID-led (bindestreg) og rene tal/bogstavord afvises, så reglen
 * ikke gør almindelige ids til GitHub-links. Kodeblokke røres aldrig.
 *
 * Linket bevarer inlineCode-elementet indeni, så badge-udseendet står
 * uændret — det er kun dødeligheden der forsvinder.
 */
import type { Root } from 'mdast'

/** Repoet commit-hashes peger ind i. Samme fjern som `git remote -v`. */
export const KODE_REPO = 'Nickless-cmd/jarvis-v2'

/** Kort og fuld git-hash. 7 er git's egen minimums-forkortelse. */
const HASH_RE = /^[0-9a-f]{7,40}$/i
const BARE_HASH_RE = /\b[0-9a-f]{7,40}\b/gi

/** En hel URL — ikke en URL inde i en sætning, for så er det ikke en reference. */
const URL_RE = /^https?:\/\/[^\s<>"`]+$/i

/** Side-opgave-id: `side-` + 8-12 hex-tegn. */
const SIDE_OPGAVE_RE = /^side-[0-9a-f]{8,12}$/i

/** Agent-assignment: `asg-` + hex. Kan også skrives som `agent/asg-…` — det er
 *  den form `Task`-værktøjet og run-trace'et bruger, og Bjørn skriver den selv
 *  (målt 27/10-2026). Præfikset er det der redder os: uden det ville hex-delen
 *  blive læst som en commit-hash af BARE_HASH_RE. */
const AGENT_RE = /^(?:agent\/)?(asg-[0-9a-f]{8,32})$/i

/** Worktree-id: `wt-` + hex. */
const WORKTREE_RE = /^(wt-[0-9a-f]{8,32})$/i

/** Selv-vækning: `wake-` + hex. */
const WAKE_RE = /^(wake-[0-9a-f]{8,32})$/i

/** Run-id: `run-` + hex. */
const RUN_RE = /^(run-[0-9a-f]{8,32})$/i

/** Et filnavn eller et stykke af en sti, fx `sideOpgaveHighlight.ts` eller
 *  `apps/mobile/src/lib/linkifyRefs.ts`. Endelsen er det der gør det sikkert:
 *  `0.6.270` og `e.g` rammer ikke listen. */
const FIL_RE = /^[\w][\w./-]*\.(?:ts|tsx|js|jsx|mjs|cjs|py|md|json|css|scss|html|sh|bash|yaml|yml|toml|sql|rs|go|java|kt)$/i

export function commitUrl(hash: string): string {
  return `https://github.com/${KODE_REPO}/commit/${hash}`
}

/** Er href et GitHub commit-link? Bruges til korrekt ikonvalg. */
export function isCommitHref(href: string): boolean {
  return /^https:\/\/github\.com\/[^/\s]+\/[^/\s]+\/commit\/[0-9a-f]{7,40}(?:[/?#].*)?$/i.test(href)
}

/** Pseudo-href til en side-opgave. Side-opgaver har ingen rigtig side — de
 *  bor i et panel (jarvis-desk:panel:sideopgaver), ikke en route. Dette
 *  interne scheme lader MarkdownRenderer genkende og åbne panelet i stedet
 *  for at forsøge en navigation. */
export function sideOpgaveHref(id: string): string {
  return `#side-opgave=${id}`
}

/** Er href en reference til en side-opgave? Bruges til ikonvalg (ListTodo)
 *  og til klik-håndtering (åbn panel i stedet for ekstern navigation). */
export function isSideOpgaveHref(href: string): boolean {
  return /^#side-opgave=side-[0-9a-f]{8,12}$/i.test(href)
}

/** Udtræk side-opgave-id'et fra en pseudo-href, eller null hvis den ikke er en. */
export function sideOpgaveIdFromHref(href: string): string | null {
  const m = /^#side-opgave=(side-[0-9a-f]{8,12})$/i.exec(href)
  return m?.[1] ?? null
}

/** Hvilken flade en reference peger på. MarkdownRenderer bruger dette til at
 *  vælge ikon og til at route klikket — ét opslag i stedet for fem regexer
 *  spredt ud over render-stien. */
export type RefKind = 'sideopgave' | 'agent' | 'worktree' | 'wake' | 'run' | 'fil'

const KIND_RE: Record<RefKind, RegExp> = {
  sideopgave: /^#side-opgave=(side-[0-9a-f]{8,12})$/i,
  agent: /^#agent=(asg-[0-9a-f]{8,32})$/i,
  worktree: /^#worktree=(wt-[0-9a-f]{8,32})$/i,
  wake: /^#wake=(wake-[0-9a-f]{8,32})$/i,
  run: /^#run=(run-[0-9a-f]{8,32})$/i,
  fil: /^#fil=([\w][\w./-]*\.[a-z0-9]{1,6})$/i,
}

/** Reference-mål uden om en rigtig URL. De her id'er har ingen side på nettet —
 *  de bor i et panel i desk, så vi bærer målet i et internt scheme og lader
 *  klik-håndteringen åbne den rette flade. */
export function refHref(kind: RefKind, vaerdi: string): string {
  return kind === 'sideopgave' ? `#side-opgave=${vaerdi}` : `#${kind}=${vaerdi}`
}

/** Er href en reference (i modsætning til en rigtig URL)? */
export function refKind(href: string): RefKind | null {
  for (const kind of Object.keys(KIND_RE) as RefKind[]) {
    if (KIND_RE[kind].test(href)) return kind
  }
  return null
}

/** Værdien bag en reference-href (id eller filnavn), eller null. */
export function refVaerdi(href: string): string | null {
  const kind = refKind(href)
  if (!kind) return null
  return KIND_RE[kind].exec(href)?.[1] ?? null
}

/** Bagudkompatibel indgang — samme som `refVaerdi` for side-opgaver. */
export function agentIdFromHref(href: string): string | null {
  return KIND_RE.agent.exec(href)?.[1] ?? null
}

/** Filnavnet bag en `#fil=`-href, eller null. */
export function filNavnFromHref(href: string): string | null {
  return KIND_RE.fil.exec(href)?.[1] ?? null
}

/** Den URL eller reference en inline code-reference peger på, eller null. */
export function referenceUrl(raw: string): string | null {
  const tekst = raw.trim()
  if (!tekst) return null
  if (URL_RE.test(tekst)) return tekst
  if (SIDE_OPGAVE_RE.test(tekst)) return sideOpgaveHref(tekst)
  // Rækkefølgen er ikke kosmetisk: præfikserne (asg/wt/wake/run) skal prøves
  // FØR hash-reglen, ellers ville hex-delen blive læst som en commit.
  const agent = AGENT_RE.exec(tekst)
  if (agent?.[1]) return refHref('agent', agent[1])
  const worktree = WORKTREE_RE.exec(tekst)
  if (worktree?.[1]) return refHref('worktree', worktree[1])
  const wake = WAKE_RE.exec(tekst)
  if (wake?.[1]) return refHref('wake', wake[1])
  const run = RUN_RE.exec(tekst)
  if (run?.[1]) return refHref('run', run[1])
  // Filnavn før hash: `sideOpgaveHighlight.ts` er ikke hex, men et token som
  // `abc1234.ts` kunne i teorien forvirre — endelsen afgør det.
  if (FIL_RE.test(tekst)) return refHref('fil', tekst)
  if (HASH_RE.test(tekst)) return commitUrl(tekst)
  return null
}

type Forelder = { children: unknown[] }

type MdNode = {
  type?: string
  value?: string
  children?: unknown[]
}

function bareHashNodes(value: string): MdNode[] | null {
  const nodes: MdNode[] = []
  let cursor = 0
  let found = false
  BARE_HASH_RE.lastIndex = 0
  for (let match = BARE_HASH_RE.exec(value); match; match = BARE_HASH_RE.exec(value)) {
    const hash = match[0]
    const start = match.index
    const before = value[start - 1] ?? ''
    const after = value[start + hash.length] ?? ''
    const likelyCommit = /[0-9]/.test(hash) && /[a-f]/i.test(hash)
      && before !== '#' && before !== '-' && after !== '-'
    if (!likelyCommit) continue
    if (start > cursor) nodes.push({ type: 'text', value: value.slice(cursor, start) })
    nodes.push({
      type: 'link',
      url: commitUrl(hash),
      title: null,
      children: [{ type: 'inlineCode', value: hash }],
    } as MdNode)
    cursor = start + hash.length
    found = true
  }
  if (!found) return null
  if (cursor < value.length) nodes.push({ type: 'text', value: value.slice(cursor) })
  return nodes
}

/** remark-plugin: referencer → links uden at røre kodeblokke eller eksisterende links. */
export function linkifyRefs() {
  return (tree: Root): void => {
    const gaa = (node: MdNode): void => {
      const boern = node.children
      if (!Array.isArray(boern)) return
      for (let i = 0; i < boern.length; i += 1) {
        const barn = boern[i] as MdNode
        if (!barn || typeof barn !== 'object') continue
        if (barn.type === 'inlineCode' && typeof barn.value === 'string') {
          const url = referenceUrl(barn.value)
          if (url) {
            ;(boern as unknown[])[i] = {
              type: 'link',
              url,
              title: null,
              children: [{ type: 'inlineCode', value: barn.value }],
            }
          }
          continue
        }
        if (barn.type === 'text' && typeof barn.value === 'string' && node.type !== 'link') {
          const replacement = bareHashNodes(barn.value)
          if (replacement) {
            boern.splice(i, 1, ...replacement)
            i += replacement.length - 1
          }
          continue
        }
        if (barn.type !== 'link' && barn.type !== 'code') gaa(barn as Forelder)
      }
    }
    gaa(tree as unknown as Forelder)
  }
}
