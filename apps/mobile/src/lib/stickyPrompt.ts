import { useSyncExternalStore } from 'react'

/**
 * Sticky prompt som ikon i topbjælken (Bjørn 19/9-2026: strimlen i toppen af
 * samtalen var «lidt træls» — den lå oven på netop de linjer man læste).
 *
 * Listen ved HVORNÅR din besked er rullet ud af syne; topbjælken bor i App,
 * tre lag længere oppe. I stedet for at trække en prop igennem ChatScreen
 * udgiver listen tilstanden her, og bjælken lytter.
 */
export interface StickyPrompt {
  tekst: string
  hop: () => void
}

let nu: StickyPrompt | null = null
const lyttere = new Set<() => void>()

export function saetStickyPrompt(s: StickyPrompt | null): void {
  // Samme tekst = samme tilstand; ellers ville hver scroll-ramme gen-rendere bjælken.
  if (nu?.tekst === s?.tekst && Boolean(nu) === Boolean(s)) { if (s && nu) nu.hop = s.hop; return }
  nu = s
  lyttere.forEach((l) => l())
}

export function useStickyPrompt(): StickyPrompt | null {
  return useSyncExternalStore(
    (l) => { lyttere.add(l); return () => { lyttere.delete(l) } },
    () => nu,
    () => nu,
  )
}
