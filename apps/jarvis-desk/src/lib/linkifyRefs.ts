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

export function commitUrl(hash: string): string {
  return `https://github.com/${KODE_REPO}/commit/${hash}`
}

/** Er href et GitHub commit-link? Bruges til korrekt ikonvalg. */
export function isCommitHref(href: string): boolean {
  return /^https:\/\/github\.com\/[^/\s]+\/[^/\s]+\/commit\/[0-9a-f]{7,40}(?:[/?#].*)?$/i.test(href)
}

/** Den URL en inline code-reference peger på, eller null hvis den ikke er en. */
export function referenceUrl(raw: string): string | null {
  const tekst = raw.trim()
  if (!tekst) return null
  if (URL_RE.test(tekst)) return tekst
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
