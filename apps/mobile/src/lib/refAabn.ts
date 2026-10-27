/** Bro mellem en klikket reference i en besked og en flade i appen.
 *
 * BAGGRUND (Bjørn 27/10-2026): desk fik klikbare referencer med ikon og flade
 * (`apps/jarvis-desk/src/lib/refAabn.ts`). Mobil-kopien af `linkifyRefs` blev
 * flagget samme dag som «referencerne er stadig døde badges på telefonen».
 *
 * HVORFOR EN EVENT OG IKKE EN PROP
 * --------------------------------
 * `MessageBubble` er `memo`'et og `MarkdownBlok` med den, fordi et langt svar
 * ellers re-rendres ved hver delta (se `lib/markdownBlokke`). En handler der
 * skal helt ned gennem den kæde ville gøre memoiseringen værdiløs — præcis
 * samme afvejning som i desk. En modul-scope event koster ingen prop-drilling.
 *
 * HVAD MOBILEN FAKTISK KAN ÅBNE
 * -----------------------------
 * Appen har to modes: `snak` og `arbejde`. Kørsler, godkendelser og
 * sideopgaver bor i `arbejde` (standardfanen er `tasks`), så de fem
 * kørsels-familier lander dér. Mobilen har INGET filtræ — derfor viser et
 * filnavn sin sti i stedet for at påstå en flade der ikke findes. Et link der
 * lover mere end appen kan levere er værre end et der ærligt viser sig selv.
 */

export type RefKind = 'side' | 'agent' | 'worktree' | 'wake' | 'run' | 'fil'

export const REF_AABN_EVENT = 'jarvis:ref-aabn'

export interface RefAabnDetail {
  kind: RefKind
  id: string
}

export function emitRefAabn(kind: RefKind, id: string): void {
  // React Native har et `window`-global UDEN DOM-metoderne. En guard der kun
  // spørger «findes window?» slipper derfor igennem og kaster i render —
  // målt 27/10-2026: fire App-tests faldt i ErrorBoundary («Visningen ramte
  // en fejl»). Spørg om METODEN, ikke om objektet.
  if (typeof window === 'undefined') return
  if (typeof window.dispatchEvent !== 'function') return
  window.dispatchEvent(
    new CustomEvent<RefAabnDetail>(REF_AABN_EVENT, { detail: { kind, id } })
  )
}

export function onRefAabn(
  listener: (kind: RefKind, id: string) => void
): () => void {
  if (typeof window === 'undefined') return () => undefined
  if (typeof window.addEventListener !== 'function') return () => undefined
  const handler = (e: Event) => {
    const detail = (e as CustomEvent<RefAabnDetail>).detail
    if (!detail?.kind || !detail?.id) return
    listener(detail.kind, detail.id)
  }
  window.addEventListener(REF_AABN_EVENT, handler)
  return () => window.removeEventListener(REF_AABN_EVENT, handler)
}
