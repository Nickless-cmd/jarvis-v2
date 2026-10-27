/** Gør referencer skrevet som inline code til rigtige links — mobil-kopien.
 *
 * Samme regel som desk (`apps/jarvis-desk/src/lib/linkifyRefs.ts`). De to apps
 * har hver deres build og deler ikke moduler, så de 15 linjer står to steder
 * med vilje. Ændrer du reglen, ret BEGGE — ellers ser den samme besked
 * forskellig ud på telefon og desk.
 *
 * BAGGRUND (målt 25/10-2026, Bjørn): en commit-hash som `442b3bc85` blev vist
 * som grå kode-badge, men var død — han skulle kopiere den for at slå den op.
 * MarkdownIt's `linkify: true` autolinker kun PROSA; en URL i backticks bliver
 * `code_inline` uden link. Derfor konverterer vi på token-niveau.
 *
 * Konservativt med vilje: kun inline code, aldrig kodeblokke (```), hvor en
 * hash kan være en del af en kommando.
 */

/** Samme fjern som `git remote -v` i repoet. */
export const KODE_REPO = 'Nickless-cmd/jarvis-v2'

import type { RefKind } from './refAabn'

const HASH_RE = /^[0-9a-f]{7,40}$/i
const URL_RE = /^https?:\/\/[^\s<>"`]+$/i

// Referencerne jeg selv skriver i chat (27/10-2026). Samme fem familier som
// desk, og rækkefølgen betyder noget: præfikserne tjekkes FØR hash-reglen,
// ellers ville `asg-d82c9e2189ec4b8e` blive læst som en commit-hash.
//
// Grænsen er stram med vilje — et almindeligt ord må ikke blive et link.
const AGENT_RE = /^(?:agent\/)?(asg-[0-9a-f]{8,})$/i
const WORKTREE_RE = /^(wt-[0-9a-f]{8,})$/i
const WAKE_RE = /^(wake-[0-9a-f]{8,})$/i
const RUN_RE = /^(run-[0-9a-f]{8,})$/i
const SIDE_OPGAVE_RE = /^(side-[0-9a-f]{8,})$/i
const FIL_RE =
  /^[\w.\-/]+\.(?:py|ts|tsx|js|jsx|json|md|css|html|sh|yml|yaml|toml|sql|db|txt|pdf|docx|xlsx|pptx)$/i

export function commitUrl(hash: string): string {
  return `https://github.com/${KODE_REPO}/commit/${hash}`
}

/** Den URL en inline code-reference peger på, eller null. */
export function referenceUrl(raw: string): string | null {
  const tekst = raw.trim()
  if (!tekst) return null
  if (URL_RE.test(tekst)) return tekst

  // Pseudo-hrefs: de peger ikke på en ekstern ressource, men styrer
  // UI-tilstand i appen selv (`lib/refAabn`). Sanitizeren i desk har en
  // tilsvarende snæver hvidliste — hold dem i samme form.
  const agent = AGENT_RE.exec(tekst)
  if (agent) return `#ref=agent:${agent[1]}`
  const wt = WORKTREE_RE.exec(tekst)
  if (wt) return `#ref=worktree:${wt[1]}`
  const wake = WAKE_RE.exec(tekst)
  if (wake) return `#ref=wake:${wake[1]}`
  const run = RUN_RE.exec(tekst)
  if (run) return `#ref=run:${run[1]}`
  const side = SIDE_OPGAVE_RE.exec(tekst)
  if (side) return `#ref=side:${side[1]}`
  if (FIL_RE.test(tekst)) return `#ref=fil:${tekst}`

  if (HASH_RE.test(tekst)) return commitUrl(tekst)
  return null
}

/** Læs en `#ref=`-href tilbage til (familie, id). Null for alt andet. */
export function parseRefHref(href: string): { kind: RefKind; id: string } | null {
  const m = /^#ref=(side|agent|worktree|wake|run|fil):(.+)$/.exec(
    String(href ?? '').trim()
  )
  if (!m) return null
  const kind = m[1] as RefKind
  const id = m[2] ?? ''
  return id ? { kind, id } : null
}

type Token = {
  type: string
  content: string
  children?: Token[] | null
  attrs?: [string, string][] | null
  attrSet?: (navn: string, vaerdi: string) => void
  attrJoin?: (navn: string, vaerdi: string) => void
}

type State = {
  tokens: Token[]
  Token: new (type: string, tag: string, nesting: number) => Token
}

/** markdown-it core-regel: `code_inline` der er en reference bliver et link. */
export function linkifyRefsRule(state: State): void {
  for (const token of state.tokens) {
    if (token.type !== 'inline' || !Array.isArray(token.children)) continue
    const ny: Token[] = []
    for (const barn of token.children) {
      const url = barn.type === 'code_inline' ? referenceUrl(barn.content) : null
      if (!url) {
        ny.push(barn)
        continue
      }
      const aabn = new state.Token('link_open', 'a', 1)
      aabn.attrSet?.('href', url)
      const tekst = new state.Token('text', '', 0)
      tekst.content = barn.content
      const luk = new state.Token('link_close', 'a', -1)
      ny.push(aabn, tekst, luk)
    }
    token.children = ny
  }
}
