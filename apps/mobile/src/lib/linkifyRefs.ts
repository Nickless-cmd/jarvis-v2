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

const HASH_RE = /^[0-9a-f]{7,40}$/i
const URL_RE = /^https?:\/\/[^\s<>"`]+$/i

export function commitUrl(hash: string): string {
  return `https://github.com/${KODE_REPO}/commit/${hash}`
}

/** Den URL en inline code-reference peger på, eller null. */
export function referenceUrl(raw: string): string | null {
  const tekst = raw.trim()
  if (!tekst) return null
  if (URL_RE.test(tekst)) return tekst
  if (HASH_RE.test(tekst)) return commitUrl(tekst)
  return null
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
