/** Gør referencer jeg skriver som inline code til rigtige links.
 *
 * BAGGRUND (målt 25/10-2026, Bjørn): commit-hashes som `442b3bc85` blev vist
 * som grå kode-badges — korrekt formateret, men døde. Han skulle kopiere dem
 * manuelt for at slå dem op. Samme gælder en URL skrevet i backticks:
 * remark-gfm autolinker KUN prosa (målt: `Se https://srvlab.dk` → link,
 * `` `https://srvlab.dk` `` → inlineCode uden link).
 *
 * HVORFOR KUN INLINE CODE, IKKE BAR TEKST
 * En bar 8-tegns hex-streng kan være en farvekode, et id eller en hash i en
 * sætning der ikke handler om git. Inline code er derimod et bevidst signal
 * fra mig om "dette er en reference". Derfor er reglen konservativ: den rører
 * kun tekst jeg selv har markeret, og den rører aldrig kodeblokke (```), hvor
 * en hash kan være en del af en kommando.
 *
 * Linket bevarer inlineCode-elementet indeni, så badge-udseendet står
 * uændret — det er kun dødeligheden der forsvinder.
 */
import type { Root } from 'mdast'

/** Repoet commit-hashes peger ind i. Samme fjern som `git remote -v`. */
export const KODE_REPO = 'Nickless-cmd/jarvis-v2'

/** Kort og fuld git-hash. 7 er git's egen minimums-forkortelse. */
const HASH_RE = /^[0-9a-f]{7,40}$/i

/** En hel URL — ikke en URL inde i en sætning, for så er det ikke en reference. */
const URL_RE = /^https?:\/\/[^\s<>"`]+$/i

export function commitUrl(hash: string): string {
  return `https://github.com/${KODE_REPO}/commit/${hash}`
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

/** remark-plugin: inlineCode → link når værdien er en hash eller en URL. */
export function linkifyRefs() {
  return (tree: Root): void => {
    const gaa = (node: { children?: unknown[] }): void => {
      const boern = node.children
      if (!Array.isArray(boern)) return
      for (let i = 0; i < boern.length; i += 1) {
        const barn = boern[i] as { type?: string; value?: string; children?: unknown[] }
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
        gaa(barn as Forelder)
      }
    }
    gaa(tree as unknown as Forelder)
  }
}
